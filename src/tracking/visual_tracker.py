import cv2
import numpy as np
import logging
from utils.misc_funcs import num_to_range
from hardware.motion.dyna_controller import DynaController
from hardware.camera.camera_manager import CameraManager
from multiprocessing import Queue
import time
import queue
from utils.perf_timings import perf_counter_ns

class VisualTracker:
    def __init__(self, data_queue: Queue, config: dict):
        self.logger = logging.getLogger("VisualTracker")
        self.data_queue = data_queue
        
        # Get tracking parameters from config
        visual_config = config["tracking"]["visual_tracking"]
        self.min_contour_area = visual_config["min_contour_area"]
        
        self.logger.info("Initializing visual tracking...")
        
        # Initialize camera
        self.camera = CameraManager()
        if not self.camera.connect_camera(config["devices"]["cameras"]["tracking"]):
            raise RuntimeError("Failed to connect to tracking camera")
        self.logger.info("Connected to tracking camera")
        
        # Setup camera parameters
        self.setup_camera()
        self.logger.info("Camera parameters configured")
        
        # Initialize Dynamixel
        self.dyna = DynaController(config["devices"]["dynamixel_port"])
        if not self.dyna.open_port():
            raise RuntimeError("Failed to connect to Dynamixel")
        self.logger.info("Connected to Dynamixel")
        
        self.setup_motors()
        
        # Initialize background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=20,          # Shorter history for faster adaptation (was 50)
            varThreshold=8,     # Lower threshold for higher sensitivity (was 16)
            detectShadows=False  # Keep disabled for speed
        )
        
        self.start_time = time.perf_counter()
        self.counter = 0
        
        # Add performance tracking
        self.perf_stats = {
            'frame_read': [],
            'processing': [],
            'motor_control': [],
            'total_loop': []
        }

    def setup_motors(self):
        """Initialize motor settings"""
        self.dyna.set_gains(1, 2432, 720, 3200, 0)
        self.dyna.set_gains(2, 2432, 720, 3200, 0)
        self.dyna.set_op_mode(self.dyna.pan_id, 3)
        self.dyna.set_op_mode(self.dyna.tilt_id, 3)

    def setup_camera(self):
        """Configure camera settings"""
        try:
            # Set acquisition parameters
            self.camera.cap.set_pyspin_value("AcquisitionFrameRateEnable", True)
            self.camera.cap.set_pyspin_value("AcquisitionFrameRate", 400.0)
            self.camera.cap.set_pyspin_value("DeviceLinkThroughputLimit", 200000000)
            
            # Set exposure and gain
            self.camera.cap.set(cv2.CAP_PROP_EXPOSURE, 500)
            self.camera.cap.set(cv2.CAP_PROP_GAIN, 10)
            
        except Exception as e:
            self.logger.warning(f"Could not set some camera parameters: {e}")

    def process_frame(self, frame):
        """Process frame using MOG2 background subtraction"""
        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(gray)
        
        # Reduced blur for finer detail
        fg_mask = cv2.medianBlur(fg_mask, 3)  # Was 5
        
        # Find contours of moving objects
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            # Lower area threshold for smaller movements
            if area > 100:  # Was 500
                # Get centroid
                M = cv2.moments(largest_contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    return cx, cy, fg_mask
        
        return None

    def track(self):
        """Main tracking loop"""
        loop_start = perf_counter_ns()
        self.counter += 1
        
        # Time frame capture
        t0 = perf_counter_ns()
        ret, frame = self.camera.cap.read()
        t1 = perf_counter_ns()
        frame_time = (t1 - t0) * 1e-6
        self.perf_stats['frame_read'].append(frame_time)
        
        if not ret:
            self.logger.error("Failed to grab frame")
            return
        
        # Time frame processing
        t0 = perf_counter_ns()
        result = self.process_frame(frame)
        t1 = perf_counter_ns()
        process_time = (t1 - t0) * 1e-6
        self.perf_stats['processing'].append(process_time)
        
        if result:
            cx, cy, mask = result
            # Calculate angles and update motors
            height, width = frame.shape[:2]
            fx, fy = 800, 800
            center_x, center_y = width // 2, height // 2
            
            # Calculate raw angles
            pan_angle = np.degrees(np.arctan((cx - center_x) / fx))
            tilt_angle = -np.degrees(np.arctan((cy - center_y) / fy))
            
            # Only move if change is significant and limit both angles to safe range
            if abs(pan_angle) > 0.1 or abs(tilt_angle) > 0.1:
                # Map both angles to the same safe range (20.5 to 65.5)
                pan_angle = round(num_to_range(pan_angle, -45, 45, 20.5, 65.5), 2)
                tilt_angle = round(num_to_range(tilt_angle, -45, 45, 20.5, 65.5), 2) + 3
                
                # Additional safety clamp
                pan_angle = max(20.5, min(65.5, pan_angle))
                tilt_angle = max(20.5, min(65.5, tilt_angle))
                
                # Time motor control
                t0 = perf_counter_ns()
                self.dyna.set_sync_pos(pan_angle, tilt_angle)
                encoder_pan, encoder_tilt = self.dyna.get_sync_pos()
                t1 = perf_counter_ns()
                motor_time = (t1 - t0) * 1e-6
                self.perf_stats['motor_control'].append(motor_time)
                
                # Put data in queue
                try:
                    data = (
                        np.array([cx, cy, 0]),
                        pan_angle,
                        tilt_angle,
                        round(encoder_pan, 2),
                        round(encoder_tilt, 2),
                        time.perf_counter_ns() * 1e-6
                    )
                    self.data_queue.put_nowait(data)
                except queue.Full:
                    self.logger.debug("Data queue is full")
        
        # Calculate total loop time
        loop_end = perf_counter_ns()
        total_time = (loop_end - loop_start) * 1e-6
        self.perf_stats['total_loop'].append(total_time)

    def shutdown(self):
        """Clean up resources"""
        end_time = time.perf_counter()
        freq = self.counter / (end_time - self.start_time)
        self.logger.info(f"Visual tracking frequency: {freq:.2f} Hz")
        
        # Log performance statistics
        for key, times in self.perf_stats.items():
            if times:
                avg_time = sum(times) / len(times)
                self.logger.info(f"Average {key} time: {avg_time:.2f} ms")
        
        if self.dyna:
            self.dyna.close_port()
        if self.camera:
            self.camera.release() 