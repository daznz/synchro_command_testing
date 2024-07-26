# synchro_command_testing

This command will run a quick test with feedback on the synchro_se2_trajectory_point_command.

Please ensure the robot is NOT on a dock, and has 2m of clear space in front of it.
This test will, in order:
    - Power the robot on
    - Stand the robot
    - Walk the robot forwards 1m
    - Sit the robot
    - Power the robot off

Debug feedback will be provided for each step of the test.


Installation:

If you don't want to install modules into the main python environment, it's often best to setup a virtual environment:

Create venv:
> python3 -m venv .venv

Activate venv:
> source .venv/bin/activate

(If you can't run the above commands because venv is not installed, install it):
> sudo apt-get install python3-venv

Update pip:
> python3 -m pip install --upgrade pip

Install requirements:
> python3 -m pip install -r requirements.txt