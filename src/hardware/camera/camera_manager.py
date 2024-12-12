import time, cv2, logging, EasyPySpin, warnings, sys, numpy as np
from vidgear.gears import WriteGear
from threading import Thread
from queue import Queue
from pathlib import Path
from time import perf_counter_ns
from utils.perf_timings import perf_counter_ns

# Settings the warnings to be ignored 
warnings.filterwarnings('ignore') 

class CameraManager:
    """Manages camera operations including live feed and recording."""
    def __init__(self):
        self.logger = logging.getLogger("Camera")
        self.cap = None
        self.initialize_camera()

        # Initialize video recording params
        self.frame_queue = Queue()
        self.recording = False
        self.writer = None
        self.is_paused = False
        self.debug_overlay = False

        # Initialize frame streaming params
        self.latest_frame = None
        self.frame_thread = None
        self.is_reading = False

        # FPS measurement
        self.frame_times = []
        self.fps_window = 200  # Number of frames to average for FPS calculation
        self.measured_fps = None

        # Init cam props
        self.initialise_cam_props()

        self.writing = False

    def initialise_cam_props(self):
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size = (self.frame_width, self.frame_height)
        self.fps = round(self.cap.get(cv2.CAP_PROP_FPS), 2)

    def connect_camera(self, serial):
        """Connect to camera by serial number"""
        try:
            if self.cap:
                self.release()
                
            self.cap = EasyPySpin.VideoCapture(serial)
            if not self.cap.isOpened():
                self.logger.error(f"Failed to open camera {serial}")
                return False
                
            # Start acquisition
            self.cap.cam.BeginAcquisition()
            
            # Initialize camera properties
            self.initialise_cam_props()
            self.logger.info(f"Successfully connected to camera {serial}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to camera {serial}: {e}")
            return False
            
    def release(self):
        """Safely release camera resources"""
        try:
            if self.cap:
                # Stop frame thread if running
                if self.is_reading:
                    self.stop_frame_thread()
                    
                # Stop acquisition
                if self.cap.cam.IsStreaming():
                    self.cap.cam.EndAcquisition()
                    
                self.cap.release()
                self.cap = None
        except Exception as e:
            self.logger.error(f"Error releasing camera: {e}")

    def initialize_camera(self, camera_index=0):
        try:
            self.cap = EasyPySpin.VideoCapture(camera_index)
            if not self.cap.isOpened():  # Check if the camera has been opened successfully
                self.logger.error("Camera could not be opened.")
                return
            self.configure_camera()
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {e}")
            self.release()

    def configure_camera(self):
        # self.cap.set_pyspin_value('AcquisitionFrameRateEnable', False)
        # self.cap.set_pyspin_value('AcquisitionFrameRate', 201)
        pass

    def start_frame_thread(self):
        """Start frame reading thread and measure FPS"""
        self.is_reading = True
        
        # Reset and initialize FPS measurement
        self.frame_times = []
        self.measured_fps = None
        
        # Collect initial frame times for FPS measurement
        for _ in range(self.fps_window):
            ret, _ = self.cap.read()
            if ret:
                self.frame_times.append(time.perf_counter())
        
        # Calculate initial FPS
        if len(self.frame_times) >= 2:
            time_diffs = np.diff(self.frame_times)
            avg_time_diff = np.mean(time_diffs)
            self.measured_fps = 1.0 / avg_time_diff if avg_time_diff > 0 else None
            self.logger.info(f"Measured camera FPS: {self.measured_fps:.1f}")
        
        # Start the frame reading thread
        self.frame_thread = Thread(target=self.update_frame, daemon=True)
        self.frame_thread.start()

    def stop_frame_thread(self):
        self.is_reading = False
        if self.frame_thread is not None:
            self.frame_thread.join()
        self.frame_thread = None

    def update_frame(self):
        while self.is_reading:
            ret, frame = self.cap.read()
            if ret:
                self.latest_frame = frame
                
    def measure_fps(self):
        """Calculate FPS from the last fps_window frame timestamps"""
        if len(self.frame_times) < self.fps_window:
            # Collect frame times
            start_time = time.perf_counter()
            frame_count = 0
            
            while frame_count < self.fps_window:
                ret, _ = self.cap.read()
                if ret:
                    current_time = time.perf_counter()
                    self.frame_times.append(current_time)
                    frame_count += 1
            
            # Calculate initial FPS from collection period
            total_time = self.frame_times[-1] - self.frame_times[0]
            if total_time > 0:
                measured_fps = (len(self.frame_times) - 1) / total_time
                self.logger.info(f"Initial FPS measurement: {measured_fps:.1f}")
                return measured_fps
            
        # Calculate FPS using the last fps_window frames
        recent_times = self.frame_times[-self.fps_window:]
        time_diffs = np.diff(recent_times)
        avg_time_diff = np.mean(time_diffs)
        std_dev = np.std(time_diffs)
        
        measured_fps = 1.0 / avg_time_diff if avg_time_diff > 0 else None
        
        # Only accept FPS if measurement is stable
        if std_dev < 0.001:  # 1ms stability threshold
            self.logger.info(f"Measured FPS: {measured_fps:.1f} (±{std_dev*1000:.2f}ms)")
            return measured_fps
        else:
            self.logger.warning(f"Unstable frame timing - std dev: {std_dev*1000:.2f}ms")
            return None

    def queue_frames(self):
        self.frame_counter = 0
        self.frame_timestamps = []
        
        while self.recording:
            # Single timestamp call instead of pre/post
            frame_time = perf_counter_ns()
            ret, frame = self.cap.read()
            
            if ret:
                # Calculate timestamp relative to recording start
                frame_timestamp = (frame_time * 1e-6) - self.start_time_ms
                
                # Store frame metadata
                self.frame_timestamps.append(frame_timestamp)
                self.frame_counter += 1
                
                self.latest_frame = frame
                # Queue frame with its metadata
                self.frame_queue.put((frame, frame_timestamp, self.frame_counter))

    def start_recording(self, filename):
        """Start recording using pre-measured FPS"""
        # Use high-precision timer for start time
        self.start_time_ms = perf_counter_ns() * 1e-6
        
        # Reset frame recording variables
        self.frame_counter = 0
        self.frame_timestamps = []
        
        # Use pre-measured FPS or fallback to default
        actual_fps = self.measured_fps if self.measured_fps is not None else 200.0
        
        # Store metadata in filename
        base_name = Path(filename).stem
        extension = Path(filename).suffix
        directory = Path(filename).parent
        filename_with_metadata = directory / f"{base_name}_FPS{actual_fps:.1f}_START{self.start_time_ms:.0f}{extension}"

        # Configure output parameters
        output_params = {
            "-c:v": "libx264",
            "-input_framerate": 30,
            "-r": "30",
            "-preset": "ultrafast",
            "-crf": 22,
            "-ffmpeg_download_path": "_local/ffmpeg"
        }

        self.logger.info(f"Recording started:")
        self.logger.info(f"- FPS: {actual_fps:.1f}")
        self.logger.info(f"- Start time: {self.start_time_ms:.0f}ms")
        self.logger.info(f"- Output file: {filename_with_metadata.name}")

        # Start recording
        self.recording = True
        self.writer = WriteGear(
            output=str(filename_with_metadata), 
            compression_mode=True,
            logging=False, 
            **output_params
        )

        # Start frame queue and writing threads
        queue_thread = Thread(target=self.queue_frames, daemon=True)
        writing_thread = Thread(target=self.write_frames, daemon=True)
        queue_thread.start()
        writing_thread.start()

    def write_frames(self):
        """Write frames to video file with proper cleanup"""
        self.writing = True
        frames_written = 0
        
        try:
            while True:
                frame_data = self.frame_queue.get()
                
                # Check for stop signal
                if frame_data is None:
                    self.logger.info(f"Received stop signal. Total frames written: {frames_written}")
                    break
                
                # Unpack the tuple
                frame, timestamp, frame_number = frame_data
                
                if frame.size != 0:
                    # Only log every 100 frames to reduce console spam
                    if frame_number % 100 == 0:
                        self.logger.info(f"Writing frame {frame_number} at {timestamp:.2f}ms")
                    
                    # Convert ndarray to cv2.imshow compatible format
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    self.writer.write(frame)
                    frames_written += 1
                        
        except Exception as e:
            self.logger.error(f"Error in write_frames: {e}")
            
        finally:
            try:
                if self.writer:
                    self.logger.info("Closing video writer...")
                    self.writer.close()
                    self.logger.info("Video writer closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing writer: {e}")
                
            self.writing = False
            
            # Execute the callback function if provided
            if hasattr(self, 'on_write_finished') and self.on_write_finished:
                self.logger.info("Executing write finished callback")
                self.on_write_finished()
                
            self.logger.info(f"Write process completed. Total frames written: {frames_written}")

    def set_on_write_finished(self, callback):
        self.on_write_finished = callback

    def stop_recording(self):
        """Safely stop recording and ensure all frames are written"""
        self.logger.info("Stopping recording...")
        self.recording = False
        
        # Wait a short time for queue_frames to finish
        time.sleep(0.1)
        
        # Signal the end of the frame queue
        self.frame_queue.put(None)
        
        # Log final frame count
        self.logger.info(f"Recording stopped. Total frames: {self.frame_counter}")
        self.logger.info("Waiting for all frames to be written...")

    def get_available_cameras(self):
        cameras = []
        i = 0
        while True:
            try:
                cap = EasyPySpin.VideoCapture(i)
                if cap.isOpened():
                    cameras.append(f"Camera {i}")
                    cap.release()
                else:
                    break
            except:
                break
            i += 1
        return cameras

    def get_frame_timestamps(self):
        """Get the complete list of frame timestamps after recording"""
        if not self.frame_timestamps:
            self.logger.warning("No frame timestamps available")
            return []
        
        self.logger.info(f"Providing {len(self.frame_timestamps)} frame timestamps")
        return self.frame_timestamps.copy()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)

    camera_manager = CameraManager()
    
    video_path = "D:/Charlie/recorded_video.mkv"


    camera_manager.start_recording(video_path)

    # Record for 10 seconds
    time.sleep(10)

    camera_manager.stop_recording()

    # Release resources after recording finishes
    camera_manager.release()

    print("Recording stopped, video saved to:", video_path)