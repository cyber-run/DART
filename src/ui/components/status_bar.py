import customtkinter as ctk
import logging

class StatusBar(ctk.CTkFrame):
    def __init__(self, parent, state_manager, calibrator):
        super().__init__(
            parent,
            height=4,
            corner_radius=0,
            border_width=-2,
            border_color="#1c1c1c"
        )
        
        self.state = state_manager
        self.calibrator = calibrator
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize status bar UI elements"""
        # Status label
        self.state.ui.status_label = ctk.CTkLabel(
            self,
            text=self.state.status['app_status'],
            height=18,
            font=("default_theme", 14)
        )
        self.state.ui.status_label.pack(side="left", padx=10, pady=0, anchor="center")

        # Camera status
        self.state.ui.camera_status = ctk.CTkLabel(
            self,
            text="Camera: Ready",
            font=("default_theme", 14),
            height=18
        )
        self.state.ui.camera_status.pack(side="left", padx=10)

        # Mocap status
        self.state.ui.mocap_status = ctk.CTkLabel(
            self,
            text="Mocap: Ready",
            font=("default_theme", 14),
            height=18
        )
        self.state.ui.mocap_status.pack(side="left", padx=10)

        # Motors status
        self.state.ui.motors_status = ctk.CTkLabel(
            self,
            text="Motors: Ready",
            font=("default_theme", 14),
            height=18
        )
        self.state.ui.motors_status.pack(side="left", padx=10)

        # Calibration age
        self.state.ui.age_label = ctk.CTkLabel(
            self,
            text=f"Calibration age: {int(self.calibrator.calibration_age)} h",
            height=18,
            font=("default_theme", 14)
        )
        self.state.ui.age_label.pack(side="left", padx=10, pady=0, anchor="e", expand=True)

        # Memory usage
        self.state.ui.memory_label = ctk.CTkLabel(
            self,
            text=f"Memory usage: {self.state.status['memory_usage']}%",
            height=18,
            font=("default_theme", 14)
        )
        self.state.ui.memory_label.pack(side="right", padx=10, pady=0, anchor="e", expand=False) 

    def cleanup(self):
        """Safely cleanup status bar"""
        try:
            # Remove references to labels before destroying
            self.state.ui.status_label = None
            self.state.ui.camera_status = None
            self.state.ui.mocap_status = None
            self.state.ui.motors_status = None
            self.state.ui.memory_label = None
            self.state.ui.age_label = None
            
            # Destroy frame
            self.destroy()
        except Exception as e:
            logging.debug(f"Error cleaning up status bar: {e}")