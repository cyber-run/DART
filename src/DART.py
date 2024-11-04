import logging
logging.basicConfig(level=logging.ERROR)

from utils.misc_funcs import num_to_range
from utils.perf_timings import perf_counter_ns
import cProfile, time, cv2, os, asyncio, psutil, signal
from hardware.motion.dyna_controller import DynaController
from hardware.camera.camera_manager import CameraManager
from core.image_processor import ImageProcessor
from CTkMessagebox import CTkMessagebox
from multiprocessing import Process, Queue, Event
from data.data_handler import DataHandler
from tracking.dart_track_akf import dart_track
from tracking.calibrate import Calibrator
import serial.tools.list_ports
import customtkinter as ctk
from ui.dart_gui import DARTGUI
from hardware.mocap.qtm_mocap import *
from PIL import Image
import tkinter as tk
import numpy as np
from core.state_manager import DARTState
from ui.ui_controller import UIController



class DART:
    def __init__(self, window: ctk.CTk):
        # Initialize state manager
        self.state = DARTState()
        self.ui_controller = UIController(self)
        
        self.init_window(window)
        self.window.bind("<Configure>", self.on_configure)

        self.init_hardware()
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

    def toggle_video_feed(self):
        """Toggle video feed on/off"""
        self.state.recording.is_live = not self.state.recording.is_live
        
        # Use UI controller to update button
        self.ui_controller.update_video_button(
            text="Stop" if self.state.recording.is_live else "Start",
            icon=self.state.get_icon('stop' if self.state.recording.is_live else 'play')
        )
        
        if self.state.recording.is_live:
            self.camera_manager.start_frame_thread()
            if self.state.get_current_view() == "track":
                self.update_video_label()
        else:
            self.camera_manager.stop_frame_thread()

    def toggle_record(self):
        # If camera manager is not recording, start recording
        if self.state.ui.record_button.cget("text") == "Record":
            # Stop the stream frame thread if it's running
            if self.camera_manager.is_reading:
                self.camera_manager.stop_frame_thread()

            # Get current timestamp and entry field for recording filename
            timestamp = time.strftime("%d%mT%H%M%S")
            file_name = self.state.ui.file_name_entry.get().strip()

            # Set the file name to a default value if it's empty
            if file_name:
                video_name = f"{file_name}_{timestamp}.mp4"
                data_name = f"{file_name}_{timestamp}.parquet"
            else:
                video_name = f"video_{timestamp}.mp4"
                data_name = f"data_{timestamp}.parquet"

            # Ensure the recordings directory exists
            os.makedirs(self.state.recording.video_path, exist_ok=True)

            video_path = os.path.join(self.state.recording.video_path, video_name)
            data_path = os.path.join(self.state.recording.video_path, data_name)
            
            # Start recording
            self.camera_manager.start_recording(video_path)
            self.state.recording.record_start_ms = perf_counter_ns() * 1e-6

            # Start the DataHandler if tracking is enabled
            if self.state.tracking['process'] is not None:
                self.data_handler = DataHandler(
                    self.state.tracking['data_queue'], 
                    batch_size=1000, 
                    output_dir=self.state.recording.video_path, 
                    start_time=self.state.recording.record_start_ms
                )
                
                # Check for old value stored in queue and clear it
                if self.state.tracking['data_queue'].full():
                    _ = self.state.tracking['data_queue'].get() # Clear the queue

                self.data_handler.start(data_path)

            # Update the record button to show that recording is in progress
            self.state.ui.record_button.configure(text="Stop", image=self.state.get_icon('stop'))
            
            # Set the callback function to be executed when the writing thread finishes
            self.camera_manager.set_on_write_finished(self.on_write_finished)

            self.state.ui.pause_button.configure(state="normal")
        else:
            # Stop recording
            self.camera_manager.stop_recording()

            # Stop the DataHandler if tracking is enabled
            if self.state.tracking['process'] is not None:
                self.data_handler.stop()  # Stop the DataHandler

            if self.camera_manager.is_paused:
                self.state.ui.pause_button.configure(
                    text="Pause", 
                    state="disabled", 
                    image=self.state.get_icon('pause')
                )
                self.camera_manager.is_paused = False
                self.state.ui.record_button.configure(
                    text="Record", 
                    state="enabled", 
                    image=self.state.get_icon('record')
                )
            else:
                self.state.ui.record_button.configure(text="Saving", state="disabled")

    def toggle_pause(self):
        if self.camera_manager.is_paused:
            # Stop the stream frame thread if it's running
            if self.camera_manager.is_reading:
                self.camera_manager.stop_frame_thread()

            # Resume recording with a new video file
            self.camera_manager.is_paused = False
            timestamp = time.strftime("%d%mT%H%M%S")
            file_name = f"video_{timestamp}.mp4"
            filename = os.path.join(self.state.recording.video_path, file_name)
            self.camera_manager.start_recording(filename)

            # Set the callback function to be executed when the writing thread finishes
            self.camera_manager.set_on_write_finished(self.on_write_finished)
            self.state.ui.pause_button.configure(text="Pause", image=self.state.get_icon('pause'))
        else:
            # Pause recording and stop the current video file
            self.camera_manager.is_paused = True
            self.camera_manager.stop_recording()
            
            self.state.ui.pause_button.configure(text="Saving", state="disabled")

    def on_write_finished(self):
        if not self.camera_manager.is_paused:
            # Update the record button to allow recording again
            self.state.ui.record_button.configure(text="Record", image=self.state.get_icon('record'), state="normal")
        else:
            self.state.ui.pause_button.configure(text="Resume", image=self.state.get_icon('play'), state="normal")
            
        # Restart the frame thread if video feed is live
        if self.state.recording.is_live:
            self.camera_manager.start_frame_thread()

    def adjust_gain(self, gain_value: float):
        if self.camera_manager.cap:
            try:
                self.camera_manager.cap.set(cv2.CAP_PROP_GAIN, float(gain_value))
                self.state.ui.gain_label.configure(text=f"Gain (dB): {round(gain_value, 2)}")
            except AttributeError:
                logging.error("Gain not set.")

    def update_fps_label(self):
        if self.camera_manager.cap:
            try:
                fps = self.camera_manager.cap.get(cv2.CAP_PROP_FPS)
                self.state.ui.fps_label.configure(text=f"FPS: {round(float(fps),2)}")
            except AttributeError:
                logging.error("FPS not set.")

    def adjust_exposure(self, exposure_value: float):
        if self.camera_manager.cap:
            try:
                self.camera_manager.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
                self.state.ui.exposure_label.configure(text=f"Exposure (us): {round(exposure_value, 2)}")
                self.update_fps_label()
            except AttributeError:
                logging.error("Exposure not set.")

    def update_video_label(self):
        if self.state.recording.is_live:
            frame = self.camera_manager.latest_frame

            if frame is not None:
                processed_frame = self.image_pro.process_frame(frame)
                self.display_frame(processed_frame)

            self.window.after(30, self.update_video_label)

    def update_num_marker_label(self):
        """Update the marker count display"""
        if self.state.hardware.qtm_stream is not None:
            try:
                num_markers = self.state.hardware.qtm_stream.num_markers
                self.ui_controller.update_marker_count(num_markers)
                # Schedule next update only if QTM stream exists
                if self.state.hardware.qtm_stream:
                    self.window.after(200, self.update_num_marker_label)
            except Exception as e:
                logging.error(f"Error updating marker count: {e}")
                self.ui_controller.update_mocap_status("Error")

    def display_frame(self, frame):
        # Convert to cv2 img
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to pil img
        img = Image.fromarray(img)

        # Convert to tk img
        img = ctk.CTkImage(img, size=(self.camera_manager.frame_width, self.camera_manager.frame_height))

        # Update label with new image through state manager
        if self.state.ui.video_label:
            self.state.ui.video_label.configure(image=img)

    def set_threshold(self, value: float):
        self.image_pro.threshold_value = int(value)
        self.state.ui.threshold_label.configure(text=f"Threshold: {int(value)}")

    def set_strength(self, value: float):
        self.image_pro.strength_value = int(value)
        self.state.ui.strength_label.configure(text=f"Strength: {int(value)}")

    def update_serial_ports_dropdown(self):
        """Updates the list of serial ports in the dropdown."""
        serial_ports = get_serial_ports()
        self.state.ui.com_port_combobox.configure(values=serial_ports)

    def connect_dyna_controller(self):
        """Initializes or reconnects the DynaController with the selected COM port."""
        try:
            selected_port = self.state.hardware.selected_com_port.get()  # Ensure this matches how you obtain the selected COM port value
            if selected_port:
                self.dyna = DynaController(com_port=selected_port)
                self.dyna.open_port()

                self.dyna.set_gains(self.dyna.pan_id, 2432, 720, 3200, 0)
                self.dyna.set_gains(self.dyna.tilt_id, 2432, 720, 3200, 0)

                self.dyna.set_op_mode(1, 3)  # Pan to position control
                self.dyna.set_op_mode(2, 3)  # Tilt to position control

                self.dyna.set_sync_pos(45, 45)

                self.dyna.set_torque(self.dyna.pan_id, self.state.flags['torque'].get())
                self.dyna.set_torque(self.dyna.tilt_id, self.state.flags['torque'].get())
                
                logging.info(f"Connected to Dynamixel controller on {selected_port}.")
            else:
                logging.error("No COM port selected.")
        except Exception as e:
            logging.error(f"Error connecting to Dynamixel controller: {e}")
            self.dyna = None

    def update_camera_dropdown(self):
        cameras = self.camera_manager.get_available_cameras()
        self.state.ui.cam_combobox.configure(values=cameras)
        if cameras:
            self.state.ui.cam_combobox.set(cameras[0])
        else:
            self.state.ui.cam_combobox.set("")

    def connect_camera(self, camera_index: int):
        selected_camera = self.state.hardware.selected_camera.get()
        if selected_camera:
            camera_index = int(selected_camera.split(" ")[1])
            self.camera_manager.connect_camera(camera_index)
        else:
            logging.error("No camera selected.")

    def mocap_button_press(self):
        """Handle mocap connection button press"""
        if self.state.hardware.qtm_stream is None:
            self.connect_mocap()
            if self.state.hardware.qtm_stream is not None:
                self.update_num_marker_label()
                self.ui_controller.update_mocap_button("Disconnect", self.state.get_icon('stop'))
        else:
            try:
                self.state.hardware.qtm_stream._close()
                self.state.hardware.qtm_stream.close()
                self.state.hardware.qtm_stream = None
                self.ui_controller.update_mocap_status("Disconnected")
                self.ui_controller.update_mocap_button("Connect", self.state.get_icon('sync'))
            except Exception as e:
                logging.error(f"Error disconnecting from QTM: {e}")

    def connect_mocap(self):
        try:
            self.state.hardware.qtm_stream = QTMStream()
            self.state.hardware.qtm_stream.calibration_target = True
            self.ui_controller.update_mocap_status("Connected")
            logging.info("Connected to QTM.")
        except Exception as e:
            self.ui_controller.update_mocap_status("Failed")
            logging.error(f"Error connecting to QTM: {e}")
            self.state.hardware.qtm_stream = None

    def set_torque(self):
        if self.dyna is not None:
            self.dyna.set_torque(self.dyna.pan_id, self.state.flags['torque'].get())
            self.dyna.set_torque(self.dyna.tilt_id, self.state.flags['torque'].get())
        else:
            logging.error("Dynamixel controller not connected.")

    def set_pan(self, value: float):
        if self.dyna is not None:
            value = round(value, 3)
            self.state.motor['pan_value'] = value
            self.state.ui.pan_label.configure(text=f"Pan: {round(value,1)}°")
            angle = num_to_range(self.state.motor['pan_value'], -45, 45, 22.5, 67.5)
            self.dyna.set_pos(1, angle)
        else:
            logging.error("Dynamixel controller not connected.")

    def set_tilt(self, value: float):
        if self.dyna is not None:
            value = round(value, 3)
            self.state.motor['tilt_value'] = value
            self.state.ui.tilt_label.configure(text=f"Tilt: {round(value,1)}°")

            # angle = num_to_range(self.state.motor['tilt_value'], -45, 45, 292.5, 337.5)

            # Reverse tilt mapping direction
            angle = num_to_range(self.state.motor['tilt_value'], -45, 45, 22.5, 67.5)
            self.dyna.set_pos(2, angle)
        else:
            logging.error("Dynamixel controller not connected.")

    def centre(self):
        """Center both pan and tilt motors"""
        self.set_pan(0)
        self.set_tilt(0)
        self.ui_controller.update_slider_values(pan=0, tilt=0)

    def on_closing(self):
        """Clean up resources and close the application"""
        # Stop any ongoing tracking
        if self.state.tracking['process'] is not None:
            self.state.stop_tracking()

        # Stop video feed
        if self.state.recording.is_live:
            self.toggle_video_feed()
        
        # Cleanup GUI resources
        self.gui.cleanup_resources()
        
        try:
            # Close the camera
            self.camera_manager.stop_frame_thread()
            self.camera_manager.release()
        except Exception as e:
            logging.info(f"Error closing camera: {e}")
    
        try:
            # Close QTM connection
            if self.state.hardware.qtm_stream is not None:
                self.state.hardware.qtm_stream._close()
                self.state.hardware.qtm_stream.close()
                self.state.hardware.qtm_stream = None
        except Exception as e:
            logging.info(f"Error closing QTM connection: {e}")

        try:
            # Close the serial port
            if self.dyna is not None:
                self.dyna.close_port()
                self.dyna = None
        except Exception as e:
            logging.info(f"Error closing serial port: {e}")

        try:
            # Destroy the window and quit
            self.window.quit()
            self.window.destroy()
        except Exception as e:
            logging.error(f"Error closing window: {e}")

        # Force exit if needed
        try:
            import sys
            sys.exit(0)
        except Exception as e:
            logging.error(f"Error during system exit: {e}")

    def select_folder(self):
        path = ctk.filedialog.askdirectory()
        if path:  # Only update if a path was selected
            self.state.recording.video_path = path

    def on_configure(self, e):
        if e.widget == self.window:
            time.sleep(0.01)

    def get_mem(self):
        """Get system memory usage and update display"""
        self.state.status['memory_usage'] = psutil.virtual_memory()[2]
        self.ui_controller.update_memory_usage(self.state.status['memory_usage'])
        self.window.after(5000, self.get_mem)

    def track(self):
        """Handle tracking start/stop"""
        if self.state.tracking['process'] is not None:
            self.state.stop_tracking()
            self.connect_dyna_controller()
            self.ui_controller.update_track_button("Track", self.state.get_icon('play'))
            return
        
        if self.calibrator.calibrated and self.state.tracking['process'] is None:
            # Close QTM connections
            if self.state.hardware.qtm_stream:
                self.state.hardware.qtm_stream._close()
                self.state.hardware.qtm_stream.close()

            # Close serial port
            if self.dyna:
                self.dyna.close_port()

            # Create instance of queue for retrieving data
            self.state.tracking['data_queue'] = Queue(maxsize=1)

            # Create and start the tracking process
            self.state.tracking['terminate_event'] = Event()
            self.state.tracking['process'] = Process(
                target=dart_track, 
                args=(self.state.tracking['data_queue'], 
                      self.state.tracking['terminate_event'])
            )
            self.state.tracking['process'].start()

            # Update the track button to show "Stop"
            self.ui_controller.update_track_button("Stop", self.state.get_icon('stop'))
        else:
            # Add popup window to notify user that DART is not calibrated
            CTkMessagebox(title="Error", message="DART Not Calibrated", icon="cancel")
            logging.error("DART is not calibrated.")

    def calibrate(self):
        """Calibrate the system using current positions"""
        if self.state.hardware.qtm_stream:
            p1 = np.array(self.state.hardware.qtm_stream.position)
            p2 = np.array(self.state.hardware.qtm_stream.position2)
            self.calibrator.run(p1, p2)
            self.ui_controller.update_calibration_age(int(self.calibrator.calibration_age))
        else:
            logging.error("QTM stream not available for calibration")

def get_serial_ports() -> list:
    """Lists available serial ports.

    :return: A list of serial port names available on the system.
    """
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

if __name__ == "__main__":
    ctk.set_default_color_theme("config/style.json")
    root = ctk.CTk()
    app = DART(root)
    # cProfile.run('app = DART(root)')
