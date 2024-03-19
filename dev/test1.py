import os, pickle, logging
from datetime import datetime


# Load calibration data if it exists
calib_data_path = 'dev/config/calib_data.pkl'
if os.path.exists(calib_data_path):
    with open(calib_data_path, 'rb') as f:
        pan_origin, tilt_origin, rotation_matrix = pickle.load(f)
        calibrated = True
        logging.info("Calibration data loaded successfully.")
        print(f"Local origin: {pan_origin}")
else:
    logging.info("No calibration data found.")
    
time_stamp = datetime.now()

os.makedirs('config', exist_ok=True)  # Ensure the config directory exists
with open('dev/config/calib_data1.pkl', 'wb') as f:
    pickle.dump((pan_origin, tilt_origin, rotation_matrix, time_stamp), f)
    logging.info("Calibration data saved successfully.")