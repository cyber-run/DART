from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import customtkinter as ctk
from PIL import Image
import numpy as np
import serial



GLOBAL_FONT = ("default_theme", 15)

class DARTGUI:
    def __init__(self, window, dart_instance):
        # Store the window and dart instance
        self.window = window
        self.dart = dart_instance

        self.current_view = None

        # Set up persistent GUI elements
        self.setup_sidebar()
        self.setup_status_bar()

        # Set up track view
        self.setup_track_view()

    def setup_track_view(self):
        '''
        Set up the track view
        '''
        # Configure the row weights
        self.window.grid_rowconfigure(0, weight=1)
        # Configure the column weights
        self.window.grid_columnconfigure(1, weight=1)

        self.setup_motor_frame()
        self.setup_mocap_frame()
        self.setup_track_frame()
        self.setup_camera_frame()
        self.setup_video_frame()

    def setup_data_view(self):
        '''
        Set up the data analysis view
        '''
        self.setup_video_frame2()
        self.setup_plot_frame()

    def switch_view(self, view):
        '''
        Switch between the track view and data analysis view
        '''
        if view == "track" and self.current_view != "track":
            # Destroy the existing widgets in the data view if they exist
            self.current_view = "track"
            self.video_label2.grid_forget()
            self.plot_frame.grid_forget()

            # Set up the track view
            self.setup_track_view()
            
        elif view == "data" and self.current_view != "data":
            self.current_view = "data"
            # Destroy the existing widgets in the track view if they exist
            self.motor_frame.grid_forget()
            self.mocap_frame.grid_forget()
            self.track_frame.grid_forget()
            self.camera_frame.grid_forget()
            # Hide the video label
            self.video_label.grid_forget()

            # Set up the data analysis view
            self.setup_data_view()

    def setup_sidebar(self):
        '''
        Set up the sidebar with buttons for switching between views
        '''
        self.window.grid_columnconfigure(0, weight=0)  # Sidebar column

        self.sidebar_frame = ctk.CTkFrame(self.window, width=50, corner_radius=0, border_width=-2, border_color="#1c1c1c")
        self.sidebar_frame.grid(row=0, column=0, rowspan=5, sticky="nsw", padx=(0,5))
        fg_color1 = self.sidebar_frame.cget("fg_color")

        # Creating a thin frame to act as a stroke
        stroke_frame = ctk.CTkFrame(self.sidebar_frame, width=3, height=50, fg_color="white", bg_color="white")
        stroke_frame.pack(side="left", padx=(0, 0), pady=0, anchor="nw")  # Adjust padding for position

        home_button = ctk.CTkButton(
            self.sidebar_frame,
            text="",
            image=self.dart.home_icon,
            height=50,
            width=50,
            corner_radius=0,
            bg_color=fg_color1,
            fg_color=fg_color1,
            hover_color="#1c1c1c",
            command=lambda: self.switch_view("track")  # Switch to track view when clicked
        )
        home_button.pack(side="top", padx=0, pady=0)

        data_button = ctk.CTkButton(
            self.sidebar_frame,
            text="",
            image=self.dart.data_icon,
            height=50,
            width=50,
            corner_radius=0,
            bg_color=fg_color1,
            fg_color=fg_color1,
            hover_color="#1c1c1c",
            command=lambda: self.switch_view("data")  # Switch to data analysis view when clicked
        )
        data_button.pack(side="top", padx=0, pady=0)

        # data_button.bind("<Button-1>", lambda event: command()) # bind command
        data_button.pack(side="top", padx=0, pady=0)

    def setup_video_frame2(self):
        '''
        Set up the video feed for the data view
        '''
        self.video_label2 = ctk.CTkLabel(self.window, text="")
        self.video_label2.grid(row=0, column=1, rowspan=2, padx=5, pady=5)
        self.video_label2.configure(image=self.dart.small_placeholder_image)
    
    def setup_plot_frame(self):
        ''' 
        Set up the plot frame for the data view
        '''
        self.plot_frame = ctk.CTkFrame(self.window, width=400, height=200)
        self.plot_frame.grid(row=0, column=2, padx=5, pady=5)
        self.plot_frame.pack_propagate(False)

        # Generate random data for the plot
        trajectory_plot_data = np.random.rand(100)
        angle_plot_data = np.random.rand(100)

        # Create a figure and axis for trajectory plot
        trajectory_plot_fig, trajectory_plot_ax = plt.subplots()
        trajectory_plot_ax.plot(trajectory_plot_data)

        # Create a figure and axis for angle plot
        angle_plot_fig, angle_plot_ax = plt.subplots()
        angle_plot_ax.plot(angle_plot_data)

        # Create a canvas for trajectory plot
        trajectory_plot_canvas = FigureCanvasTkAgg(trajectory_plot_fig, self.plot_frame)
        trajectory_plot_canvas.get_tk_widget().pack(side="top", fill="both", expand=True, anchor="n")

        # Create a canvas for angle plot
        angle_plot_canvas = FigureCanvasTkAgg(angle_plot_fig, self.plot_frame)
        angle_plot_canvas.get_tk_widget().pack(side="top", fill="both", expand=True, anchor="center")

    def setup_video_frame(self):
        '''
        Set up the video feed for the track view
        '''
        self.video_label = ctk.CTkLabel(self.window, text="")
        self.video_label.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        self.video_label.configure(image=self.dart.placeholder_image)

    def setup_motor_frame(self):
        '''
        Set up the motor control frame for the track view
        '''
        self.motor_frame = ctk.CTkFrame(self.window)
        self.motor_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Get available serial ports for combo box
        serial_ports = get_serial_ports()

        # Serial port frame
        serial_frame = ctk.CTkFrame(self.motor_frame)
        serial_frame.pack(side="top", padx=10, pady=10)

        # Combo box for selecting the COM port
        self.dart.com_port_combobox = ctk.CTkComboBox(serial_frame, width=100, values=serial_ports,
                                                variable=self.dart.selected_com_port,
                                                command=lambda choice: self.dart.connect_dyna_controller())
        self.dart.com_port_combobox.pack(side="left", padx=5, pady=5)

        # Button refresh serial port list
        self.dart.serial_refresh = ctk.CTkButton(serial_frame, width=28, text="", 
                                            image=self.dart.refresh_icon, command=self.dart.update_serial_ports_dropdown)
        self.dart.serial_refresh.pack(side="left", padx=5, pady=5)

        # Motor control sub-frame
        control_frame = ctk.CTkFrame(self.motor_frame, height = 2000)
        control_frame.pack(side="top", padx=10, pady=10)

        # Frame for pan slider and label
        pan_frame = ctk.CTkFrame(control_frame, width=80, height = 500)
        pan_frame.grid(row=0, column=0, padx=0, pady=0)
        pan_frame.pack_propagate(False)  # Prevents the frame from resizing to fit the label
        self.dart.pan_label = ctk.CTkLabel(pan_frame, text="Pan: 0.0°", font=GLOBAL_FONT, padx=5, pady=5)
        self.dart.pan_label.pack()
        self.dart.pan_slider = ctk.CTkSlider(pan_frame, from_=-45, to=45, command=self.dart.set_pan, orientation="vertical", height=500)
        self.dart.pan_slider.set(self.dart.pan_value)
        self.dart.pan_slider.pack(padx=5, pady=5)

        # Frame for tilt slider and label
        tilt_frame = ctk.CTkFrame(control_frame, width=80, height = 500)
        tilt_frame.grid(row=0, column=1, padx=0, pady=0)  # Place it next to pan_frame using grid
        tilt_frame.pack_propagate(False)  # Prevents the frame from resizing to fit the label
        self.dart.tilt_label = ctk.CTkLabel(tilt_frame, text="Tilt: 0.0°", font=GLOBAL_FONT, padx=5, pady=5)
        self.dart.tilt_label.pack()
        self.dart.tilt_slider = ctk.CTkSlider(tilt_frame, from_=-45, to=45, command=self.dart.set_tilt, orientation="vertical", height=500)
        self.dart.tilt_slider.set(self.dart.tilt_value)
        self.dart.tilt_slider.pack(padx=5, pady=5)  # Packing inside tilt_frame is fine

        # Calibrate frame
        self.dart.calibrate_frame = ctk.CTkFrame(self.motor_frame)
        self.dart.calibrate_frame.pack(side="top", padx=10, pady=10)

        # Create a calibration button
        self.dart.calibration_button = ctk.CTkButton(self.dart.calibrate_frame, width = 80, text="Calibrate", command=self.dart.calibrate, font=GLOBAL_FONT)
        self.dart.calibration_button.pack(side="left", padx=10, pady=10)

        self.dart.centre_button = ctk.CTkButton(self.dart.calibrate_frame, width = 40, text="", image=self.dart.qtm_stream_icon, 
                                           command=self.dart.centre, font=GLOBAL_FONT)
        self.dart.centre_button.pack(side="left", padx=10, pady=10)

    def setup_mocap_frame(self):
        '''
        Set up the MoCap frame for the track view
        '''
        self.mocap_frame = ctk.CTkFrame(self.window)
        self.mocap_frame.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # Button to start/stop saving images
        self.dart.mocap_button = ctk.CTkButton(self.mocap_frame, width=80, text="MoCap", image=self.dart.sync_icon, 
                                          command=self.dart.mocap_button_press, font=GLOBAL_FONT)
        self.dart.mocap_button.pack(side="top", pady=10)

        # Checkbox to enable/disable crosshair used to help with calibration
        self.dart.crosshair_checkbox = ctk.CTkCheckBox(
            self.mocap_frame,
            text="Crosshair",
            variable=self.dart.show_crosshair,
            command=lambda: setattr(self.dart.image_pro, 'show_crosshair', self.dart.show_crosshair.get()),
            onvalue=True,
            offvalue=False, 
            font=GLOBAL_FONT
        )
        self.dart.crosshair_checkbox.pack(side="top", pady=10, expand=True)

        # MoCap number of markers indicator
        num_marker_frame = ctk.CTkFrame(self.mocap_frame)
        num_marker_frame.pack(side="top", padx=10, pady=10, expand=True)
        self.dart.num_marker_label = ctk.CTkLabel(num_marker_frame, text="No. Markers: 0", font=GLOBAL_FONT)
        self.dart.num_marker_label.pack(padx=5, pady=5)

    def setup_track_frame(self):
        '''
        Set up the track frame
        '''
        self.track_frame = ctk.CTkFrame(self.window)
        self.track_frame.grid(row=2, column=2, sticky="nsew", padx=5, pady=5)

        # Create a track button
        self.dart.track_button = ctk.CTkButton(self.track_frame, text="Track", command=self.dart.track, font=GLOBAL_FONT)
        self.dart.track_button.pack(side="top", padx=10, pady=10, anchor="center", expand=True)

    def setup_camera_frame(self):
        '''
        Set up the camera frame for the track view
        '''
        self.camera_frame = ctk.CTkFrame(self.window)
        self.camera_frame.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)

        # Camera combo box frame
        cam_frame = ctk.CTkFrame(self.camera_frame)
        cam_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True)

        # Dropdown combo box for selecting the camera
        self.dart.cam_combobox = ctk.CTkComboBox(cam_frame, width=100, values=[],
                                            variable=self.dart.selected_camera,
                                            command=self.dart.connect_camera)
        self.dart.cam_combobox.pack(side="left", padx=5, pady=5)

        # Button to refresh camera list
        self.dart.cam_refresh = ctk.CTkButton(cam_frame, width=28, text="", image=self.dart.refresh_icon,
                                        command=self.dart.update_camera_dropdown, font=GLOBAL_FONT)
        self.dart.cam_refresh.pack(side="left", padx=5, pady=5)

        # Button to start/stop live feed
        self.dart.toggle_video_button = ctk.CTkButton(self.camera_frame, width=80, text="Start", image=self.dart.play_icon,
                                                command=self.dart.toggle_video_feed, font=GLOBAL_FONT)
        self.dart.toggle_video_button.pack(side="left", padx=10, anchor="center", expand=True)

        # Frame for exposure slider and label
        exposure_frame = ctk.CTkFrame(self.camera_frame)
        exposure_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True, fill="x")
        self.dart.exposure_slider = ctk.CTkSlider(exposure_frame, width=140, from_=4, to=4000, command=self.dart.adjust_exposure)
        self.dart.exposure_slider.set(1000)
        self.dart.exposure_slider.pack(padx=5, pady=5, expand=True, fill="x")
        self.dart.exposure_label = ctk.CTkLabel(exposure_frame, text="Exposure (us): 1000", font=GLOBAL_FONT)
        self.dart.exposure_label.pack()

        # Frame for gain slider and label
        gain_frame = ctk.CTkFrame(self.camera_frame)
        gain_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True, fill="x")
        self.dart.gain_slider = ctk.CTkSlider(gain_frame, width =140, from_=0, to=47, command=self.dart.adjust_gain)
        self.dart.gain_slider.set(10) 
        self.dart.gain_slider.pack(padx=5, pady=5, expand=True, fill="x")
        self.dart.gain_label = ctk.CTkLabel(gain_frame, text="Gain: 10", font=GLOBAL_FONT)
        self.dart.gain_label.pack()

        # Frame for video path and file name
        video_path_frame = ctk.CTkFrame(self.camera_frame)
        video_path_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True)

        # Button to open folder dialog
        self.dart.file_button = ctk.CTkButton(video_path_frame, width=28, text="", image=self.dart.folder_icon, command=self.dart.select_folder, font=GLOBAL_FONT)
        self.dart.file_button.pack(side="left", padx=5, pady=5)

        # Text entry field for initial file name
        self.dart.file_name_entry = ctk.CTkEntry(video_path_frame, width=120, placeholder_text="Enter file name", font=GLOBAL_FONT)
        self.dart.file_name_entry.pack(side="left", padx=5, pady=5)

        # Button to start/stop recording
        self.dart.record_button = ctk.CTkButton(self.camera_frame, width=90, text="Record", image=self.dart.record_icon, command=self.dart.toggle_record, font=GLOBAL_FONT)
        self.dart.record_button.pack(side="left", padx=10, anchor="center", expand=True)

        # Button to pause recording
        self.dart.pause_button = ctk.CTkButton(self.camera_frame, width=100, text="Pause", image=self.dart.pause_icon, command=self.dart.toggle_pause, state="disabled", font=GLOBAL_FONT)
        self.dart.pause_button.pack(side="left", padx=10, anchor="center", expand=True)

        # FPS indicator display
        fps_frame = ctk.CTkFrame(self.camera_frame)
        fps_frame.pack(side="right", padx=10, pady=10, anchor="e", expand=True)
        self.dart.fps_label = ctk.CTkLabel(fps_frame, text=f"FPS: {round(self.dart.camera_manager.fps, 2)}", font=GLOBAL_FONT)
        self.dart.fps_label.pack(padx=5, pady=5)

    def setup_status_bar(self):
        '''
        Set up the status bar at the bottom of the window
        '''
        self.dart.status_bar = ctk.CTkFrame(self.window, height=4, corner_radius=0, border_width=-2, border_color="#1c1c1c")
        self.dart.status_bar.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(5,0))

        # Add label to status bar
        self.dart.status_label = ctk.CTkLabel(self.dart.status_bar, text=self.dart.app_status, height=18, font=("default_theme", 14))
        self.dart.status_label.pack(side="left", padx=10, pady=0, anchor="center")

        # Camera connection status
        self.dart.camera_status = ctk.CTkLabel(self.dart.status_bar, text="Camera: -", font=("default_theme", 14), height=18)
        self.dart.camera_status.pack(side="left", padx=10)

        # Mocap connection status
        self.dart.mocap_status = ctk.CTkLabel(self.dart.status_bar, text="Mocap: -", font=("default_theme", 14), height=18)
        self.dart.mocap_status.pack(side="left", padx=10)

        # Motors connection status
        self.dart.motors_status = ctk.CTkLabel(self.dart.status_bar, text="Motors: -", font=("default_theme", 14), height=18)
        self.dart.motors_status.pack(side="left", padx=10)

        self.dart.age_label = ctk.CTkLabel(self.dart.status_bar, text=f"Calibration age: {int(self.dart.calibrator.calibration_age)} h", height=18, font=("default_theme", 14))
        self.dart.age_label.pack(side="left", padx=10, pady=0, anchor="e", expand=True)

        self.dart.memory_label = ctk.CTkLabel(self.dart.status_bar, text=f"Memory usage: {self.dart.memory_usage}%", height=18, font=("default_theme", 14))
        self.dart.memory_label.pack(side="right", padx=10, pady=0, anchor="e", expand=False)
        self.dart.get_mem()

def get_serial_ports() -> list:
    """Lists available serial ports.

    :return: A list of serial port names available on the system.
    """
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]