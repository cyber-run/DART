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

- [ ] Add stop button for tracking -> terminate process

- [ ] Refactor code to be more modular and readable and create dev branch

- [ ] take the mean of multiple markers

- [ ] tilt calibration
