from ui.views.base_view import BaseView
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

GLOBAL_FONT = ("default_theme", 14)
BG_COLOR = "#151518"        # Darker background for main view
FRAME_COLOR = "#09090b"     # Slightly lighter for control containers
TRANSPARENT = "transparent"  # For nested frames that should inherit parent color

class DashboardView(BaseView):
    def __init__(self, parent, dart_instance):
        super().__init__(parent, dart_instance)
        self.configure(fg_color=BG_COLOR)
    
    def setup_ui(self):
        """Initialize dashboard view UI"""
        # Configure the grid
        self.grid_columnconfigure(1, weight=1)  # Video preview
        self.grid_columnconfigure(2, weight=1)  # Plots
        
        self.setup_video_preview()
        self.setup_plots()
    
    def setup_video_preview(self):
        """Set up video preview"""
        # Video preview frame
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.configure(fg_color=FRAME_COLOR)
        self.preview_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)

        # Video label
        self.dart.state.ui.video_label2 = ctk.CTkLabel(
            self.preview_frame, 
            text=""
        )
        self.dart.state.ui.video_label2.pack(expand=True, padx=5, pady=5)
        self.dart.state.ui.video_label2.configure(
            image=self.dart.state.get_icon('small_placeholder')
        )
    
    def setup_plots(self):
        """Set up data plots"""
        # Main plots frame
        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.configure(fg_color=FRAME_COLOR)
        self.plot_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Use dark background style
        plt.style.use('dark_background')

        # Create sample data
        trajectory_data = np.random.rand(50)
        angle_data = np.random.rand(50)

        # Trajectory plot frame
        trajectory_frame = ctk.CTkFrame(self.plot_frame, fg_color=TRANSPARENT)
        trajectory_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        
        trajectory_label = ctk.CTkLabel(
            trajectory_frame,
            text="Trajectory",
            font=GLOBAL_FONT
        )
        trajectory_label.pack(pady=(0, 5))
        
        self.setup_trajectory_plot(trajectory_frame, trajectory_data)

        # Angle plot frame
        angle_frame = ctk.CTkFrame(self.plot_frame, fg_color=TRANSPARENT)
        angle_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        
        angle_label = ctk.CTkLabel(
            angle_frame,
            text="Angles",
            font=GLOBAL_FONT
        )
        angle_label.pack(pady=(0, 5))
        
        self.setup_angle_plot(angle_frame, angle_data)

    def setup_trajectory_plot(self, parent, data):
        """Set up trajectory plot"""
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(data)
        fig.set_facecolor("none")
        ax.set_facecolor("#09090b")
        
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.get_tk_widget().configure(bg="#09090b")
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def setup_angle_plot(self, parent, data):
        """Set up angle plot"""
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(data)
        fig.set_facecolor("none")
        ax.set_facecolor("#09090b")
        
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.get_tk_widget().configure(bg="#09090b")
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def cleanup(self):
        """Cleanup matplotlib resources"""
        plt.close('all')