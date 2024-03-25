import os, time, cv2, logging, EasyPySpin
from vidgear.gears import WriteGear
from threading import Thread
from queue import Queue


class CameraManager:
    def __init__(self):
        self.cap = None
        self.initialize_camera()

        # Get camera properties
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size = (self.frame_width, self.frame_height)
        self.fps = round(self.cap.get(cv2.CAP_PROP_FPS), 2)

        # Initialize video recording params
        self.frame_queue = Queue()
        self.recording = False
        self.writer = None
        self.writing_thread = None

        self.latest_frame = None
        self.frame_thread = None
        self.is_reading = False
        self.start_t = None
        self.is_paused = False
        # self.frame_counter = 0
    
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
        # self.cap.set_pyspin_value('AcquisitionFrameRateEnable', False)
        # self.cap.set_pyspin_value('AcquisitionFrameRate', 201)
        pass

    def release(self):
        if self.cap:
            self.cap.release()

    def start_frame_thread(self):
        self.is_reading = True
        self.frame_thread = Thread(target=self.update_frame, daemon=True)
        self.frame_thread.start()
        self.start_t = time.perf_counter()

    def stop_frame_thread(self):
        self.is_reading = False
        if self.frame_thread is not None:
            self.frame_thread.join()
        self.frame_thread = None
        # print(f"Frames processed: {self.frame_counter} in {time.perf_counter() - self.start_t:.4f} s")
        # print(f"Frame rate: {self.frame_counter/(time.perf_counter() - self.start_t):.4f} fps")
        # self.frame_counter = 0

    def update_frame(self):
        while self.is_reading:
            ret, frame = self.cap.read()
            if ret:
                # self.frame_counter += 1
                # Flip frame verically
                frame = cv2.flip(frame, 0)
                self.latest_frame = frame
                
    def start_recording(self, filename):
        # cv2 writer parameters
        # fourcc = cv2.VideoWriter_fourcc(*'H264')
        # self.writer = cv2.VideoWriter(filename, fourcc, self.fps, self.frame_size, isColor=False)

        # Vidgear wrtier parameters
        output_params = {
            "-input_framerate": 30,
            "-r" : 30,
            "-preset": "ultrafast",
            "-crf": 18
        }
        # Define writer with defined parameters and suitable output filename for e.g. `Output.mp4
        self.writer = WriteGear(output=filename, logging=False, **output_params)

        self.recording = True

        Thread(target=self.queue_frames, daemon=True).start()
        self.writing_thread = Thread(target=self.write_frames)
        self.writing_thread.start()

    def queue_frames(self):
        while self.recording:
            logging.info("Capturing frame.")
            ret, frame = self.cap.read()

            # Flip frame verically
            frame = cv2.flip(frame, 0)

            if ret:
                self.latest_frame = frame
                self.frame_queue.put(self.latest_frame)
                logging.info("Queueing frame.")

        # Signal the end of the frame queue via sentinel value
        self.frame_queue.put(None)

    def write_frames(self):
        while not self.frame_queue.empty() or self.recording:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                if frame is not None and frame.size != 0:
                    logging.info("Writing frame...")
                    # Convert ndarray to cv2.imshow compatible format
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    self.writer.write(frame)
            else:
                time.sleep(0.001)  # Add a small delay to avoid excessive CPU usage

        self.writer.close()
        
        # Execute the callback function if provided
        if self.on_write_finished:
            self.on_write_finished()

    def set_on_write_finished(self, callback):
        self.on_write_finished = callback

    def stop_recording(self):
        self.recording = False


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