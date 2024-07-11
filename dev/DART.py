import logging
logging.basicConfig(level=logging.ERROR)

from misc_funcs import num_to_range, set_realtime_priority
from perf_timer import perf_counter_ns
import cProfile, time, cv2, os, asyncio, psutil, signal
from dyna_controller import DynaController
from camera_manager import CameraManager
from image_processor import ImageProcessor
from CTkMessagebox import CTkMessagebox
from multiprocessing import Process, Queue, Event
from data_handler import DataHandler
from dart_track import dart_track
from calibrate import Calibrator
import serial.tools.list_ports
import customtkinter as ctk
from dart_gui import DARTGUI
from qtm_mocap import *
from PIL import Image
import tkinter as tk
import numpy as np


class DART:
    def __init__(self, window: ctk.CTk):
        self.init_window(window)
        self.window.bind("<Configure>", self.on_configure)

        self.init_hardware()

        self.init_params()
        self.gui = DARTGUI(window, self)

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def init_window(self, window):
        self.window = window
        self.window.title("DART")

        # Set the minimum window size to the initial size
        self.window.geometry("1440x1080")
        self.window.minsize(1440, 1080)

    def init_hardware(self):
        # Create an instance of ImageProcessor
        self.image_pro = ImageProcessor()

        # Create an instance of CameraManager
        self.camera_manager = CameraManager()

        # Create an instance of Calibrator
        self.calibrator = Calibrator()

        self.selected_com_port = ctk.StringVar(value="")
        self.selected_camera = ctk.StringVar(value="")
        
        # Initialize QTM and Dynamixel controller objects
        self.qtm_stream = None

        self.dyna = None

    def init_params(self):
        # Camera/image functionality
        self.is_live = False
        self.video_path = "dev/recordings"

        # Image processing GUI flags
        self.torque_flag = tk.BooleanVar(value=False)
        self.show_crosshair = tk.BooleanVar(value=False)
        self.threshold_flag = tk.BooleanVar(value=False)
        self.detect_flag = tk.BooleanVar(value=False)

        # GUI icons/assets
        self.refresh_icon = ctk.CTkImage(Image.open("src/icons/refresh.png"), size=(20, 20))
        self.sync_icon = ctk.CTkImage(Image.open("src/icons/sync.png"), size=(20, 20))
        self.play_icon = ctk.CTkImage(Image.open("src/icons/play.png"), size=(20, 20))
        self.stop_icon = ctk.CTkImage(Image.open("src/icons/stop.png"), size=(20, 20))
        self.folder_icon = ctk.CTkImage(Image.open("src/icons/folder.png"), size=(20, 20))
        self.record_icon = ctk.CTkImage(Image.open("src/icons/record.png"), size=(20, 20))
        self.qtm_stream_icon = ctk.CTkImage(Image.open("src/icons/target.png"), size=(20, 20))
        self.pause_icon = ctk.CTkImage(Image.open("src/icons/pause.png"), size=(20, 20))
        self.placeholder_image = ctk.CTkImage(Image.new("RGB", (1200, 900), "black"), size=(1200, 900))
        self.small_placeholder_image = ctk.CTkImage(Image.new("RGB", (300, 225), "black"), size=(800, 600))
        self.home_icon = ctk.CTkImage(Image.open("src/icons/track.png"), size=(30, 30))
        self.data_icon = ctk.CTkImage(Image.open("src/icons/data.png"), size=(30, 30))

        self.app_status = "Idle"
        self.file_name = None

        # Motor control values
        self.pan_value = 0
        self.tilt_value = 0

        # Tracking process flag
        self.track_process = None

        # Memory usage var
        self.memory_usage = None

    def get_mem(self):
        # Get system memory usage as a percentage
        self.memory_usage = psutil.virtual_memory()[2]

        # Update memory usage label
        self.memory_label.configure(text=f"Memory usage: {self.memory_usage}%")

        # Update memory usage at 0.2Hz
        self.mem_id = self.window.after(5000, self.get_mem)

    def calibrate(self):
        p1 = np.array(self.qtm_stream.position)
        p2 = np.array(self.qtm_stream.position2)
        self.calibrator.run(p1, p2)

    def track(self):
        if self.track_process is not None:
            self.terminate_event.set()
            self.track_process.join()
            self.track_process = None
            self.connect_dyna_controller()
            self.track_button.configure(text="Track", image=self.play_icon)
            return
        
        if self.calibrator.calibrated and self.track_process is None:
            # Close QTM connections
            self.qtm_stream._close()
            self.qtm_stream.close()

            # Close serial port
            self.dyna.close_port()

            # Create instance of queue for retrieving data
            self.data_queue = Queue(maxsize=1)

            # Create and start the tracking process
            self.terminate_event = Event()
            self.track_process = Process(target=dart_track, args=(self.data_queue, self.terminate_event))
            self.track_process.start()

            self.track_process.pid

            self.track_button.configure(text="Stop", image=self.stop_icon)
        else:
            # Add popup window to notify user that DART is not calibrated
            CTkMessagebox(title="Error", message="DART Not Calibrated", icon="cancel")
            logging.error("DART is not calibrated.")

    def toggle_video_feed(self):
        self.is_live = not self.is_live
        self.toggle_video_button.configure(text="Stop" if self.is_live else "Start")
        self.toggle_video_button.configure(image=self.stop_icon if self.is_live else self.play_icon)
        if self.is_live:
            self.camera_manager.start_frame_thread()
            self.update_video_label()
        else:
            self.camera_manager.stop_frame_thread()

    def toggle_record(self):
        # If camera manager is not recording, start recording
        if self.record_button.cget("text") == "Record":
            # Stop the stream frame thread if it's running
            if self.camera_manager.is_reading:
                self.camera_manager.stop_frame_thread()

            # Get current timestamp and entry field for recording filename
            timestamp = time.strftime("%d%mT%H%M%S")
            file_name = self.file_name_entry.get().strip()

            # Set the file name to a default value if it's empty
            if file_name:
                video_name = f"{file_name}_{timestamp}.mp4"
                data_name = f"{file_name}_{timestamp}.parquet"
            else:
                video_name = f"video_{timestamp}.mp4"
                data_name = f"data_{timestamp}.parquet"

            video_path = os.path.join(self.video_path, video_name)
            data_path = os.path.join(self.video_path, data_name)
            
            # Start recording
            self.camera_manager.start_recording(video_path)
            self.record_start_ms = perf_counter_ns() * 1e-6
            self.data_handler = DataHandler(self.data_queue, 
                                            batch_size=1000, 
                                            output_dir=self.video_path, 
                                            start_time = self.record_start_ms)
            
            # Check for old value stored in queue and clear it
            if self.data_queue.full():
                _ = self.data_queue.get() # Clear the queue

            self.data_handler.start(data_path)

            # Update the record button to show that recording is in progress
            self.record_button.configure(text="Stop", image=self.stop_icon)
            
            # Set the callback function to be executed when the writing thread finishes
            self.camera_manager.set_on_write_finished(self.on_write_finished)

            self.pause_button.configure(state="normal")
        else:
            # Stop recording
            self.camera_manager.stop_recording()
            self.data_handler.stop()  # Stop the DataHandler

            if self.camera_manager.is_paused:
                self.pause_button.configure(text="Pause", state="disabled", image=self.pause_icon)
                self.camera_manager.is_paused = False
                self.record_button.configure(text="Record", state="enabled", image=self.record_icon)
            else:
                self.record_button.configure(text="Saving", state="disabled")

    def toggle_pause(self):
        if self.camera_manager.is_paused:
            # Stop the stream frame thread if it's running
            if self.camera_manager.is_reading:
                self.camera_manager.stop_frame_thread()

            # Resume recording with a new video file
            self.camera_manager.is_paused = False
            timestamp = time.strftime("%d%mT%H%M%S")
            file_name = f"video_{timestamp}.mp4"
            filename = os.path.join(self.video_path, file_name)
            self.camera_manager.start_recording(filename)

            # Set the callback function to be executed when the writing thread finishes
            self.camera_manager.set_on_write_finished(self.on_write_finished)
            self.pause_button.configure(text="Pause", image=self.pause_icon)
        else:
            # Pause recording and stop the current video file
            self.camera_manager.is_paused = True
            self.camera_manager.stop_recording()
            
            self.pause_button.configure(text="Saving", state="disabled")

    def on_write_finished(self):
        if not self.camera_manager.is_paused:
            # Update the record button to allow recording again
            self.record_button.configure(text="Record", image=self.record_icon, state="normal")
        else:
            self.pause_button.configure(text="Resume", image=self.play_icon, state="normal")
            
        # Restart the frame thread if video feed is live
        if self.is_live:
            self.camera_manager.start_frame_thread()

    def adjust_gain(self, gain_value: float):
        if self.camera_manager.cap:
            try:
                self.camera_manager.cap.set(cv2.CAP_PROP_GAIN, float(gain_value)) # dB
                self.gain_label.configure(text=f"Gain (dB): {round(gain_value, 2)}")
            except AttributeError:
                logging.error("Gain not set.")

    def update_fps_label(self):
        if self.camera_manager.cap:
            try:
                fps = self.camera_manager.cap.get(cv2.CAP_PROP_FPS)
                self.fps_label.configure(text=f"FPS: {round(float(fps),2)}")
            except AttributeError:
                logging.error("FPS not set.")

    def adjust_exposure(self, exposure_value: float):
        if self.camera_manager.cap:
            try:
                self.camera_manager.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
                self.exposure_label.configure(text=f"Exposure (us): {round(exposure_value, 2)}")
                self.update_fps_label()
            except AttributeError:
                logging.error("Exposure not set.")

    def update_video_label(self):
        if self.is_live:
            frame = self.camera_manager.latest_frame

            if frame is not None:
                processed_frame = self.image_pro.process_frame(frame)
                self.display_frame(processed_frame)

            self.window.after(30, self.update_video_label)

    def update_num_marker_label(self):
        if self.qtm_stream is not None:
            self.num_marker_label.configure(text=f"No. Markers: {self.qtm_stream.num_markers}")
            # Update number of markers at 5Hz -> this is a good proof of concept for marker averaging
            self.window.after(200, self.update_num_marker_label)

    def display_frame(self, frame):
        # Convert to cv2 img
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to pil img
        img = Image.fromarray(img)

        # Convert to tk img
        img = ctk.CTkImage(img, size = (self.camera_manager.frame_width*(2/3), self.camera_manager.frame_height*(2/3)))

        # Update label with new image
        self.gui.video_label.configure(image=img)

    def set_threshold(self, value: float):
        self.image_pro.threshold_value = int(value)
        self.threshold_label.configure(text=f"Threshold: {int(value)}")

    def set_strength(self, value: float):
        self.image_pro.strength_value = int(value)
        self.strength_label.configure(text=f"Strength: {int(value)}")

    def update_serial_ports_dropdown(self):
        """Updates the list of serial ports in the dropdown."""
        serial_ports = get_serial_ports()
        self.com_port_combobox.configure(values=serial_ports)

    def connect_dyna_controller(self):
        """Initializes or reconnects the DynaController with the selected COM port."""
        try:
            selected_port = self.selected_com_port.get()  # Ensure this matches how you obtain the selected COM port value
            if selected_port:
                self.dyna = DynaController(com_port=selected_port)
                self.dyna.open_port()

                self.dyna.set_gains(self.dyna.pan_id, 2432, 720, 3200, 0)
                self.dyna.set_gains(self.dyna.tilt_id, 2432, 720, 3200, 0)

                self.dyna.set_op_mode(1, 3)  # Pan to position control
                self.dyna.set_op_mode(2, 3)  # Tilt to position control

                self.dyna.set_sync_pos(45, 45)

                self.dyna.set_torque(self.dyna.pan_id, self.torque_flag.get())
                self.dyna.set_torque(self.dyna.tilt_id, self.torque_flag.get())
                
                logging.info(f"Connected to Dynamixel controller on {selected_port}.")
            else:
                logging.error("No COM port selected.")
        except Exception as e:
            logging.error(f"Error connecting to Dynamixel controller: {e}")
            self.dyna = None

    def update_camera_dropdown(self):
        cameras = self.camera_manager.get_available_cameras()
        self.cam_combobox.configure(values=cameras)
        if cameras:
            self.cam_combobox.set(cameras[0])
        else:
            self.cam_combobox.set("")

    def connect_camera(self, camera_index: int):
        selected_camera = self.selected_camera.get()
        if selected_camera:
            camera_index = int(selected_camera.split(" ")[1])
            self.camera_manager.connect_camera(camera_index)
        else:
            logging.error("No camera selected.")

    def mocap_button_press(self):
        self.connect_mocap()
        self.update_num_marker_label()

    def connect_mocap(self):
        try:
            self.qtm_stream = QTMStream()
            self.qtm_stream.calibration_target = True

            logging.info("Connected to QTM.")
        except Exception as e:
            logging.error(f"Error connecting to QTM: {e}")
            self.qtm_stream = None

    def set_torque(self):
        if self.dyna is not None:
            self.dyna.set_torque(self.dyna.pan_id, self.torque_flag.get())
            self.dyna.set_torque(self.dyna.tilt_id, self.torque_flag.get())
        else:
            logging.error("Dynamixel controller not connected.")

    def set_pan(self, value: float):
        if self.dyna is not None:
            value = round(value, 3)
            self.pan_value = value
            self.pan_label.configure(text=f"Pan: {round(value,1)}°")
            angle = num_to_range(self.pan_value, -45, 45, 22.5, 67.5)
            self.dyna.set_pos(1, angle)
        else:
            logging.error("Dynamixel controller not connected.")

    def set_tilt(self, value: float):
        if self.dyna is not None:
            value = round(value, 3)
            self.tilt_value = value
            self.tilt_label.configure(text=f"Tilt: {round(value,1)}°")

            # angle = num_to_range(self.tilt_value, -45, 45, 292.5, 337.5)

            # Reverse tilt mapping direction
            angle = num_to_range(self.tilt_value, -45, 45, 22.5, 67.5)
            self.dyna.set_pos(2, angle)
        else:
            logging.error("Dynamixel controller not connected.")

    def centre(self):
        self.set_pan(0)
        self.set_tilt(0)
        self.pan_slider.set(0)
        self.tilt_slider.set(0)

    def on_closing(self):
        # Cleanup GUI resources
        self.gui.cleanup_resources()
        
        try:
            # Close the camera
            self.is_live = False
            self.camera_manager.stop_frame_thread()
            self.camera_manager.release()
        except Exception as e:
            logging.info(f"Error closing camera or serial port: {e}")
    
        try:
            self.window.destroy()
        except Exception as e:
            logging.error(f"Error closing window: {e}")

        try:
            if self.qtm_stream is not None:
                asyncio.run_coroutine_threadsafe(self.qtm_stream._close(), asyncio.get_event_loop())
                self.qtm_stream.close()

        except Exception as e:
            logging.info(f"Error closing QTM connection: {e}")

        try:
            # Close the serial port
            if self.dyna is not None:
                self.dyna.close_port()
        except Exception as e:
            logging.info(f"Error closing serial port: {e}")

        # Terminate subprocess
        if self.track_process is not None and hasattr(self, 'track_process') and self.track_process.is_alive():
            try:
                self.terminate_event.set()
                self.track_process.join()
            except Exception as e:
                logging.error(f"Error terminating track process: {e}")

        try:
            quit()
        except Exception as e:
            logging.error(f"Error quitting: {e}")

    def select_folder(self):
            path = ctk.filedialog.askdirectory()
            
            self.video_path = path

    def on_configure(self, e):
        if e.widget == self.window:
            time.sleep(0.01)

def get_serial_ports() -> list:
    """Lists available serial ports.

    :return: A list of serial port names available on the system.
    """
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

if __name__ == "__main__":
    ctk.set_default_color_theme("src/style.json")
    root = ctk.CTk()
    app = DART(root)
    # cProfile.run('app = DART(root)')
