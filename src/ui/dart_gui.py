from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.views.theia_control_window import TheiaLensControlWindow
from hardware.motion.theia_controller import TheiaController
import matplotlib.pyplot as plt
import customtkinter as ctk
from CTkMenuBar import *
from PIL import Image
import numpy as np
import serial, os


GLOBAL_FONT = ("default_theme", 14)

class DARTGUI:
    def __init__(self, window, dart_instance):
        # Store the window and dart instance
        self.window = window
        self.dart = dart_instance

        self.current_view = None

        # Set up persistent GUI elements
        self.setup_sidebar()
        self.setup_status_bar()
        self.setup_menu_bar()

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
        self.window.grid_columnconfigure(2, weight=0)

        # self.setup_video_frame()
        self.setup_video_frame()
        self.setup_motor_frame()
        self.setup_mocap_frame()
        self.setup_track_frame()
        self.setup_camera_frame()

    def setup_data_view(self):
        '''
        Set up the data analysis view
        '''
        # Configure the column weights
        self.window.grid_columnconfigure(2, weight=1)
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
            self.home_button.configure(fg_color="#27272a")
            self.data_button.configure(fg_color=self.fg_color1)
            
        elif view == "data" and self.current_view != "data":
            self.current_view = "data"
            # Hide the video label
            self.video_label.grid_forget()
            # Destroy the existing widgets in the track view if they exist
            self.motor_frame.grid_forget()
            self.mocap_frame.grid_forget()
            self.track_frame.grid_forget()
            self.camera_frame.grid_forget()

            # Set up the data analysis view
            self.setup_data_view()
            self.data_button.configure(fg_color="#27272a")
            self.home_button.configure(fg_color=self.fg_color1)

    def setup_menu_bar(self):
        '''
        Set up the menu bar
        '''
        # Create the title menu if windows else create menu bar
        title_menu = CTkTitleMenu(self.window) if os.name == "nt" else CTkMenuBar(self.window)

        file_menu = title_menu.add_cascade(text="File")
        file_dropdown = CustomDropdownMenu(widget=file_menu)
        file_dropdown.add_option(option="Track", command=self.dart.track)
        file_dropdown.add_separator()
        file_dropdown.add_option(option="Exit", command=self.dart.on_closing)

        # Add Tools menu
        tools_menu = title_menu.add_cascade(text="Tools")
        tools_dropdown = CustomDropdownMenu(widget=tools_menu)
        tools_dropdown.add_option(option="Lens Control", command=self.open_theia_control_window)

    def open_theia_control_window(self):
        if not hasattr(self, 'theia_controller'):
            # Initialize the Theia controller with a default port
            # You might want to make this configurable or use a method to detect the correct port
            self.theia_controller = TheiaController(port="COM17")
        
        # Create and show the Theia Lens Control window
        self.theia_window = TheiaLensControlWindow(self.window, self.theia_controller)
        self.theia_window.grab_set()  # Make the window modal

    def setup_sidebar(self):
        '''
        Set up the sidebar with buttons for switching between views
        '''
        self.window.grid_columnconfigure(0, weight=0)  # Sidebar column

        self.sidebar_frame = ctk.CTkFrame(self.window, width=50, corner_radius=0, border_width=-2, border_color="#1c1c1c")
        self.sidebar_frame.grid(row=0, column=0, rowspan=5, sticky="nsw", padx=(0,5))
        self.fg_color1 = self.sidebar_frame.cget("fg_color")

        self.home_button = ctk.CTkButton(
            self.sidebar_frame,
            text="",
            image=self.dart.state.get_icon('home'),
            height=40,
            width=40,
            corner_radius=5,
            fg_color="#27272a",
            hover_color="#1c1c1c",
            command=lambda: self.switch_view("track")  # Switch to track view when clicked
        )
        self.home_button.pack(side="top", padx=5, pady=5)

        self.data_button = ctk.CTkButton(
            self.sidebar_frame,
            text="",
            image=self.dart.state.get_icon('data'),
            height=40,
            width=40,
            corner_radius=5,
            fg_color=self.fg_color1,
            hover_color="#1c1c1c",
            command=lambda: self.switch_view("data")  # Switch to data analysis view when clicked
        )
        self.data_button.pack(side="top", padx=5, pady=5)

    def setup_video_frame2(self):
        '''
        Set up the video feed for the data view
        '''
        self.video_label2 = ctk.CTkLabel(self.window, text="")
        self.video_label2.grid(row=0, column=1, rowspan=2, padx=5, pady=5)
        self.video_label2.configure(image=self.dart.state.get_icon('small_placeholder'))
    
    def setup_plot_frame(self):
        ''' 
        Set up the plot frame for the data view
        '''
        self.plot_frame = ctk.CTkFrame(self.window)
        self.plot_frame.grid(row=0, column=2, padx=5, pady=5)

        # Use the dark background style
        plt.style.use('dark_background')

        # Generate random data for the plot
        trajectory_plot_data = np.random.rand(50)
        angle_plot_data = np.random.rand(50)

        # Create a figure and axis for trajectory plot
        trajectory_plot_fig, trajectory_plot_ax = plt.subplots(figsize=(5, 3))
        trajectory_plot_ax.plot(trajectory_plot_data)
        trajectory_plot_fig.set_facecolor("none")

        # Create a figure and axis for angle plot
        angle_plot_fig, angle_plot_ax = plt.subplots(figsize=(5, 3))
        angle_plot_ax.plot(angle_plot_data)
        angle_plot_fig.set_facecolor("none")

        # Create a canvas for trajectory plot
        trajectory_plot_canvas = FigureCanvasTkAgg(trajectory_plot_fig, self.plot_frame)
        trajectory_plot_canvas.get_tk_widget().configure(bg="#09090b")
        trajectory_plot_canvas.get_tk_widget().pack(side="top", fill="both", expand=True, anchor="center", pady=20, padx=20)

        # Create a canvas for angle plot
        angle_plot_canvas = FigureCanvasTkAgg(angle_plot_fig, self.plot_frame)
        angle_plot_canvas.get_tk_widget().configure(bg="#09090b")
        angle_plot_canvas.get_tk_widget().pack(side="top", fill="both", expand=True, anchor="center", pady=20, padx=20)

    def setup_video_frame(self):
        '''
        Set up the video feed for the track view
        '''
        self.video_label = ctk.CTkLabel(self.window, text="")
        self.video_label.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        self.video_label.configure(image=self.dart.state.get_icon('placeholder'))

    def setup_motor_frame(self):
        '''
        Set up the motor control frame for the track view
        '''
        self.motor_frame = ctk.CTkFrame(self.window)
        self.motor_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Get available serial ports for combo box
        serial_ports = get_serial_ports()

        # Serial port frame
        serial_frame = ctk.CTkFrame(self.motor_frame, fg_color="transparent")
        serial_frame.pack(side="top", padx=10, pady=10)

        # Combo box for selecting the COM port
        self.dart.state.ui.com_port_combobox = ctk.CTkComboBox(
            serial_frame, 
            width=100, 
            values=serial_ports,
            variable=self.dart.state.hardware.selected_com_port,
            command=lambda choice: self.dart.connect_dyna_controller()
        )
        self.dart.state.ui.com_port_combobox.pack(side="left", padx=5, pady=5)

        # Button refresh serial port list
        self.dart.serial_refresh = ctk.CTkButton(
            serial_frame, 
            width=28, 
            text="", 
            image=self.dart.state.get_icon('refresh'), 
            command=self.dart.update_serial_ports_dropdown
        )
        self.dart.serial_refresh.pack(side="left", padx=5, pady=5)

        # Checkbox to enable/disable motor torque
        self.dart.torque_checkbox = ctk.CTkCheckBox(
            self.motor_frame,
            text="Torque",
            variable=self.dart.state.flags['torque'],
            command=self.dart.set_torque,
            onvalue=True,
            offvalue=False
        )
        self.dart.torque_checkbox.pack(side="top", pady=10, expand=False)

        # Motor control sub-frame
        control_frame = ctk.CTkFrame(self.motor_frame, height = 2000, fg_color="transparent")
        control_frame.pack(side="top", padx=10, pady=10)

        # Frame for pan slider and label
        pan_frame = ctk.CTkFrame(control_frame, width=80, height=500, fg_color="transparent")
        pan_frame.grid(row=0, column=0, padx=0, pady=0)
        pan_frame.pack_propagate(False)  # Prevents the frame from resizing to fit the label
        
        # Store pan label in state
        self.dart.state.ui.pan_label = ctk.CTkLabel(
            pan_frame, 
            text="Pan: 0.0°", 
            font=GLOBAL_FONT, 
            padx=5, 
            pady=5
        )
        self.dart.state.ui.pan_label.pack()
        
        # Store pan slider in state
        self.dart.state.ui.pan_slider = ctk.CTkSlider(
            pan_frame, 
            from_=-45, 
            to=45, 
            command=self.dart.set_pan, 
            orientation="vertical", 
            height=500
        )
        # Set initial value from state
        self.dart.state.ui.pan_slider.set(self.dart.state.motor['pan_value'])
        self.dart.state.ui.pan_slider.pack(padx=5, pady=5)

        # Frame for tilt slider and label
        tilt_frame = ctk.CTkFrame(control_frame, width=80, height=500)
        tilt_frame.grid(row=0, column=1, padx=0, pady=0)
        tilt_frame.pack_propagate(False)
        
        # Store tilt label in state
        self.dart.state.ui.tilt_label = ctk.CTkLabel(
            tilt_frame, 
            text="Tilt: 0.0°", 
            font=GLOBAL_FONT, 
            padx=5, 
            pady=5
        )
        self.dart.state.ui.tilt_label.pack()
        
        # Store tilt slider in state
        self.dart.state.ui.tilt_slider = ctk.CTkSlider(
            tilt_frame, 
            from_=-45, 
            to=45, 
            command=self.dart.set_tilt, 
            orientation="vertical", 
            height=500
        )
        # Set initial value from state
        self.dart.state.ui.tilt_slider.set(self.dart.state.motor['tilt_value'])
        self.dart.state.ui.tilt_slider.pack(padx=5, pady=5)

        # Calibrate frame
        self.dart.calibrate_frame = ctk.CTkFrame(self.motor_frame, fg_color="transparent")
        self.dart.calibrate_frame.pack(side="top", padx=10, pady=10)

        # Create a calibration button
        self.dart.calibration_button = ctk.CTkButton(self.dart.calibrate_frame, width = 80, text="Calibrate", command=self.dart.calibrate, font=GLOBAL_FONT)
        self.dart.calibration_button.pack(side="left", padx=10, pady=10)

        self.dart.centre_button = ctk.CTkButton(self.dart.calibrate_frame, width = 40, text="", image=self.dart.state.get_icon('qtm_stream'), 
                                           command=self.dart.centre, font=GLOBAL_FONT)
        self.dart.centre_button.pack(side="left", padx=10, pady=10)

    def setup_mocap_frame(self):
        '''
        Set up the MoCap frame for the track view
        '''
        self.mocap_frame = ctk.CTkFrame(self.window)
        self.mocap_frame.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # Button to start/stop saving images
        self.dart.state.ui.mocap_button = ctk.CTkButton(
            self.mocap_frame, 
            width=80, 
            text="MoCap", 
            image=self.dart.state.get_icon('sync'), 
            command=self.dart.mocap_button_press, 
            font=GLOBAL_FONT
        )
        self.dart.state.ui.mocap_button.pack(side="top", pady=10)

        # Checkbox to enable/disable crosshair
        self.dart.state.ui.crosshair_checkbox = ctk.CTkCheckBox(
            self.mocap_frame,
            text="Crosshair",
            variable=self.dart.state.flags['crosshair'],
            command=lambda: setattr(self.dart.image_pro, 'show_crosshair', 
                                  self.dart.state.flags['crosshair'].get()),
            onvalue=True,
            offvalue=False, 
            font=GLOBAL_FONT
        )
        self.dart.state.ui.crosshair_checkbox.pack(side="top", pady=10, expand=True)

        # MoCap number of markers indicator
        num_marker_frame = ctk.CTkFrame(self.mocap_frame, fg_color="transparent")
        num_marker_frame.pack(side="top", padx=10, pady=10, expand=True)
        self.dart.state.ui.num_marker_label = ctk.CTkLabel(
            num_marker_frame, 
            text="No. Markers: 0", 
            font=GLOBAL_FONT
        )
        self.dart.state.ui.num_marker_label.pack(padx=5, pady=5)

    def setup_track_frame(self):
        '''
        Set up the track frame
        '''
        self.track_frame = ctk.CTkFrame(self.window)
        self.track_frame.grid(row=2, column=2, sticky="nsew", padx=5, pady=5)

        # Create a track button and store it in state
        self.dart.state.ui.track_button = ctk.CTkButton(
            self.track_frame, 
            text="Track", 
            command=self.dart.track, 
            font=GLOBAL_FONT
        )
        self.dart.state.ui.track_button.pack(side="top", padx=10, pady=10, anchor="center", expand=True)

    def setup_camera_frame(self):
        '''
        Set up the camera frame for the track view
        '''
        self.camera_frame = ctk.CTkFrame(self.window)
        self.camera_frame.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)

        # Camera combo box frame
        cam_frame = ctk.CTkFrame(self.camera_frame, fg_color="transparent")
        cam_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True)

        # Dropdown combo box for selecting the camera
        self.dart.state.ui.cam_combobox = ctk.CTkComboBox(
            cam_frame, 
            width=100, 
            values=[],
            variable=self.dart.state.hardware.selected_camera,
            command=self.dart.connect_camera
        )
        self.dart.state.ui.cam_combobox.pack(side="left", padx=5, pady=5)

        # Button to refresh camera list
        self.dart.cam_refresh = ctk.CTkButton(cam_frame, width=28, text="", image=self.dart.state.get_icon('refresh'),
                                        command=self.dart.update_camera_dropdown, font=GLOBAL_FONT)
        self.dart.cam_refresh.pack(side="left", padx=5, pady=5)

        # Button to start/stop live feed
        self.dart.state.ui.toggle_video_button = ctk.CTkButton(
            self.camera_frame, 
            width=80, 
            text="Start", 
            image=self.dart.state.get_icon('play'),
            command=self.dart.toggle_video_feed, 
            font=GLOBAL_FONT
        )
        self.dart.state.ui.toggle_video_button.pack(side="left", padx=10, anchor="center", expand=True)

        # Frame for exposure slider and label
        exposure_frame = ctk.CTkFrame(self.camera_frame, fg_color="transparent")
        exposure_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True, fill="x")
        self.dart.state.ui.exposure_slider = ctk.CTkSlider(exposure_frame, width=140, from_=4, to=4000, command=self.dart.adjust_exposure)
        self.dart.state.ui.exposure_slider.set(1000)
        self.dart.state.ui.exposure_slider.pack(padx=5, pady=5, expand=True, fill="x")
        self.dart.state.ui.exposure_label = ctk.CTkLabel(exposure_frame, text="Exposure (us): 1000", font=GLOBAL_FONT)
        self.dart.state.ui.exposure_label.pack()

        # Frame for gain slider and label
        gain_frame = ctk.CTkFrame(self.camera_frame, fg_color="transparent")
        gain_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True, fill="x")
        self.dart.state.ui.gain_slider = ctk.CTkSlider(gain_frame, width =140, from_=0, to=47, command=self.dart.adjust_gain)
        self.dart.state.ui.gain_slider.set(10) 
        self.dart.state.ui.gain_slider.pack(padx=5, pady=5, expand=True, fill="x")
        self.dart.state.ui.gain_label = ctk.CTkLabel(gain_frame, text="Gain (dB): 10", font=GLOBAL_FONT)
        self.dart.state.ui.gain_label.pack()

        # Frame for video path and file name
        video_path_frame = ctk.CTkFrame(self.camera_frame, fg_color="transparent")
        video_path_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True)

        # Button to open folder dialog
        self.dart.state.ui.file_button = ctk.CTkButton(video_path_frame, width=28, text="", image=self.dart.state.get_icon('folder'), command=self.dart.select_folder, font=GLOBAL_FONT)
        self.dart.state.ui.file_button.pack(side="left", padx=5, pady=5)

        # Text entry field for initial file name
        self.dart.state.ui.file_name_entry = ctk.CTkEntry(video_path_frame, width=120, placeholder_text="Enter file name", font=GLOBAL_FONT)
        self.dart.state.ui.file_name_entry.pack(side="left", padx=5, pady=5)

        # Button to start/stop recording
        self.dart.state.ui.record_button = ctk.CTkButton(self.camera_frame, width=90, text="Record", image=self.dart.state.get_icon('record'), command=self.dart.toggle_record, font=GLOBAL_FONT)
        self.dart.state.ui.record_button.pack(side="left", padx=10, anchor="center", expand=True)

        # Button to pause recording
        self.dart.state.ui.pause_button = ctk.CTkButton(self.camera_frame, width=100, text="Pause", image=self.dart.state.get_icon('pause'), command=self.dart.toggle_pause, state="disabled", font=GLOBAL_FONT)
        self.dart.state.ui.pause_button.pack(side="left", padx=10, anchor="center", expand=True)

        # FPS indicator display
        fps_frame = ctk.CTkFrame(self.camera_frame, fg_color="transparent")
        fps_frame.pack(side="right", padx=10, pady=10, anchor="e", expand=True)
        self.dart.state.ui.fps_label = ctk.CTkLabel(fps_frame, text=f"FPS: {round(self.dart.camera_manager.fps, 2)}", font=GLOBAL_FONT)
        self.dart.state.ui.fps_label.pack(padx=5, pady=5)

    def setup_status_bar(self):
        '''Set up the status bar at the bottom of the window'''
        self.dart.state.ui.status_bar = ctk.CTkFrame(
            self.window, 
            height=4, 
            corner_radius=0, 
            border_width=-2, 
            border_color="#1c1c1c"
        )
        self.dart.state.ui.status_bar.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(5,0))

        # Add label to status bar
        self.dart.state.ui.status_label = ctk.CTkLabel(
            self.dart.state.ui.status_bar, 
            text=self.dart.state.status['app_status'], 
            height=18, 
            font=("default_theme", 14)
        )
        self.dart.state.ui.status_label.pack(side="left", padx=10, pady=0, anchor="center")

        # Camera connection status
        self.dart.state.ui.camera_status = ctk.CTkLabel(
            self.dart.state.ui.status_bar, 
            text="Camera: -", 
            font=("default_theme", 14), 
            height=18
        )
        self.dart.state.ui.camera_status.pack(side="left", padx=10)

        # Mocap connection status
        self.dart.state.ui.mocap_status = ctk.CTkLabel(
            self.dart.state.ui.status_bar, 
            text="Mocap: -", 
            font=("default_theme", 14), 
            height=18
        )
        self.dart.state.ui.mocap_status.pack(side="left", padx=10)

        # Motors connection status
        self.dart.state.ui.motors_status = ctk.CTkLabel(
            self.dart.state.ui.status_bar, 
            text="Motors: -", 
            font=("default_theme", 14), 
            height=18
        )
        self.dart.state.ui.motors_status.pack(side="left", padx=10)

        # Calibration age
        self.dart.state.ui.age_label = ctk.CTkLabel(
            self.dart.state.ui.status_bar, 
            text=f"Calibration age: {int(self.dart.calibrator.calibration_age)} h", 
            height=18, 
            font=("default_theme", 14)
        )
        self.dart.state.ui.age_label.pack(side="left", padx=10, pady=0, anchor="e", expand=True)

        # Memory usage
        self.dart.state.ui.memory_label = ctk.CTkLabel(
            self.dart.state.ui.status_bar, 
            text=f"Memory usage: {self.dart.state.status['memory_usage']}%", 
            height=18, 
            font=("default_theme", 14)
        )
        self.dart.state.ui.memory_label.pack(side="right", padx=10, pady=0, anchor="e", expand=False)
        
        # Start memory monitoring
        self.dart.get_mem()

    def cleanup_resources(self):
        # Close and destroy all figures
        plt.close('all')
        
        # Destroy all widgets
        for widget in self.window.winfo_children():
            widget.destroy()

def get_serial_ports() -> list:
    """Lists available serial ports.

    :return: A list of serial port names available on the system.
    """
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]