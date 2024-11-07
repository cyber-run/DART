from utils.misc_funcs import set_realtime_priority, num_to_range
import logging, time, asyncio
from utils.perf_timings import perf_counter_ns
from hardware.motion.dyna_controller import *
from importlib import reload
from hardware.motion.theia_controller import TheiaController
from hardware.mocap.qtm_mocap import *
import numpy as np
import queue
import threading
import math
from core.config_manager import ConfigManager
from tracking.kalman_filter import AdaptiveKalmanFilter


class DynaTracker:
    '''
    Object to track a target using a Dynamixel servo and a QTM mocap system.
    
    - Before running this script, ensure that the Dynamixel servo is connected to
      the computer via USB and that the QTM mocap system is running and streaming
      data.
    '''
    def __init__(self, data_queue):
        self.logger = logging.getLogger("Track")
        # Configure logging for this process with a console handler
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # Load configuration
        self.config = ConfigManager()
        
        # Get calibration data from config
        pan_origin, tilt_origin, rotation_matrix = self.config.get_calibration_data()
        if pan_origin is None or tilt_origin is None or rotation_matrix is None:
            self.logger.error("No calibration data found in config.")
            raise ValueError("Calibration data not found")
            
        self.pan_origin = pan_origin
        self.tilt_origin = tilt_origin
        self.rotation_matrix = rotation_matrix
        self.logger.info("Calibration data loaded successfully.")

        # Get device configuration
        device_config = self.config.config["devices"]
        dyna_port = device_config["dynamixel_port"]
        theia_port = device_config["theia_port"]
        
        if not dyna_port or not theia_port:
            self.logger.error("Motor controller ports not configured")
            raise ValueError("Motor controller configuration missing")

        # Create a queue to store data
        self.data_queue = data_queue

        # Connect to QTM; init tracker and target
        self.target = QTMStream()
        self.target_pos = None
        time.sleep(0.1)

        # Create dynamixel controller object and open serial port
        self.dyna = DynaController(dyna_port)  # Use configured port
        self.dyna.open_port()

        self.dyna.set_gains(1, 2432, 720, 3200, 0)
        self.dyna.set_gains(2, 2432, 720, 3200, 0)
        
        # Default init operating mode into position
        self.dyna.set_op_mode(self.dyna.pan_id, 3)
        self.dyna.set_op_mode(self.dyna.tilt_id, 3)

        self.start_time = time.perf_counter()

        self.mean_origin = (self.pan_origin + self.tilt_origin) / 2

        # Initialize Theia with saved positions from config
        self.theia = TheiaController(port=theia_port)
        self.theia.connect()
        self.theia.initialise()
        
        # Get stored positions from config
        theia_state = self.config.config["devices"]["theia_state"]
        zoom_position = theia_state.get("zoom_position", 0)
        focus_position = theia_state.get("focus_position", 0)
        
        # Set the controller's absolute positions
        self.theia.set_absolute_position("A", zoom_position)  # Zoom
        self.theia.set_absolute_position("B", focus_position)  # Focus
        
        self.logger.info(f"Initialized Theia with saved positions - Zoom: {zoom_position}, Focus: {focus_position}")

        # Define the data points
        distance_data = np.array([0.68, 1.05, 1.61, 1.110, 0.699])
        steps_data = np.array([0, 2000, 6000, 4000, 0])

        # Fit a polynomial curve (degree 2) to the data
        self.coefficients = np.polyfit(distance_data, steps_data, 2)
        self.dist = 0

        self.counter = 0

        # Initialize Kalman Filter only if enabled in config
        self.use_kalman = self.config.config["tracking"].get("use_kalman", True)
        self.kalman = AdaptiveKalmanFilter() if self.use_kalman else None
        self.last_time = time.perf_counter()

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
        tilt_angle = math.degrees(math.atan2(point_local[2], math.hypot(point_local[0], point_local[1])))
        return pan_angle, tilt_angle
    
    # Create a function that takes distance as input and returns steps
    def distance_to_steps(self, distance: float) -> int:
        steps = int(np.polyval(self.coefficients, distance))

        # Check if the steps are within the limits
        steps = max(0, min(steps, 65535))
        return steps

    def track(self):
        if self.use_kalman:
            current_time = time.perf_counter()
            delta_t = current_time - self.last_time
            self.last_time = current_time

            # Update Kalman filter time step
            self.kalman.update_F(delta_t)

            if self.target.lost:
                self.logger.debug("Target lost. Predicting position.")
                self.kalman.predict()
            else:
                # Get the latest measurement
                measurement = np.array(self.target.position).reshape((3, 1))
                self.kalman.predict()
                self.kalman.update(measurement)
                self.kalman.adapt_Q(measurement)

            # Latency compensation
            latency_duration = 0.003  # Total latency in seconds (3 ms)
            self.kalman.predict_latency(latency_duration)

            # Get estimated position
            estimated_position = self.kalman.get_position()
        else:
            # Use raw target position when Kalman is disabled
            if self.target.lost:
                self.logger.debug("Target lost.")
                return
            estimated_position = np.array(self.target.position)

        distance = (np.linalg.norm(estimated_position - self.mean_origin) / 1000)

        # Check if the distance has changed significantly
        if abs(distance - self.dist) > 0.1:
            steps = self.distance_to_steps(distance)
            self.logger.info(f"Distance: {distance} Steps: {steps}")
            steps = max(0, steps)
            self.theia.move_axis("B", steps)
            self.dist = distance

        # Get the local target position
        pan_local_target_pos = self.pan_global_to_local(estimated_position)
        tilt_local_target_pos = self.tilt_global_to_local(estimated_position)

        # Calculate the pan and tilt components of rotation from the positive X-axis
        pan_angle, _ = self.calc_rot_comp(pan_local_target_pos)
        _, tilt_angle = self.calc_rot_comp(tilt_local_target_pos)

        # Convert geometric angles to dynamixel angles
        pan_angle = round(num_to_range(pan_angle, 45, -45, 22.5, 67.5), 2)
        tilt_angle = round(num_to_range(tilt_angle, 45, -45, 22.5, 67.5), 2)

        # Set the dynamixel to the calculated angles
        self.dyna.set_sync_pos(pan_angle, tilt_angle)
        
        # Get the current angles of the dynamixels
        encoder_pan_angle, encoder_tilt_angle = self.dyna.get_sync_pos()

        # Put the data into the queue in a non-blocking way
        data = (
            estimated_position,
            pan_angle,
            tilt_angle,
            round(encoder_pan_angle, 2),
            round(encoder_tilt_angle, 2),
            perf_counter_ns() * 1e-6
        )
        try:
            self.data_queue.put_nowait(data)
        except queue.Full:
            self.logger.debug("Data queue is full. Skipping this data point.")

        self.counter += 1

    def shutdown(self) -> None:
        self.logger.info("Shutting down.")
        # Print control frequency
        end_time = time.perf_counter()
        self.logger.info(f"Control frequency: {self.counter / (end_time - self.start_time)} Hz")
    
        # Retrieve current lens positions
        try:
            zoom_position, focus_position = self.theia.get_current_positions()
            if zoom_position is not None and focus_position is not None:
                self.logger.info(f"Current Theia positions - Zoom: {zoom_position}, Focus: {focus_position}")
                # Save positions to config
                self.config.update_theia_position(zoom=zoom_position, focus=focus_position)
                self.config.save_config()  # Ensure the config is saved to file
                self.logger.info("Lens positions saved to configuration.")
            else:
                self.logger.warning("Could not retrieve current lens positions.")
        except Exception as e:
            self.logger.error(f"Error retrieving lens positions during shutdown: {e}")
    
        # Shutdown QTM
        asyncio.run_coroutine_threadsafe(self.target._close(), asyncio.get_event_loop())
    
        # Close QTM connections
        self.target.close()
    
        # Close serial port
        self.dyna.close_port()
    
        # Close Theia connection
        self.theia.disconnect()
    
        return

def dart_track(data_queue, terminate_event):
    set_realtime_priority()
    
    dyna_tracker = DynaTracker(data_queue)

    dyna_tracker.logger.info("Starting tracking.")
    
    while not terminate_event.is_set():
        dyna_tracker.track()
    
    dyna_tracker.shutdown()

if __name__ == '__main__':
    data_queue = queue.Queue(maxsize=1)  # Adjust maxsize as needed
    terminate_event = threading.Event()
    try:
        dart_track(data_queue, terminate_event)
    except KeyboardInterrupt:
        terminate_event.set()
