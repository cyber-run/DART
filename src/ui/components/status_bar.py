import customtkinter as ctk

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
            text="Camera: -",
            font=("default_theme", 14),
            height=18
        )
        self.state.ui.camera_status.pack(side="left", padx=10)

        # Mocap status
        self.state.ui.mocap_status = ctk.CTkLabel(
            self,
            text="Mocap: -",
            font=("default_theme", 14),
            height=18
        )
        self.state.ui.mocap_status.pack(side="left", padx=10)

        # Motors status
        self.state.ui.motors_status = ctk.CTkLabel(
            self,
            text="Motors: -",
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