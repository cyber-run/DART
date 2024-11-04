from utils.misc_funcs import set_realtime_priority, num_to_range
import logging, pickle, time, os, cProfile, asyncio, signal
from utils.perf_timings import perf_counter_ns
from hardware.motion.dyna_controller import *
from importlib import reload
from hardware.motion.theia_controller import TheiaController
from hardware.mocap.qtm_mocap import *
import numpy as np
import queue
import threading  # Ensure threading is imported
import math  # Import math module for calculations


class DynaTracker:
    '''
    Object to track a target using a Dynamixel servo and a QTM mocap system.
    
    - Before running this script, ensure that the Dynamixel servo is connected to
      the computer via USB and that the QTM mocap system is running and streaming
      data.
    '''
    def __init__(self, data_queue, com_port='COM5'):
        # Load calibration data if it exists
        if os.path.exists('config/calib_data.pkl'):
            with open('config/calib_data.pkl', 'rb') as f:
                self.pan_origin, self.tilt_origin, self.rotation_matrix, _ = pickle.load(f)
                logging.info("Calibration data loaded successfully.")
        else:
            logging.error("No calibration data found.")
            raise FileNotFoundError("Calibration data not found at 'config/calib_data.pkl'")

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
        self.dist = 0

        self.counter = 0

        # Initialize Kalman Filter parameters
        self.dim_x = 9  # State vector dimension (position, velocity, acceleration in 3D)
        self.dim_z = 3  # Measurement vector dimension (position in 3D)

        self.state_estimate = np.zeros((self.dim_x, 1))  # Initial state estimate
        self.estimate_covariance = np.eye(self.dim_x) * 1e-3  # Initial covariance

        # State Transition Matrix F
        self.F = np.eye(self.dim_x)

        # Observation Matrix H
        self.H = np.zeros((self.dim_z, self.dim_x))
        self.H[:3, :3] = np.eye(3)

        # Process Noise Covariance Q
        self.Q0 = np.eye(self.dim_x) * 1e-6  # Initial process noise covariance
        self.Q = self.Q0.copy()

        # Measurement Noise Covariance R
        self.R = np.eye(self.dim_z) * 1e-4  # Measurement noise covariance

        # Adaptive Kalman Filter parameters
        self.alpha = 1.0  # Adaptive factor
        self.alpha_min = 0.1
        self.alpha_max = 10.0
        self.expected_innovation_variance = 1e-3  # Expected innovation variance

        # Time management
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

    def create_F(self, delta_t):
        dt = delta_t
        dt2 = 0.5 * dt ** 2
        F = np.eye(self.dim_x)
        # Update F matrix for constant acceleration model
        F[:3, 3:6] = np.eye(3) * dt
        F[:3, 6:9] = np.eye(3) * dt2
        F[3:6, 6:9] = np.eye(3) * dt
        return F

    def update_F(self, delta_t):
        self.F = self.create_F(delta_t)

    def predict(self):
        self.state_estimate = self.F @ self.state_estimate
        self.estimate_covariance = self.F @ self.estimate_covariance @ self.F.T + self.Q

    def update(self, measurement):
        S = self.H @ self.estimate_covariance @ self.H.T + self.R
        K = self.estimate_covariance @ self.H.T @ np.linalg.inv(S)
        y = measurement - self.H @ self.state_estimate
        self.state_estimate = self.state_estimate + K @ y
        I = np.eye(self.dim_x)
        self.estimate_covariance = (I - K @ self.H) @ self.estimate_covariance

    def compute_alpha(self, normalized_innovation):
        expected_variance = self.expected_innovation_variance
        alpha = 1 + (normalized_innovation - expected_variance) / expected_variance
        alpha = max(self.alpha_min, min(alpha, self.alpha_max))
        return alpha

    def predict_latency(self, latency_duration):
        # Create state transition matrix for latency duration
        F_latency = self.create_F(latency_duration)
        # Predict state forward by latency duration
        self.state_estimate = F_latency @ self.state_estimate
        self.estimate_covariance = F_latency @ self.estimate_covariance @ F_latency.T + self.Q

    def track(self):
        current_time = time.perf_counter()
        delta_t = current_time - self.last_time
        self.last_time = current_time

        # Update F with new delta_t
        self.update_F(delta_t)

        if self.target.lost:
            logging.info("Target lost. Predicting position.")
            self.predict()
        else:
            # Get the latest measurement
            measurement = np.array(self.target.position).reshape((3, 1))
            self.predict()
            self.update(measurement)

            # Adapt Q based on innovation
            innovation = measurement - self.H @ self.state_estimate
            innovation_covariance = self.H @ self.estimate_covariance @ self.H.T + self.R
            normalized_innovation = innovation.T @ np.linalg.inv(innovation_covariance) @ innovation

            # Update adaptive factor alpha
            self.alpha = self.compute_alpha(normalized_innovation)
            self.Q = self.alpha * self.Q0  # Update Q

        # Latency compensation: Predict state forward by latency duration
        latency_duration = 0.003  # Total latency in seconds (3 ms)
        self.predict_latency(latency_duration)

        estimated_position = self.state_estimate[:3].flatten()
        logging.info("Tracking target.")

        distance = (np.linalg.norm(estimated_position - self.mean_origin) / 1000)

        # Check if the distance has changed significantly
        if abs(distance - self.dist) > 0.1:
            steps = self.distance_to_steps(distance)
            print(f"Distance: {distance} Steps: {steps}")
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
            logging.warning("Data queue is full. Skipping this data point.")

        self.counter += 1

    def shutdown(self) -> None:
        # Print control frequency
        end_time = time.perf_counter()
        print(f"Control frequency: {self.counter / (end_time - self.start_time)} Hz")

        # Shutdown QTM
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
        # No sleep to maintain high update rate
    
    dyna_tracker.shutdown()

if __name__ == '__main__':
    data_queue = queue.Queue(maxsize=1)  # Adjust maxsize as needed
    terminate_event = threading.Event()
    try:
        dart_track(data_queue, terminate_event)
    except KeyboardInterrupt:
        terminate_event.set()
