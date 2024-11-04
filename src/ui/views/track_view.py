from ui.views.base_view import BaseView
import customtkinter as ctk
from typing import Callable
import serial.tools.list_ports

GLOBAL_FONT = ("default_theme", 14)
BG_COLOR = "#151518"        # Darker background for main view
FRAME_COLOR = "#09090b"     # Slightly lighter for control containers
TRANSPARENT = "transparent"  # For nested frames that should inherit parent color

class TrackView(BaseView):
    def __init__(self, parent, dart_instance):
        # Call parent's __init__ with both arguments
        super().__init__(parent, dart_instance)
        self.configure(fg_color=BG_COLOR)

    def setup_ui(self):
        """Initialize track view UI"""
        # Configure the grid
        self.grid_columnconfigure(1, weight=1)  # Video column
        self.grid_columnconfigure(2, weight=0)  # Controls column
        self.grid_rowconfigure(0, weight=1)     # Main content

        # Setup components
        self.setup_video_frame()
        self.setup_motor_frame()
        self.setup_mocap_frame()
        self.setup_track_frame()
        self.setup_camera_frame()

    def setup_video_frame(self):
        """Set up the video feed"""
        self.dart.state.ui.video_label = ctk.CTkLabel(self, text="")
        self.dart.state.ui.video_label.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        self.dart.state.ui.video_label.configure(image=self.dart.state.get_icon('placeholder'))

    def setup_motor_frame(self):
        """Set up motor controls"""
        self.motor_frame = ctk.CTkFrame(self)
        self.motor_frame.configure(fg_color=FRAME_COLOR)
        self.motor_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Get available serial ports
        serial_ports = [port.device for port in serial.tools.list_ports.comports()]

        # Serial port frame
        serial_frame = ctk.CTkFrame(self.motor_frame, fg_color=TRANSPARENT)
        serial_frame.pack(side="top", padx=10, pady=10)

        # COM port selection
        self.dart.state.ui.com_port_combobox = ctk.CTkComboBox(
            serial_frame, 
            width=100, 
            values=serial_ports,
            variable=self.dart.state.hardware.selected_com_port,
            command=lambda choice: self.dart.connect_dyna_controller()
        )
        self.dart.state.ui.com_port_combobox.pack(side="left", padx=5, pady=5)

        # Refresh button
        self.dart.state.ui.serial_refresh = ctk.CTkButton(
            serial_frame, 
            width=28, 
            text="", 
            image=self.dart.state.get_icon('refresh'),
            command=self.dart.update_serial_ports_dropdown
        )
        self.dart.state.ui.serial_refresh.pack(side="left", padx=5, pady=5)

        # Torque checkbox
        self.dart.state.ui.torque_checkbox = ctk.CTkCheckBox(
            self.motor_frame,
            text="Torque",
            variable=self.dart.state.flags['torque'],
            command=self.dart.set_torque,
            onvalue=True,
            offvalue=False
        )
        self.dart.state.ui.torque_checkbox.pack(side="top", pady=10, expand=False)

        # Motor control frame
        control_frame = ctk.CTkFrame(self.motor_frame, height=2000, fg_color=TRANSPARENT)
        control_frame.pack(side="top", padx=10, pady=10)

        # Pan control
        pan_frame = ctk.CTkFrame(control_frame, width=80, height=500, fg_color=TRANSPARENT)
        pan_frame.grid(row=0, column=0, padx=0, pady=0)
        pan_frame.pack_propagate(False)

        self.dart.state.ui.pan_label = ctk.CTkLabel(
            pan_frame, 
            text="Pan: 0.0°", 
            font=GLOBAL_FONT, 
            padx=5, 
            pady=5
        )
        self.dart.state.ui.pan_label.pack()

        self.dart.state.ui.pan_slider = ctk.CTkSlider(
            pan_frame,
            from_=-45,
            to=45,
            command=self.dart.set_pan,
            orientation="vertical",
            height=500
        )
        self.dart.state.ui.pan_slider.set(self.dart.state.motor['pan_value'])
        self.dart.state.ui.pan_slider.pack(padx=5, pady=5)

        # Tilt control
        tilt_frame = ctk.CTkFrame(control_frame, width=80, height=500, fg_color=TRANSPARENT)
        tilt_frame.grid(row=0, column=1, padx=0, pady=0)
        tilt_frame.pack_propagate(False)

        self.dart.state.ui.tilt_label = ctk.CTkLabel(
            tilt_frame,
            text="Tilt: 0.0°",
            font=GLOBAL_FONT,
            padx=5,
            pady=5
        )
        self.dart.state.ui.tilt_label.pack()

        self.dart.state.ui.tilt_slider = ctk.CTkSlider(
            tilt_frame,
            from_=-45,
            to=45,
            command=self.dart.set_tilt,
            orientation="vertical",
            height=500
        )
        self.dart.state.ui.tilt_slider.set(self.dart.state.motor['tilt_value'])
        self.dart.state.ui.tilt_slider.pack(padx=5, pady=5)

        # Calibrate frame
        self.dart.state.ui.calibrate_frame = ctk.CTkFrame(
            self.motor_frame, 
            fg_color=TRANSPARENT
        )
        self.dart.state.ui.calibrate_frame.pack(side="top", padx=10, pady=10)

        # Calibration button
        self.dart.state.ui.calibration_button = ctk.CTkButton(
            self.dart.state.ui.calibrate_frame,
            width=80,
            text="Calibrate",
            command=self.dart.calibrate,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.calibration_button.pack(side="left", padx=10, pady=10)

        # Center button
        self.dart.state.ui.centre_button = ctk.CTkButton(
            self.dart.state.ui.calibrate_frame,
            width=40,
            text="",
            image=self.dart.state.get_icon('qtm_stream'),
            command=self.dart.centre,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.centre_button.pack(side="left", padx=10, pady=10)

    def setup_mocap_frame(self):
        """Set up motion capture frame"""
        self.mocap_frame = ctk.CTkFrame(self)
        self.mocap_frame.configure(fg_color=FRAME_COLOR)
        self.mocap_frame.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # MoCap connect button
        self.dart.state.ui.mocap_button = ctk.CTkButton(
            self.mocap_frame,
            width=80,
            text="MoCap",
            image=self.dart.state.get_icon('sync'),
            command=self.dart.mocap_button_press,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.mocap_button.pack(side="top", pady=10)

        # Crosshair checkbox
        self.dart.state.ui.crosshair_checkbox = ctk.CTkCheckBox(
            self.mocap_frame,
            text="Crosshair",
            variable=self.dart.state.flags['crosshair'],
            command=lambda: setattr(
                self.dart.image_pro,
                'show_crosshair',
                self.dart.state.flags['crosshair'].get()
            ),
            onvalue=True,
            offvalue=False,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.crosshair_checkbox.pack(side="top", pady=10, expand=True)

        # Marker count display
        num_marker_frame = ctk.CTkFrame(self.mocap_frame, fg_color=TRANSPARENT)
        num_marker_frame.pack(side="top", padx=10, pady=10, expand=True)
        
        self.dart.state.ui.num_marker_label = ctk.CTkLabel(
            num_marker_frame,
            text="No. Markers: 0",
            font=GLOBAL_FONT
        )
        self.dart.state.ui.num_marker_label.pack(padx=5, pady=5)

    def setup_track_frame(self):
        """Set up tracking controls"""
        self.track_frame = ctk.CTkFrame(self)
        self.track_frame.configure(fg_color=FRAME_COLOR)
        self.track_frame.grid(row=2, column=2, sticky="nsew", padx=5, pady=5)

        # Track button
        self.dart.state.ui.track_button = ctk.CTkButton(
            self.track_frame,
            text="Track",
            command=self.dart.track,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.track_button.pack(side="top", padx=10, pady=10, anchor="center", expand=True)

    def setup_camera_frame(self):
        """Set up camera controls"""
        self.camera_frame = ctk.CTkFrame(self)
        self.camera_frame.configure(fg_color=FRAME_COLOR)
        self.camera_frame.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)

        # Camera selection frame
        cam_frame = ctk.CTkFrame(self.camera_frame, fg_color=TRANSPARENT)
        cam_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True)

        # Camera selection dropdown
        self.dart.state.ui.cam_combobox = ctk.CTkComboBox(
            cam_frame,
            width=100,
            values=[],
            variable=self.dart.state.hardware.selected_camera,
            command=self.dart.connect_camera
        )
        self.dart.state.ui.cam_combobox.pack(side="left", padx=5, pady=5)

        # Camera refresh button
        self.dart.state.ui.cam_refresh = ctk.CTkButton(
            cam_frame,
            width=28,
            text="",
            image=self.dart.state.get_icon('refresh'),
            command=self.dart.update_camera_dropdown,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.cam_refresh.pack(side="left", padx=5, pady=5)

        # Video toggle button
        self.dart.state.ui.toggle_video_button = ctk.CTkButton(
            self.camera_frame,
            width=80,
            text="Start",
            image=self.dart.state.get_icon('play'),
            command=self.dart.toggle_video_feed,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.toggle_video_button.pack(side="left", padx=10, anchor="center", expand=True)

        # Exposure control
        exposure_frame = ctk.CTkFrame(self.camera_frame, fg_color=TRANSPARENT)
        exposure_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True, fill="x")
        
        self.dart.state.ui.exposure_slider = ctk.CTkSlider(
            exposure_frame,
            width=140,
            from_=4,
            to=4000,
            command=self.dart.adjust_exposure
        )
        self.dart.state.ui.exposure_slider.set(1000)
        self.dart.state.ui.exposure_slider.pack(padx=5, pady=5, expand=True, fill="x")
        
        self.dart.state.ui.exposure_label = ctk.CTkLabel(
            exposure_frame,
            text="Exposure (us): 1000",
            font=GLOBAL_FONT
        )
        self.dart.state.ui.exposure_label.pack()

        # Gain control
        gain_frame = ctk.CTkFrame(self.camera_frame, fg_color=TRANSPARENT)
        gain_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True, fill="x")
        
        self.dart.state.ui.gain_slider = ctk.CTkSlider(
            gain_frame,
            width=140,
            from_=0,
            to=47,
            command=self.dart.adjust_gain
        )
        self.dart.state.ui.gain_slider.set(10)
        self.dart.state.ui.gain_slider.pack(padx=5, pady=5, expand=True, fill="x")
        
        self.dart.state.ui.gain_label = ctk.CTkLabel(
            gain_frame,
            text="Gain (dB): 10",
            font=GLOBAL_FONT
        )
        self.dart.state.ui.gain_label.pack()

        # Recording controls
        video_path_frame = ctk.CTkFrame(self.camera_frame, fg_color=TRANSPARENT)
        video_path_frame.pack(side="left", padx=10, pady=10, anchor="center", expand=True)

        # Folder selection button
        self.dart.state.ui.file_button = ctk.CTkButton(
            video_path_frame,
            width=28,
            text="",
            image=self.dart.state.get_icon('folder'),
            command=self.dart.select_folder,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.file_button.pack(side="left", padx=5, pady=5)

        # Filename entry
        self.dart.state.ui.file_name_entry = ctk.CTkEntry(
            video_path_frame,
            width=120,
            placeholder_text="Enter file name",
            font=GLOBAL_FONT
        )
        self.dart.state.ui.file_name_entry.pack(side="left", padx=5, pady=5)

        # Record button
        self.dart.state.ui.record_button = ctk.CTkButton(
            self.camera_frame,
            width=90,
            text="Record",
            image=self.dart.state.get_icon('record'),
            command=self.dart.toggle_record,
            font=GLOBAL_FONT
        )
        self.dart.state.ui.record_button.pack(side="left", padx=10, anchor="center", expand=True)

        # Pause button
        self.dart.state.ui.pause_button = ctk.CTkButton(
            self.camera_frame,
            width=100,
            text="Pause",
            image=self.dart.state.get_icon('pause'),
            command=self.dart.toggle_pause,
            state="disabled",
            font=GLOBAL_FONT
        )
        self.dart.state.ui.pause_button.pack(side="left", padx=10, anchor="center", expand=True)

        # FPS display
        fps_frame = ctk.CTkFrame(self.camera_frame, fg_color=TRANSPARENT)
        fps_frame.pack(side="right", padx=10, pady=10, anchor="e", expand=True)
        
        self.dart.state.ui.fps_label = ctk.CTkLabel(
            fps_frame,
            text=f"FPS: {round(self.dart.camera_manager.fps, 2)}",
            font=GLOBAL_FONT
        )
        self.dart.state.ui.fps_label.pack(padx=5, pady=5)