## How to setup for running scripts

- First create 3.8 python venv => python3.8 -m venv venv38 

- Then activate venv => source venv38/bin/activate

- Then install requirements => pip install -r requirements.txt

- Then run any scripts as required => python <script_name>.py

- /dev/ => is current working folder

## TODO list:

- [x] Implement motor calibration through app

- [x] Spawn tracking process with rotation matrix

- [x] Add upgraded motor (and horns) with new mirror mount hardware

- [x] Investigate QuadDXL controller for higher control frequency

- [x] Add sync read and optimise param delcarlation for sync methods

- [x] Optimse fsolve for better convergence ie initial guess; more runs; higher tolerance

- [x] Fix bug where calibration angle carries over to another run in session

- [x] Add stop button for tracking -> terminate process

- [x] Refactor code to be more modular and readable and create dev branch

- [x] Add cd and user 

- [x] tilt calibration
    - [x] ammend calibrator class for additional point collection
    - [x] add tilt centre to tracking calculation
    - [ ] possibly change UI/UX for procedure

- [x] add video compression -> VidGear

- [x]  sync recording camera

- [x] add thread for position recording on dyna_controller

- [x] Log and sync event in mocap

- [x] Get a bigger hard drive

- [x] Log position readings

- [x] CHECK MOTOR SETTINGS ie pwm ramp

- [x] Link mocap control and all recording functions together

- [ ] Cancel recording

- [ ] take the mean of multiple markers