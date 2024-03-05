import logging
logging.basicConfig(level=logging.INFO)

from dyna_controller import DynaController
from camera_manager import CameraManager
from image_processor import ImageProcessor
from calibrate import Calibrator
from dart_track import dart_track
from CTkMessagebox import CTkMessagebox
from multiprocessing import Process
from PIL import Image, ImageTk
import customtkinter as ctk
from mocap_stream import *
import vec_math2 as vm2
import tkinter as tk
import numpy as np
import cProfile
import pickle
import time
import cv2
import os


class DART:
    def __init__(self, window: ctk.CTk):
        self.init_window(window)
        self.init_hardware()

        self.init_gui_flags()
        self.setup_gui_elements()

        self.set_pan(0)
        self.set_tilt(0)

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def init_window(self, window):
        self.window = window
        self.window.title("DART")

    def init_hardware(self):
        # Create an instance of ImageProcessor
        self.image_pro = ImageProcessor()

        # Create an instance of CameraManager
        self.camera_manager = CameraManager()

        # Create an instance of Calibrator
        self.calibrator = Calibrator()
        
        # try:
        #     self.target = MoCap(stream_type='3d')
        #     self.target.calibration_target = True
        # except Exception as e:
        #     logging.error(f"Error connecting to QTM: {e}")
        #     self.target = None

        try:
            self.dyna = DynaController(com_port='COM5')
            self.dyna.open_port()
            self.dyna.set_op_mode(1, 3)  # Pan to position control
            self.dyna.set_op_mode(2, 3)  # Tilt to position control
            self.dyna.set_sync_pos(225, 315)
        except:
            logging.error("Error connecting to Dynamixel controller.")
            self.dyna = None

    def init_gui_flags(self):
        # Camera/image functionality
        self.is_live = False
        self.is_saving_images = False
        self.image_folder = "images"

        # Image processing GUI flags
        self.show_crosshair = tk.BooleanVar(value=False)
        self.threshold_flag = tk.BooleanVar(value=False)
        self.detect_flag = tk.BooleanVar(value=False)

        # Motor control values
        self.pan_value = 0
        self.tilt_value = 0

    def setup_gui_elements(self):
        self.video_label = ctk.CTkLabel(self.window, text="")
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ################## Frame for motor controls ##################
        dyn_control_frame = ctk.CTkFrame(self.window)
        dyn_control_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)  # Increase vertical padding

        # Frame for pan slider and label
        pan_frame = ctk.CTkFrame(dyn_control_frame)
        pan_frame.pack(side="top", padx=10, pady=10)
        self.pan_slider = ctk.CTkSlider(pan_frame, from_=-45, to=45, command=self.set_pan)
        self.pan_slider.set(self.pan_value)
        self.pan_slider.pack(padx =5, pady=5)
        self.pan_label = ctk.CTkLabel(pan_frame, text="Pan angle: 0")
        self.pan_label.pack()

        # Frame for tilt slider and label
        tilt_frame = ctk.CTkFrame(dyn_control_frame)
        tilt_frame.pack(side="top", padx=10, pady=10)
        self.tilt_slider = ctk.CTkSlider(tilt_frame, from_=-45, to=45, command=self.set_tilt)
        self.tilt_slider.set(self.tilt_value)
        self.tilt_slider.pack(padx =5, pady=5)
        self.tilt_label = ctk.CTkLabel(tilt_frame, text="Tilt angle: 0")
        self.tilt_label.pack()

        # Create a calibration button
        self.calibration_button = ctk.CTkButton(dyn_control_frame, text="Calibrate", command=self.calibrate)
        self.calibration_button.pack(side="top", padx=10, pady=10)

        # Create a track button
        self.track_button = ctk.CTkButton(dyn_control_frame, text="Track", command=self.track)
        self.track_button.pack(side="top", padx=10, pady=10)

        ################## Frame for camera controls ##################
        camera_control_frame = ctk.CTkFrame(self.window)
        camera_control_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)  # Increase vertical padding

        # Button to start/stop live feed
        self.toggle_video_button = ctk.CTkButton(camera_control_frame, text="Start Live Feed", command=self.toggle_video_feed)
        self.toggle_video_button.pack(side="left", padx=10)

        # Button to start/stop saving images
        self.record_button = ctk.CTkButton(camera_control_frame, text="Start Saving Images", command=self.toggle_image_saving)
        self.record_button.pack(side="left", padx=10)

        # Frame for exposure slider and label
        exposure_frame = ctk.CTkFrame(camera_control_frame)
        exposure_frame.pack(side="left", padx=10, pady = 10)
        self.exposure_slider = ctk.CTkSlider(exposure_frame, from_=1, to=100000, command=self.adjust_exposure)
        self.exposure_slider.set(50)
        self.exposure_slider.pack(padx =5, pady=5)
        self.exposure_label = ctk.CTkLabel(exposure_frame, text="Exposure (us): 57500")
        self.exposure_label.pack()

        ################## Frame for image processing detect ##################
        img_processing_frame = ctk.CTkFrame(self.window)
        img_processing_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)  # Increase vertical padding

        self.crosshair_checkbox = ctk.CTkCheckBox(
            img_processing_frame,
            text="Crosshair",
            variable=self.show_crosshair,
            command=lambda: setattr(self.image_pro, 'show_crosshair', self.show_crosshair.get()),
            onvalue=True,
            offvalue=False
        )
        self.crosshair_checkbox.pack(side="left", padx=10)

        self.detect_checkbox = ctk.CTkCheckBox(
            img_processing_frame,
            text="Detect",
            variable=self.detect_flag,
            command=lambda: setattr(self.image_pro, 'detect_circle_flag', self.detect_flag.get()),
            onvalue=True,
            offvalue=False
        )
        self.detect_checkbox.pack(side="left", padx=10)

        # Frame for threshold slider and label
        threshold_frame = ctk.CTkFrame(img_processing_frame)
        threshold_frame.pack(side="left", padx=10, pady=10)
        self.threshold_slider = ctk.CTkSlider(threshold_frame, from_=0, to=255, command=self.set_threshold)
        self.threshold_slider.set(70)
        self.threshold_slider.pack(padx =5, pady=5)
        self.threshold_label = ctk.CTkLabel(threshold_frame, text="Threshold: 70")
        self.threshold_label.pack()

        # Frame for strength slider and label
        strength_frame = ctk.CTkFrame(img_processing_frame)
        strength_frame.pack(side="left", padx=10, pady=10)
        self.strength_slider = ctk.CTkSlider(strength_frame, from_=30, to=100, command=self.set_strength)
        self.strength_slider.set(60)
        self.strength_slider.pack(padx =5, pady=5)
        self.strength_label = ctk.CTkLabel(strength_frame, text="Strength: 60")
        self.strength_label.pack()

    def calibrate(self):
        p1 = np.array(self.target.position)
        p2 = np.array(self.target.position2)
        self.calibrator.run(p1, p2)

    def track(self):
        if self.calibrator.calibrated:
            # Close QTM connections
            self.target._close()
            self.target.close()

            # Close serial port
            self.dyna.close_port()

            time.sleep(1) # HACK: Add small blocking delay to allow serial port to close

            self.track_process = Process(target=dart_track)
            self.track_process.start()
        else:
            # Add popup window to notify user that DART is not calibrated
            CTkMessagebox(title="Error", message="DART Not Calibrated", icon="cancel")
            logging.error("DART is not calibrated.")

    def toggle_video_feed(self):
        self.is_live = not self.is_live
        self.toggle_video_button.configure(text="Stop Live Feed" if self.is_live else "Start Live Feed")
        if self.is_live:
            self.update_video_label()

    def toggle_image_saving(self):
        self.camera_manager.release()
        self.is_saving_images = not self.is_saving_images
        self.record_button.configure(text="Stop Saving Images" if self.is_saving_images else "Start Saving Images")

    def adjust_exposure(self, exposure_value: float):
        if self.camera_manager.cap:
            try:
                self.camera_manager.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
                self.exposure_label.configure(text=f"Exposure (us): {exposure_value}")
            except AttributeError:
                logging.error("Exposure not set.")

    def update_video_label(self):
        if self.is_live:
            ret, frame = self.camera_manager.read_frame()
            if ret:
                # Flip the frame horizontally
                frame = cv2.flip(frame, 1)
                
                # Process the frame with all the selected options
                processed_frame = self.image_pro.process_frame(frame)
                self.display_frame(processed_frame)
                
                # Save the original or processed frame if needed
                self.save_frame(processed_frame)

            self.window.after(30, self.update_video_label)

    def display_frame(self, frame):
        cv_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(cv_img)
        imgtk = ImageTk.PhotoImage(image=pil_img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def save_frame(self, frame):
        if self.is_saving_images:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = os.path.join(self.image_folder, f"image_{timestamp}.png")
            cv2.imwrite(filename, frame)

    def set_threshold(self, value: float):
        self.image_pro.threshold_value = int(value)
        self.threshold_label.configure(text=f"Threshold: {int(value)}")

    def set_strength(self, value: float):
        self.image_pro.strength_value = int(value)
        self.strength_label.configure(text=f"Strength: {int(value)}")

    def set_pan(self, value: float):
        self.pan_value = int(value)
        self.pan_label.configure(text=f"Pan angle: {int(value)}")
        angle = vm2.num_to_range(self.pan_value, -45, 45, 202.5, 247.5)
        self.dyna.set_pos(1, angle)

    def set_tilt(self, value: float):
        self.tilt_value = int(value)
        self.tilt_label.configure(text=f"Tilt angle: {int(value)}")
        angle = vm2.num_to_range(self.tilt_value, -45, 45, 292.5, 337.5)
        self.dyna.set_pos(2, angle)

    def on_closing(self):
        try:
            self.target._close()
            self.target.close()
        except Exception as e:
            logging.error(f"Error closing QTM connection: {e}")
            
        try:
            # Close the camera
            self.is_live = False
            self.camera_manager.release()
        except Exception as e:
            logging.error(f"Error closing camera or serial port: {e}")

        try:
            # Close the serial port
            self.dyna.close_port()
        except Exception as e:
            logging.error(f"Error closing serial port: {e}")

        # Terminate subprocess
        if hasattr(self, 'track_process') and self.track_process.is_alive():
            try:
                self.track_process.terminate()
                self.track_process.join()  # Wait for the process to terminate
            except Exception as e:
                logging.error(f"Error terminating track process: {e}")

        try:
            self.window.destroy()
        except Exception as e:
            logging.error(f"Error closing window: {e}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = DART(root)
    # cProfile.run('app = DART(root)')
