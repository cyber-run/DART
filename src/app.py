import logging
from utils.misc_funcs import num_to_range
from utils.perf_timings import perf_counter_ns
import time, cv2, os, psutil
from hardware.motion.dyna_controller import DynaController
from hardware.motion.theia_controller import TheiaController
from hardware.camera.camera_manager import CameraManager
from core.image_processor import ImageProcessor
from CTkMessagebox import CTkMessagebox
from multiprocessing import Process, Queue, Event
from data.data_handler import DataHandler
from tracking.dart_track import dart_track
from tracking.calibrate import Calibrator
import serial.tools.list_ports
import customtkinter as ctk
from ui.main_window import MainWindow
from hardware.mocap.qtm_mocap import *
from PIL import Image
import numpy as np
from core.state_manager import DARTState
from ui.ui_controller import UIController
from core.device_manager import DeviceManager
from core.config_manager import ConfigManager
from ui.views.theia_control_window import TheiaLensControlWindow


class DART:
    def __init__(self, window: ctk.CTk):
        self.logger = logging.getLogger("DART")
        
        # Initialize configuration first
        self.config = ConfigManager()
        
        # Initialize state and controllers
        self.state = DARTState()
        self.ui_controller = UIController(self)
        
        # Initialize device manager with config
        self.device_manager = DeviceManager(self.config)
        
        # Initialize core components
        self.image_pro = ImageProcessor()
        self.calibrator = Calibrator(self.config)
        
        # Initialize hardware components with defaults
        self.camera_manager = CameraManager()
        self.dyna = None
        self.theia = None
        
        self.init_window(window)
        self.window.bind("<Configure>", self.on_configure)

        # Initialize hardware with config
        self.init_hardware()
        
        # Create main window after hardware is initialized
        self.main_window = MainWindow(window, self)
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def init_window(self, window):
        self.window = window
        self.window.title("DART")

        # Set the minimum window size to the initial size
        self.window.geometry("1200x820")
        self.window.minsize(1200, 820)

    def init_hardware(self):
        """Initialize and connect hardware from saved configuration"""
        try:
            device_config = self.config.config["devices"]
            
            # Auto-connect cameras if configured
            if device_config["cameras"]:
                self.camera_manager = CameraManager()
                for serial in device_config["cameras"]:
                    if self.camera_manager.connect_camera(serial):
                        self.ui_controller.update_camera_status("Connected")
                    else:
                        self.ui_controller.update_camera_status("Failed")
                        self.logger.error(f"Failed to connect camera: {serial}")
            
            # Auto-connect Dynamixel if configured
            if device_config["dynamixel_port"]:
                self.dyna = DynaController(device_config["dynamixel_port"])
                if self.dyna.open_port():
                    self.dyna.set_gains(self.dyna.pan_id, 2432, 720, 3200, 0)
                    self.dyna.set_gains(self.dyna.tilt_id, 2432, 720, 3200, 0)
                    self.dyna.set_op_mode(1, 3)  # Pan to position control
                    self.dyna.set_op_mode(2, 3)  # Tilt to position control
                    self.ui_controller.update_motors_status("Connected")
                else:
                    self.ui_controller.update_motors_status("Failed")
                    self.logger.error("Failed to connect to motors")
            
            # Auto-connect Theia if configured
            if device_config["theia_port"]:
                try:
                    self.theia = TheiaController(device_config["theia_port"])
                    self.theia.connect()
                    self.theia.initialise()
                    self.logger.info(f"Connected to Theia controller on {device_config['theia_port']}")
                except Exception as e:
                    self.logger.error(f"Failed to connect to Theia controller: {e}")
                    self.theia = None
                
        except Exception as e:
            self.logger.error(f"Error initializing hardware: {e}")
            self.ui_controller.update_status_text("Hardware initialization failed")

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
                
                # Wait briefly for frame timestamps to be available
                time.sleep(0.1)  # Wait 100ms for frames to accumulate
                
                if self.camera_manager.frame_timestamps:
                    self.data_handler.set_frame_timestamps(self.camera_manager.frame_timestamps)
                else:
                    self.logger.warning("No frame timestamps available yet")
                
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
            self.logger.info("Stopping recording sequence...")
            
            # 1. Stop collecting new data
            if self.state.tracking['process'] is not None:
                self.data_handler.stop_collecting()
            
            # 2. Stop camera recording
            self.camera_manager.stop_recording()
            
            # 3. Wait for all frames to be written
            self.logger.info("Waiting for frame writing to complete...")
            while self.camera_manager.writing:
                time.sleep(0.1)
            
            # 4. Now that frames are written, handle data
            if self.state.tracking['process'] is not None:
                # Get complete frame timestamps
                frame_timestamps = self.camera_manager.get_frame_timestamps()
                self.data_handler.set_frame_timestamps(frame_timestamps)
                
                # 5. Stop the DataHandler and process data
                self.data_handler.stop()

            # Update UI
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
                self.logger.error("Gain not set.")

    def update_fps_label(self):
        if self.camera_manager.cap:
            try:
                fps = self.camera_manager.cap.get(cv2.CAP_PROP_FPS)
                self.state.ui.fps_label.configure(text=f"FPS: {round(float(fps),2)}")
            except AttributeError:
                self.logger.error("FPS not set.")

    def adjust_exposure(self, exposure_value: float):
        if self.camera_manager.cap:
            try:
                self.camera_manager.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
                self.state.ui.exposure_label.configure(text=f"Exposure (us): {round(exposure_value, 2)}")
                self.update_fps_label()
            except AttributeError:
                self.logger.error("Exposure not set.")

    def update_video_label(self):
        if self.camera_manager.latest_frame is not None:
            frame = self.camera_manager.latest_frame
            
            # Process frame if image processor exists
            if hasattr(self, 'image_pro'):
                processed_frame = self.image_pro.process_frame(frame)
            else:
                processed_frame = frame
                
            self.display_frame(processed_frame)
            
        if self.state.recording.is_live:
            self.window.after(10, self.update_video_label)

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
                self.logger.error(f"Error updating marker count: {e}")
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
        """Initializes or reconnects the DynaController with the configured port"""
        try:
            # Get port from config instead of UI
            dyna_port = self.config.config["devices"]["dynamixel_port"]
            if dyna_port:
                self.dyna = DynaController(com_port=dyna_port)
                if self.dyna.open_port():
                    self.dyna.set_gains(self.dyna.pan_id, 2432, 720, 3200, 0)
                    self.dyna.set_gains(self.dyna.tilt_id, 2432, 720, 3200, 0)
                    self.dyna.set_op_mode(1, 3)  # Pan to position control
                    self.dyna.set_op_mode(2, 3)  # Tilt to position control
                    self.dyna.set_sync_pos(45, 45)
                    self.dyna.set_torque(self.dyna.pan_id, self.state.flags['torque'].get())
                    self.dyna.set_torque(self.dyna.tilt_id, self.state.flags['torque'].get())
                    self.ui_controller.update_motors_status("Connected")
                    self.logger.info(f"Connected to Dynamixel controller on {dyna_port}")
                else:
                    self.ui_controller.update_motors_status("Failed")
                    self.logger.error(f"Failed to open port {dyna_port}")
            else:
                self.ui_controller.update_motors_status("Not Configured")
                self.logger.error("Dynamixel port not configured")
        except Exception as e:
            self.ui_controller.update_motors_status("Error")
            self.logger.error(f"Error connecting to Dynamixel controller: {e}")
            self.dyna = None

    def update_camera_dropdown(self):
        cameras = self.camera_manager.get_available_cameras()
        self.state.ui.cam_combobox.configure(values=cameras)
        if cameras:
            self.state.ui.cam_combobox.set(cameras[0])
        else:
            self.state.ui.cam_combobox.set("")

    def connect_camera(self, serial: str):
        """Connect to camera by serial number"""
        if self.camera_manager.connect_camera(serial):
            self.ui_controller.update_camera_status("Connected")
        else:
            self.ui_controller.update_camera_status("Failed")
            self.logger.error(f"Failed to connect to camera: {serial}")

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
                self.logger.error(f"Error disconnecting from QTM: {e}")

    def connect_mocap(self):
        try:
            self.state.hardware.qtm_stream = QTMStream()
            self.state.hardware.qtm_stream.calibration_target = True
            self.ui_controller.update_mocap_status("Connected")
            self.logger.info("Connected to QTM.")
        except Exception as e:
            self.ui_controller.update_mocap_status("Failed")
            self.logger.error(f"Error connecting to QTM: {e}")
            self.state.hardware.qtm_stream = None

    def set_torque(self):
        if self.dyna is not None:
            self.dyna.set_torque(self.dyna.pan_id, self.state.flags['torque'].get())
            self.dyna.set_torque(self.dyna.tilt_id, self.state.flags['torque'].get())
        else:
            self.logger.error("Dynamixel controller not connected.")

    def set_pan(self, value: float):
        if self.dyna is not None:
            value = round(value, 3)
            self.state.motor['pan_value'] = value
            self.state.ui.pan_label.configure(text=f"Pan: {round(value,1)}°")
            angle = num_to_range(self.state.motor['pan_value'], -45, 45, 22.5, 67.5)
            self.dyna.set_pos(1, angle)
        else:
            self.logger.error("Dynamixel controller not connected.")

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
            self.logger.error("Dynamixel controller not connected.")

    def centre(self):
        """Center both pan and tilt motors"""
        self.set_pan(0)
        self.set_tilt(0)
        self.ui_controller.update_slider_values(pan=0, tilt=0)

    def on_closing(self):
        """Clean up resources and close the application"""
        try:
            # Stop any ongoing tracking
            if self.state.tracking['process'] is not None:
                self.state.stop_tracking()

            # Stop video feed
            if self.state.recording.is_live:
                self.toggle_video_feed()
            
            # Release camera resources
            if hasattr(self, 'camera_manager'):
                self.camera_manager.release()
                
            # Close QTM connection
            if self.state.hardware.qtm_stream:
                self.state.hardware.qtm_stream._close()
                self.state.hardware.qtm_stream.close()
                
            # Close motor controllers
            if self.dyna:
                self.dyna.close_port()
                
            # Cleanup GUI resources
            self.main_window.cleanup_resources()
            
            # Destroy window
            self.window.quit()
            self.window.destroy()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            
        finally:
            # Force exit
            import sys
            sys.exit(0)

    def select_folder(self):
        path = ctk.filedialog.askdirectory()
        if path:  # Only update if a path was selected
            self.state.recording.video_path = path

    def on_configure(self, e):
        if e.widget == self.window:
            time.sleep(0.01)

    def get_mem(self):
        """Get system memory usage and update display"""
        try:
            self.state.status['memory_usage'] = psutil.virtual_memory()[2]
            self.ui_controller.update_memory_usage(self.state.status['memory_usage'])
            # Schedule next update
            self.window.after(5000, self.get_mem)
        except Exception as e:
            self.logger.error(f"Error updating memory usage: {e}")

    def track(self):
        """Handle tracking start/stop"""
        if self.state.tracking['process'] is not None:
            # Stop tracking process
            self.state.stop_tracking()

            # Reload config manager to update theia state
            self.config.reload_config()
            
            # Only reconnect motor controllers
            try:
                # Get ports from config
                dyna_port = self.config.config["devices"]["dynamixel_port"]
                theia_port = self.config.config["devices"]["theia_port"]
                
                # Reconnect Dynamixel
                if dyna_port:
                    self.dyna = DynaController(dyna_port)
                    if self.dyna.open_port():
                        self.dyna.set_gains(self.dyna.pan_id, 2432, 720, 3200, 0)
                        self.dyna.set_gains(self.dyna.tilt_id, 2432, 720, 3200, 0)
                        self.dyna.set_op_mode(1, 3)  # Pan to position control
                        self.dyna.set_op_mode(2, 3)  # Tilt to position control
                        self.ui_controller.update_motors_status("Connected")
                
                # Reconnect Theia if needed
                if theia_port:
                    self.theia = TheiaController(theia_port)
                    self.theia.connect()
                    self.theia.initialise()
                    
            except Exception as e:
                self.logger.error(f"Error reconnecting motors: {e}")
            
            self.ui_controller.update_track_button("Track", self.state.get_icon('play'))
            return
        
        if self.calibrator.calibrated and self.state.tracking['process'] is None:
            # Only close motor connections
            if self.dyna:
                self.dyna.close_port()
                self.dyna = None
            
            if hasattr(self, 'theia') and self.theia:
                try:
                    if self.theia.ser.is_open:
                        self.theia.disconnect()
                except Exception as e:
                    self.logger.error(f"Error disconnecting Theia: {e}")
                self.theia = None

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
            self.logger.error("DART is not calibrated.")

    def calibrate(self):
        """Calibrate the system using current positions"""
        if self.state.hardware.qtm_stream:
            p1 = np.array(self.state.hardware.qtm_stream.position)
            p2 = np.array(self.state.hardware.qtm_stream.position2)
            self.calibrator.run(p1, p2)
            self.ui_controller.update_calibration_age(int(self.calibrator.calibration_age))
        else:
            self.logger.error("QTM stream not available for calibration")

    def open_theia_control_window(self):
        """Open the Theia lens control window"""
        # Check if Theia is properly connected
        if not self.theia or not hasattr(self.theia, 'ser') or not self.theia.ser.is_open:
            try:
                # Try to reconnect
                device_config = self.config.config["devices"]
                if device_config["theia_port"]:
                    self.theia = TheiaController(device_config["theia_port"])
                    self.theia.connect()
                    self.theia.initialise()
                    self.logger.info(f"Reconnected to Theia controller")
            except Exception as e:
                self.logger.error(f"Failed to connect to Theia controller: {e}")
                CTkMessagebox(
                    title="Error",
                    message="Could not connect to Theia controller. Please check hardware connection.",
                    icon="cancel"
                )
                return

        # Open window if Theia is connected
        try:
            # Check if window exists and is valid
            if hasattr(self, 'theia_window') and self.theia_window.winfo_exists():
                self.theia_window.lift()  # Bring window to front
                self.theia_window.focus_force()  # Force focus
            else:
                # Create new window
                self.theia_window = TheiaLensControlWindow(self.window, self)
                self.theia_window.grab_set()  # Make window modal
        except Exception as e:
            self.logger.error(f"Error managing Theia control window: {e}")
            # Clean up reference if window is invalid
            if hasattr(self, 'theia_window'):
                delattr(self, 'theia_window')
            # Create new window
            self.theia_window = TheiaLensControlWindow(self.window, self)
            self.theia_window.grab_set()

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
