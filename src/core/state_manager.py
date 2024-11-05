from dataclasses import dataclass, field
import tkinter as tk
import customtkinter as ctk
from PIL import Image
import os
from typing import Optional, Any, List
from multiprocessing import Process, Queue, Event
import logging

@dataclass
class HardwareState:
    """Manages hardware connection states"""
    cameras: List[str] = field(default_factory=list)
    dynamixel_port: Optional[str] = None
    theia_port: Optional[str] = None
    qtm_stream: Any = None
    dyna: Any = None

@dataclass
class RecordingState:
    """Manages recording-related states"""
    is_live: bool = False
    video_path: str = "static/recordings"
    file_name: Optional[str] = None
    record_start_ms: Optional[float] = None
    data_handler: Any = None

@dataclass
class UIState:
    """Manages UI-related states and elements"""
    status_bar: Optional[Any] = None
    status_label: Optional[Any] = None
    memory_label: Optional[Any] = None
    camera_status: Optional[Any] = None
    mocap_status: Optional[Any] = None
    motors_status: Optional[Any] = None
    age_label: Optional[Any] = None
    
    # Control elements
    com_port_combobox: Optional[Any] = None
    cam_combobox: Optional[Any] = None
    pan_label: Optional[Any] = None
    tilt_label: Optional[Any] = None
    pan_slider: Optional[Any] = None
    tilt_slider: Optional[Any] = None
    gain_label: Optional[Any] = None
    exposure_label: Optional[Any] = None
    fps_label: Optional[Any] = None
    file_name_entry: Optional[Any] = None
    
    # Buttons
    record_button: Optional[Any] = None
    pause_button: Optional[Any] = None
    track_button: Optional[Any] = None
    toggle_video_button: Optional[Any] = None
    
    # Additional UI elements
    serial_refresh: Optional[Any] = None
    cam_refresh: Optional[Any] = None
    exposure_slider: Optional[Any] = None
    gain_slider: Optional[Any] = None
    threshold_label: Optional[Any] = None
    strength_label: Optional[Any] = None
    num_marker_label: Optional[Any] = None
    calibration_button: Optional[Any] = None
    centre_button: Optional[Any] = None
    crosshair_checkbox: Optional[Any] = None
    torque_checkbox: Optional[Any] = None
    file_button: Optional[Any] = None
    mocap_button: Optional[Any] = None
    calibrate_frame: Optional[Any] = None
    video_label: Optional[Any] = None
    video_label2: Optional[Any] = None

class DARTState:
    def __init__(self):
        logging.basicConfig(level=logging.ERROR)
        # Initialize state containers
        self.hardware = HardwareState(
            cameras=[],
            dynamixel_port=None,
            theia_port=None
        )
        
        self.recording = RecordingState()
        
        # GUI flags
        self.flags = {
            'torque': tk.BooleanVar(value=False),
            'crosshair': tk.BooleanVar(value=False),
            'threshold': tk.BooleanVar(value=False),
            'detect': tk.BooleanVar(value=False)
        }
        
        # Motor control states
        self.motor = {
            'pan_value': 0,
            'tilt_value': 0
        }
        
        # Process tracking
        self.tracking = {
            'process': None,
            'terminate_event': None,
            'data_queue': None
        }
        
        # Application status
        self.status = {
            'app_status': "Idle",
            'memory_usage': None
        }
        
        # Load GUI icons
        self.icons = self.load_icons()
        
        # Add UI state
        self.ui = UIState()
        
        # Add view state
        self.view = {
            'current': "track",  # Default view
            'available': ["track", "data"]
        }
    
    def load_icons(self) -> dict:
        """Load all GUI icons and images"""
        icon_specs = {
            'refresh': ("refresh.png", (20, 20)),
            'sync': ("sync.png", (20, 20)),
            'play': ("play.png", (20, 20)),
            'stop': ("stop.png", (20, 20)),
            'folder': ("folder.png", (20, 20)),
            'record': ("record.png", (20, 20)),
            'qtm_stream': ("target.png", (20, 20)),
            'pause': ("pause.png", (20, 20)),
            'home': ("track.png", (30, 30)),
            'data': ("data.png", (30, 30))
        }
        
        icons = {}
        for name, (filename, size) in icon_specs.items():
            icons[name] = self._load_icon(filename, size)
            
        # Add placeholder images
        icons['placeholder'] = ctk.CTkImage(
            Image.new("RGB", (1200, 900), "black"), 
            size=(1200, 900)
        )
        icons['small_placeholder'] = ctk.CTkImage(
            Image.new("RGB", (300, 225), "black"), 
            size=(800, 600)
        )
        
        return icons
    
    def _load_icon(self, filename: str, size: tuple) -> ctk.CTkImage:
        """Helper method to load an icon file"""
        path = os.path.join("assets", "icons", filename)
        return ctk.CTkImage(Image.open(path), size=size)

    def start_tracking(self, data_queue: Queue, terminate_event) -> None:
        """Initialize tracking state"""
        self.tracking['data_queue'] = data_queue
        self.tracking['terminate_event'] = terminate_event
        
    def stop_tracking(self) -> None:
        """Clean up tracking state"""
        if self.tracking['terminate_event']:
            self.tracking['terminate_event'].set()
        if self.tracking['process']:
            self.tracking['process'].join()
            self.tracking['process'] = None

    def get_icon(self, icon_name: str) -> ctk.CTkImage:
        """Safely retrieve an icon from the state"""
        if icon_name not in self.icons:
            logging.warning(f"Icon {icon_name} not found, returning placeholder")
            return self.icons['placeholder']
        return self.icons[icon_name]

    def update_hardware_connection(self, device_type: str, device: Any) -> None:
        """Update hardware device connections"""
        if device_type == 'qtm':
            self.hardware.qtm_stream = device
        elif device_type == 'dyna':
            self.hardware.dyna = device
            
    def disconnect_hardware(self, device_type: str) -> None:
        """Safely disconnect hardware devices"""
        if device_type == 'qtm' and self.hardware.qtm_stream:
            self.hardware.qtm_stream._close()
            self.hardware.qtm_stream.close()
            self.hardware.qtm_stream = None
        elif device_type == 'dyna' and self.hardware.dyna:
            self.hardware.dyna.close_port()
            self.hardware.dyna = None

    def set_current_view(self, view_name: str) -> None:
        """Update current view"""
        if view_name in self.view['available']:
            self.view['current'] = view_name
        else:
            logging.error(f"Invalid view name: {view_name}")
    
    def get_current_view(self) -> str:
        """Get current view name"""
        return self.view['current']