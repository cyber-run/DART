from misc_funcs import set_realtime_priority, num_to_range
import logging, pickle, time, os, cProfile, asyncio
from PerfSleeper import PerfSleeper
from dyna_controller import *
from importlib import reload
from qtm_mocap import *
import numpy as np


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
                self.pan_origin, self.tilt_origin, self.rotation_matrix, _ = pickle.load(f)
                logging.info("Calibration data loaded successfully.")
        else:
            logging.error("No calibration data found.")
            quit()

        # Connect to QTM; init tracker and target
        self.target = QTMStream()
        time.sleep(0.1)

        # Create dynamixel controller object and open serial port
        self.dyna = DynaController(com_port)
        self.dyna.open_port()

        self.dyna.set_gains(1, 650, 1300, 1200)
        self.dyna.set_gains(2, 1400, 500, 900)
        
        # Default init operating mode into position
        self.dyna.set_op_mode(self.dyna.pan_id, 3)
        self.dyna.set_op_mode(self.dyna.tilt_id, 3)

        self.counter = 0
        self.start_time = time.perf_counter()

        self.pan_angles = []
        self.tilt_angles = []

    def tilt_global_to_local(self, point_global: np.ndarray) -> np.ndarray:
        if self.rotation_matrix is None:
            raise ValueError("Calibration must be completed before transforming points.")
        return np.dot(np.linalg.inv(self.rotation_matrix), point_global - self.tilt_origin)
    
    def pan_global_to_local(self, point_global: np.ndarray) -> np.ndarray:
        if self.rotation_matrix is None:
            raise ValueError("Calibration must be completed before transforming points.")
        return np.dot(np.linalg.inv(self.rotation_matrix), point_global - self.pan_origin)

    def calc_rot_comp(self, point_local: np.ndarray) -> Tuple[float, float]:
        pan_angle = math.degrees(math.atan2(point_local[1], point_local[0]))
        tilt_angle = math.degrees(math.atan2(point_local[2], math.sqrt(point_local[0]**2 + point_local[1]**2)))
        return pan_angle, tilt_angle

    def track(self):
        # if self.target.lost:
        #     logging.info("Target lost. Skipping iteration.")
        #     return
        
        self.counter += 1
        
        logging.info("Tracking target.")
        
        # Get the target position
        target_pos = self.target.position

        # Get the local target position
        pan_local_target_pos = self.pan_global_to_local(target_pos)
        tilt_local_target_pos = self.tilt_global_to_local(target_pos)

        # Calculate the pan and tilt components of rotation from the positive X-axis
        pan_angle, _ = self.calc_rot_comp(pan_local_target_pos)
        _, tilt_angle = self.calc_rot_comp(tilt_local_target_pos)

        # Convert geometric angles to dynamixel angles
        pan_angle = num_to_range(pan_angle, 45, -45, 202.5, 247.5)
        tilt_angle = num_to_range(tilt_angle, 45, -45, 292.5, 337.5)

        # Set the dynamixel to the calculated angles
        self.dyna.set_sync_pos(round(pan_angle,2), round(tilt_angle,2))
        
        #  Get the current angles of the dynamixels
        pan_angle, tilt_angle = self.dyna.get_sync_pos()
        self.pan_angles.append(pan_angle)
        self.tilt_angles.append(tilt_angle)

    def shutdown(self) -> None:
        # print control frequency
        end_time = time.perf_counter()
        print(f"Control frequency: {self.counter / (end_time - self.start_time)} Hz")

        #  Shutdown QTM
        asyncio.run_coroutine_threadsafe(self.target._close(), asyncio.get_event_loop())

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
    perf_sleeper = PerfSleeper()
    
    try:

        while True:
            dyna_tracker.track()
            # perf_sleeper.sleep_ms(0.1)

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
    # run dart track until keyboard interrupt then shutdown
    dart_track()
        