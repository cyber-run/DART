from dyna_controller import *
from importlib import reload
from mocap_stream import *
import numpy as np
import cProfile
import logging
import pickle
import time


class DynaTracker:
    '''
    Object to track a target using a Dynamixel servo and a QTM mocap system.
    
    - Before running this script, ensure that the Dynamixel servo is connected to
    the computer via USB and that the QTM mocap system is running and streaming
    data.
    - In QTM align
    '''
    def __init__(self, com_port='COM5'):
        # Load calibration data if it exists
        if os.path.exists('dev/config/calib_data.pkl'):
            with open('dev/config/calib_data.pkl', 'rb') as f:
                self.local_origin, self.rotation_matrix = pickle.load(f)
                logging.info("Calibration data loaded successfully.")
        else:
            logging.error("No calibration data found.")
            quit()

        # Connect to QTM; init tracker and target
        self.target = MoCap(stream_type='3d')
        time.sleep(0.1)

        # Create dynamixel controller object and open serial port
        self.dyna = DynaController(com_port)
        self.dyna.open_port()
        
        # Default init operating mode into position
        self.dyna.set_op_mode(self.dyna.pan_id, 3)
        self.dyna.set_op_mode(self.dyna.tilt_id, 3)

    def global_to_local(self, point_global: np.ndarray) -> np.ndarray:
        if self.rotation_matrix is None:
            raise ValueError("Calibration must be completed before transforming points.")
        return np.dot(np.linalg.inv(self.rotation_matrix), point_global - self.local_origin)

    def calc_rot_comp(self, point_local: np.ndarray) -> Tuple[float, float]:
        pan_angle = math.degrees(math.atan2(point_local[1], point_local[0]))
        tilt_angle = math.degrees(math.atan2(point_local[2], math.sqrt(point_local[0]**2 + point_local[1]**2)))
        return pan_angle, tilt_angle

    def num_to_range(self, num, inMin, inMax, outMin, outMax):
        return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))

    def track(self):
        if self.target.lost:
            logging.info("Target lost. Skipping iteration.")
            return
        
        logging.info("Tracking target.")
        
        # Get the target position
        target_pos = self.target.position

        # Get the local target position
        local_target_pos = self.global_to_local(target_pos)

        # Calculate the pan and tilt components of rotation from the positive X-axis
        pan_angle, tilt_angle = self.calc_rot_comp(local_target_pos)

        # Convert geometric angles to dynamixel angles
        pan_angle = self.num_to_range(pan_angle, 45, -45, 202.5, 247.5)
        tilt_angle = self.num_to_range(tilt_angle, 45, -45, 292.5, 337.5)

        # print(f"Pan angle: {pan_angle}, Tilt angle: {tilt_angle}")
        # Set the dynamixel to the calculated angles
        self.dyna.set_sync_pos(pan_angle, tilt_angle)


    def shutdown(self) -> None:
        self.target._close()
    
        # Close QTM connections
        self.target.close()

        # Close serial port
        self.dyna.close_port()

        return

def dart_track():
    reload(logging)
    logging.basicConfig(level=logging.ERROR)

    set_realtime_priority()

    dyna_tracker = DynaTracker()
    
    try:

        while True:
            dyna_tracker.track()
            # time.sleep(0.03)

    except KeyboardInterrupt:
        dyna_tracker.shutdown()
        print("Port closed successfully\n")
        sys.exit(0)

    except Exception as e:
        dyna_tracker.shutdown()
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # cProfile.run('dart_track()')
    dart_track()
        