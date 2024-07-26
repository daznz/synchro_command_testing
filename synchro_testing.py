import bosdyn.client
import logging
import argparse
import os
import sys
import time
import math

import bosdyn.client.lease
import bosdyn.client.util
import bosdyn.geometry
from bosdyn.api import trajectory_pb2
from bosdyn.api.spot import robot_command_pb2 as spot_command_pb2
from bosdyn.client import math_helpers
from bosdyn.client.frame_helpers import GRAV_ALIGNED_BODY_FRAME_NAME, ODOM_FRAME_NAME, get_a_tform_b
from bosdyn.client.image import ImageClient
from bosdyn.client.robot_command import RobotCommandBuilder, RobotCommandClient, blocking_stand, blocking_sit
from bosdyn.client.robot_state import RobotStateClient
from bosdyn.util import seconds_to_duration
from bosdyn.client.estop import EstopClient, EstopEndpoint, EstopKeepAlive
from bosdyn.client.frame_helpers import ODOM_FRAME_NAME, VISION_FRAME_NAME, BODY_FRAME_NAME, get_odom_tform_body, get_vision_tform_body

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="192.168.50.3", help="The IP address of the robot")
parser.add_argument("--username", default="user", help="The username of the robot")
parser.add_argument("--password", default="password", help="The password of the robot")
args = parser.parse_args()

username = args.username
password = args.password
host = args.host

logger.info(f"Beginning test on robot at {host}, with username {username} and password {password}")

sdk = bosdyn.client.create_standard_sdk('synchro_command_test')
robot = sdk.create_robot(host)
robot.authenticate(username, password)

robot.time_sync.wait_for_sync()

estop_client = robot.ensure_client('estop')
estop_endpoint = bosdyn.client.estop.EstopEndpoint(client=estop_client, name='hello-spot', estop_timeout=9.0)
estop_endpoint.force_simple_setup()
estop_keep_alive = bosdyn.client.estop.EstopKeepAlive(estop_endpoint)

robot_state_client = robot.ensure_client(RobotStateClient.default_service_name)


lease_client = robot.ensure_client(bosdyn.client.lease.LeaseClient.default_service_name)
with bosdyn.client.lease.LeaseKeepAlive(lease_client, must_acquire=True, return_at_exit=True):
    # Now, we are ready to power on the robot. This call will block until the power
    # is on. Commands would fail if this did not happen. We can also check that the robot is
    # powered at any point.
    robot.logger.info('Powering on robot... This may take several seconds.')
    robot.power_on(timeout_sec=20)
    assert robot.is_powered_on(), 'Robot power on failed.'
    robot.logger.info('Robot powered on.')

    robot.logger.info('Commanding robot to stand...')
    command_client = robot.ensure_client(RobotCommandClient.default_service_name)
    blocking_stand(command_client, timeout_sec=10)
    robot.logger.info('Robot standing.')
    time.sleep(3)

    logger.info("Calibration in progress..")
        
    logger.info("Checking current state")
    currentState = robot_state_client.get_robot_state()
    robot_state_rt_vision = get_vision_tform_body(currentState.kinematic_state.transforms_snapshot)
    robot_yaw_rt_vision = robot_state_rt_vision.rot.to_yaw()
    initialRobotPos = robot_state_rt_vision
    initialRobotRot = robot_state_rt_vision.rotation
    zHeading = robot_yaw_rt_vision
    xGoal = initialRobotPos.x + (1 * math.cos(zHeading))
    yGoal = initialRobotPos.y + (1 * math.sin(zHeading))
    logger.info("Initial Robot Position: {}".format(initialRobotPos))

    commandTime = 20
    logger.info(f"Inside command creation, sending robot to {xGoal}, {yGoal}, {zHeading}")
    try:
        cmd = RobotCommandBuilder.synchro_se2_trajectory_point_command(goal_x=xGoal, goal_y=yGoal, goal_heading=zHeading, frame_name=VISION_FRAME_NAME, \
            locomotion_hint=spot_command_pb2.HINT_AUTO)
        commandId = command_client.robot_command(cmd, end_time_secs = time.time() + commandTime)
    except Exception as e:
        logger.info("Error sending command for calibration: {}".format(e))
        exit()
    logger.info("Command Should have executed")
    time.sleep(1)
    feedback = command_client.robot_command_feedback(commandId)
    # feedback = feedback.feedback.synchronized_feedback.mobility_command_feedback
    logger.info("Feedback Message: {}".format(feedback.feedback.synchronized_feedback.mobility_command_feedback.status))
    while feedback.feedback.synchronized_feedback.mobility_command_feedback.status != 1:
        time.sleep(1)
        feedback = command_client.robot_command_feedback(commandId)
    logger.info("Command should have finished")

    time.sleep(1)

    logger.info("Robot sitting.")

    blocking_sit(command_client, timeout_sec=10)

    time.sleep(1)

    logger.info("Powering off robot")


    robot.power_off(cut_immediately=False, timeout_sec=20)
    assert not robot.is_powered_on(), 'Robot power off failed.'
    robot.logger.info('Robot safely powered off.')