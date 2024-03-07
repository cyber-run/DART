import os
import time
import cv2
import logging
from threading import Thread
from queue import Queue
import EasyPySpin

class CameraManager:
    def __init__(self):
        self.cap = None
        self.initialize_camera()
        self.frame_queue = Queue()
        self.recording = False
        self.writer = None
        self.latest_frame = None  # Add an attribute to store the latest frame
    
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

    def initialize_camera(self, camera_index=0):
        try:
            self.cap = EasyPySpin.VideoCapture(camera_index)
            if not self.cap.isOpened():  # Check if the camera has been opened successfully
                logging.error("Camera could not be opened.")
                return
            self.configure_camera()
        except Exception as e:
            logging.error(f"Failed to initialize camera: {e}")
            if self.cap is not None:
                self.cap.release()

    def connect_camera(self, camera_index):
        self.release()
        self.initialize_camera(camera_index)

    def configure_camera(self):
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FPS, True)  # Set the camera to high FPS mode (if available)
            self.cap.set(cv2.CAP_PROP_FPS, 220)  # Set the FPS to 220

    def read_frame(self):
        try:
            if self.cap and self.cap.isOpened():
                frame  = self.cap.read()
                return frame
        except Exception as e:
            logging.error(f"Error reading frame: {e}")
        return False, None

    def start_recording(self, filename, fps=200, frame_size=(1440, 1080)):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Change to MJPG for wider compatibility
        filename = filename.replace('.avi', '.mp4')  # Ensure MP4 extension
        self.writer = cv2.VideoWriter(filename, int(fourcc), fps, frame_size)
        if not self.writer.isOpened():
            logging.error("Failed to open video writer. Check codec and file path.")
            return  # Stop the recording process if writer fails to initialize
        self.recording = True
        Thread(target=self.capture_frames, daemon=True).start()
        Thread(target=self.write_frames, daemon=True).start()

    def capture_frames(self):
        while self.recording:
            logging.info("Capturing frame...")
            ret, frame = self.read_frame()
            if ret:
                self.latest_frame = frame  # Update the latest frame
                self.frame_queue.put(frame)
                logging.info("Queueing frame.")
    
    def get_latest_frame(self):
        """Retrieve the latest frame captured by the camera."""
        return self.latest_frame

    def write_frames(self):
        while self.recording or not self.frame_queue.empty():
            frame = self.frame_queue.get()
            if frame is not None and frame.size != 0:
                logging.info("Writing frame...")
                # Display and save the resulting frame    
                self.writer.write(frame)

    def stop_recording(self):
        self.recording = False
        time.sleep(0.5)  # Give time for threads to finish
        self.writer.release()
        self.writer = None

    def release(self):
        if self.cap:
            self.cap.release()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    camera_manager = CameraManager()
    time.sleep(5)  # Allow time for the camera to initialize
    width  = int(camera_manager.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera_manager.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_x = camera_manager.cap.get(cv2.CAP_PROP_FPS)

    print(f"Camera initialized with resolution {width}x{height} and FPS {fps_x}")
    
    video_filename = os.path.join(os.getcwd(), "recorded_video.mp4")  # Ensure correct extension for codec
    camera_manager.start_recording(video_filename, fps=fps_x, frame_size=(width, height))
    
    start_time = time.time()
    duration = 10  # Record for 10 seconds
    
    while time.time() - start_time < duration:
        frame = camera_manager.get_latest_frame()
        logging.info("Getting latest frame...")
        if frame is not None:
            print("Displaying frame...")  # Debug print
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to exit early
                break
    
    camera_manager.stop_recording()
    camera_manager.release()
    cv2.destroyAllWindows()  # Close the window after recording is stopped
    print("Recording stopped, video saved to:", video_filename)
