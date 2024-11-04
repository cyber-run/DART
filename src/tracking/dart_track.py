from utils.misc_funcs import set_realtime_priority, num_to_range
import logging, pickle, time, os, cProfile, asyncio, signal
from utils.perf_timings import perf_counter_ns
from hardware.motion.dyna_controller import *
from importlib import reload
from hardware.motion.theia_controller import TheiaController
from hardware.mocap.qtm_mocap import *
import numpy as np
import queue


class DynaTracker:
    '''
    Object to track a target using a Dynamixel servo and a QTM mocap system.
    
    - Before running this script, ensure that the Dynamixel servo is connected to
    the computer via USB and that the QTM mocap system is running and streaming
    data.
    - In QTM align
    '''
    def __init__(self, data_queue, com_port='COM5'):
        # Load calibration data if it exists
        if os.path.exists('config/calib_data.pkl'):
            with open('config/calib_data.pkl', 'rb') as f:
                self.pan_origin, self.tilt_origin, self.rotation_matrix, _ = pickle.load(f)
                logging.info("Calibration data loaded successfully.")
        else:
            logging.error("No calibration data found.")
            quit()

        # Create a queue to store data
        self.data_queue = data_queue

        # Connect to QTM; init tracker and target
        self.target = QTMStream()
        self.target_pos = None
        time.sleep(0.1)

        # Create dynamixel controller object and open serial port
        self.dyna = DynaController(com_port)
        self.dyna.open_port()

        self.dyna.set_gains(1, 2432, 720, 3200, 0)
        self.dyna.set_gains(2, 2432, 720, 3200, 0)
        
        # Default init operating mode into position
        self.dyna.set_op_mode(self.dyna.pan_id, 3)
        self.dyna.set_op_mode(self.dyna.tilt_id, 3)

        self.start_time = time.perf_counter()

        self.mean_origin = (self.pan_origin + self.tilt_origin) / 2

        self.theia = TheiaController(port="COM17")
        self.theia.connect()
        self.theia.initialise()

        # Define the data points
        distance_data = np.array([0.68, 1.05, 1.61, 1.110, 0.699])
        steps_data = np.array([0, 2000, 6000, 4000, 0])

        # Fit a polynomial curve (degree 2) to the data
        self.coefficients = np.polyfit(distance_data, steps_data, 2)
        # fit linear curve to the data
        self.dist = 0

        self.counter = 0

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
    
    # Create a function that takes distance as input and returns steps
    def distance_to_steps(self, distance: float) -> int:
        steps = int(np.polyval(self.coefficients, distance))

        # Check if the steps are within the limits
        if steps > 65535:
            steps = 65535
        elif steps < 0:
            steps = 0
            
        return steps

    def track(self):
        if self.target.lost:
            logging.info("Target lost. Skipping iteration.")
            return        
        logging.info("Tracking target.")
        
        self.target_pos = self.target.position

        distance = (np.linalg.norm(self.target_pos - self.mean_origin)/1000)

        # Check if the distance has changed significantly
        # If it has, move the Theia to the new distance and save dist val to object
        if abs(distance - self.dist) > 0.1:
            steps = (self.distance_to_steps(distance))
            print(f"Distance: {distance} Steps: {steps}")
            # self.theia._wait_till_status_change(1, self.theia.FOCUS_MOVE)
            steps = max(0, steps)
            self.theia.move_axis("B", steps)
            self.dist = distance

        # Get the local target position
        pan_local_target_pos = self.pan_global_to_local(self.target_pos)
        tilt_local_target_pos = self.tilt_global_to_local(self.target_pos)

        # Calculate the pan and tilt components of rotation from the positive X-axis
        pan_angle, _ = self.calc_rot_comp(pan_local_target_pos)
        _, tilt_angle = self.calc_rot_comp(tilt_local_target_pos)

        # Convert geometric angles to dynamixel angles
        pan_angle = round(num_to_range(pan_angle, 45, -45, 22.5, 67.5),2)
        tilt_angle = round(num_to_range(tilt_angle, 45, -45, 22.5, 67.5),2)

        # Set the dynamixel to the calculated angles
        self.dyna.set_sync_pos(pan_angle, tilt_angle)
        
        #  Get the current angles of the dynamixels
        encoder_pan_angle, encoder_tilt_angle = self.dyna.get_sync_pos()

        # Put the data into the queue in a non-blocking way
        data = (
            self.target_pos,
            pan_angle,
            tilt_angle,
            round(encoder_pan_angle,2),
            round(encoder_tilt_angle,2),
            perf_counter_ns() * 1e-6
        )
        try:
            self.data_queue.put_nowait(data)
        except queue.Full:
            logging.warning("Data queue is full. Skipping this data point.")

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

        # Close Theia connection
        self.theia.stop()

        return

def dart_track(data_queue, terminate_event):
    reload(logging)
    logging.basicConfig(level=logging.ERROR)

    set_realtime_priority()

    dyna_tracker = DynaTracker(data_queue)
    
    while not terminate_event.is_set():
        dyna_tracker.track()
        # time.sleep(0.1)
    
    dyna_tracker.shutdown()

if __name__ == '__main__':
    # cProfile.run('dart_track()')
    # run dart track until keyboard interrupt then shutdown
    dart_track()
        