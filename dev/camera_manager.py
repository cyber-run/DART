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

        # Get camera properties
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size = (self.frame_width, self.frame_height)
        self.fps = round(self.cap.get(cv2.CAP_PROP_FPS),2)

        # Initialize video recording params
        self.frame_queue = Queue()
        self.recording = False
        self.writer = None
        self.latest_frame = None
        self.writing_thread = None
    
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

    def connect_camera(self, camera_index):
        self.release()
        self.initialize_camera(camera_index)

    def initialize_camera(self, camera_index=0):
        try:
            self.cap = EasyPySpin.VideoCapture(camera_index)
            if not self.cap.isOpened():  # Check if the camera has been opened successfully
                logging.error("Camera could not be opened.")
                return
            self.configure_camera()
        except Exception as e:
            logging.error(f"Failed to initialize camera: {e}")
            self.release()

    def configure_camera(self):
        self.cap.set_pyspin_value('AcquisitionFrameRateEnable', True)
        self.cap.set_pyspin_value('AcquisitionFrameRate', 220)

    def release(self):
        if self.cap:
            self.cap.release()

    def start_recording(self, filename):

        fourcc = cv2.VideoWriter_fourcc(*'H264')

        self.writer = cv2.VideoWriter(filename, fourcc, self.fps, self.frame_size, isColor=False)

        if self.writer.isOpened():
            self.writer.set(cv2.VIDEOWRITER_PROP_QUALITY, 50)  # Adjust quality (0-100)
        else:
            logging.error("Failed to open video writer. Check codec and file path.")
            return  # Stop the recording process if writer fails to initialize
        
        self.recording = True

        Thread(target=self.queue_frames, daemon=True).start()
        self.writing_thread = Thread(target=self.write_frames)
        self.writing_thread.start()

    def queue_frames(self):

        while self.recording:
            logging.info("Capturing frame.")
            ret, frame = self.cap.read()

            if ret:
                self.latest_frame = frame
                self.frame_queue.put(self.latest_frame)
                logging.info("Queueing frame.")
        
        # Signal the end of the frame queue via sentienel value
        self.frame_queue.put(None)

    def write_frames(self):

        while True:
            frame = self.frame_queue.get()

            if frame is None:
                break  # Stop writing when the sentinel value is received

            if frame is not None and frame.size != 0:
                logging.info("Writing frame...")
                # Display and save the resulting frame    
                self.writer.write(frame)

        self.writer.release()

    def stop_recording(self):
        self.recording = False
        if self.writing_thread is not None:
            self.writing_thread.join()
        self.writer = None

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