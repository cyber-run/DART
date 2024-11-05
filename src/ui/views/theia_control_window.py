import customtkinter as ctk
import logging
from typing import Optional
import CTkMessagebox

GLOBAL_FONT = ("default_theme", 14)
BG_COLOR = "#151518"        # Darker background for main view
FRAME_COLOR = "#09090b"     # Slightly lighter for control containers
TRANSPARENT = "transparent"  # For nested frames that should inherit parent color

class TheiaLensControlWindow(ctk.CTkToplevel):
    def __init__(self, master, dart_instance):
        super().__init__(master)
        self.title("Theia Lens Control")
        self.geometry("600x800")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)

        self.dart = dart_instance
        self.theia = self.dart.theia

        # Check Theia connection status
        if not self.theia or not hasattr(self.theia, 'ser') or not self.theia.ser.is_open:
            logging.error("Theia controller not properly initialized")
            CTkMessagebox(
                title="Error",
                message="Theia controller not connected. Please check hardware connection.",
                icon="cancel"
            )
            self.destroy()
            return

        # Get stored positions from config
        theia_state = self.dart.config.config["devices"]["theia_state"]
        self.current_zoom = theia_state["zoom_position"]
        self.current_focus = theia_state["focus_position"]

        self.setup_ui()
        
        # Set sliders to current positions
        self.zoom_slider.set(self.current_zoom * 100 / 50000)  # Convert steps to percentage
        self.focus_slider.set(self.current_focus * 100 / 133000)
        
        # Update labels
        self.update_position_display()
        self.status_label.configure(
            text=f"Lens Controller Connected",
            text_color="green"
        )
        
    def setup_ui(self):
        """Initialize the UI elements"""
        # Main container
        self.main_frame = ctk.CTkFrame(self, fg_color=TRANSPARENT)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Status section
        self.setup_status_section()
        
        # Controls section
        self.setup_controls_section()
        
        # Home controls section
        self.setup_home_section()

    def setup_status_section(self):
        """Setup the status display section"""
        status_frame = ctk.CTkFrame(self.main_frame, fg_color=FRAME_COLOR)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        # Connection status
        self.status_label = ctk.CTkLabel(
            status_frame,
            text=f"Lens Controller Status",
            font=(GLOBAL_FONT[0], 16, "bold")
        )
        self.status_label.pack(pady=5)
        
        # Port info
        port_label = ctk.CTkLabel(
            status_frame,
            text=f"Port: {self.dart.config.config['devices']['theia_port']}",
            font=GLOBAL_FONT
        )
        port_label.pack(pady=5)
        
        # Current position display
        self.position_label = ctk.CTkLabel(
            status_frame,
            text="Current Position - Zoom: 0%, Focus: 0%",
            font=GLOBAL_FONT
        )
        self.position_label.pack(pady=5)

    def setup_controls_section(self):
        """Setup the lens control section"""
        controls_frame = ctk.CTkFrame(self.main_frame, fg_color=FRAME_COLOR)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        # Zoom controls
        zoom_frame = ctk.CTkFrame(controls_frame, fg_color=TRANSPARENT)
        zoom_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(zoom_frame, text="Zoom Control", font=(GLOBAL_FONT[0], 14, "bold")).pack()
        
        self.zoom_slider = ctk.CTkSlider(
            zoom_frame,
            from_=0,
            to=100,
            command=self.set_zoom,
            number_of_steps=100
        )
        self.zoom_slider.pack(fill="x", padx=20, pady=5)
        
        self.zoom_label = ctk.CTkLabel(zoom_frame, text="Zoom: 0%", font=GLOBAL_FONT)
        self.zoom_label.pack(pady=5)
        
        # Focus controls
        focus_frame = ctk.CTkFrame(controls_frame, fg_color=TRANSPARENT)
        focus_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(focus_frame, text="Focus Control", font=(GLOBAL_FONT[0], 14, "bold")).pack()
        
        self.focus_slider = ctk.CTkSlider(
            focus_frame,
            from_=0,
            to=100,
            command=self.set_focus,
            number_of_steps=100
        )
        self.focus_slider.pack(fill="x", padx=20, pady=5)
        
        self.focus_label = ctk.CTkLabel(focus_frame, text="Focus: 0%", font=GLOBAL_FONT)
        self.focus_label.pack(pady=5)

    def setup_home_section(self):
        """Setup the homing controls section"""
        home_frame = ctk.CTkFrame(self.main_frame, fg_color=FRAME_COLOR)
        home_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            home_frame, 
            text="Homing Controls", 
            font=(GLOBAL_FONT[0], 14, "bold")
        ).pack(pady=10)
        
        button_frame = ctk.CTkFrame(home_frame, fg_color=TRANSPARENT)
        button_frame.pack(pady=10)
        
        self.home_zoom_button = ctk.CTkButton(
            button_frame,
            text="Home Zoom",
            command=self.home_zoom,
            width=120,
            font=GLOBAL_FONT
        )
        self.home_zoom_button.pack(side="left", padx=10)
        
        self.home_focus_button = ctk.CTkButton(
            button_frame,
            text="Home Focus",
            command=self.home_focus,
            width=120,
            font=GLOBAL_FONT
        )
        self.home_focus_button.pack(side="left", padx=10)

    def update_position_display(self):
        """Update the position display"""
        self.position_label.configure(
            text=f"Current Position - Zoom: {self.current_zoom}%, Focus: {self.current_focus}%"
        )

    def set_zoom(self, value: float):
        """Set zoom position"""
        try:
            if self.theia and self.theia.ser.is_open:
                new_zoom = int(value * 50000 / 100)  # Scale to motor steps
                steps = new_zoom - self.current_zoom  # Calculate relative movement
                if steps != 0:  # Only move if position changed
                    self.theia.move_axis("A", steps)
                    self.current_zoom = new_zoom
                    self.dart.config.update_theia_position(zoom=self.current_zoom)
                    self.zoom_label.configure(text=f"Zoom: {int(value)}%")
                    self.update_position_display()
            else:
                self.status_label.configure(text="Error: Lens controller not connected")
        except Exception as e:
            logging.error(f"Error setting zoom: {e}")
            self.status_label.configure(text="Error setting zoom")

    def set_focus(self, value: float):
        """Set focus position"""
        try:
            if self.theia and self.theia.ser.is_open:
                new_focus = int(value * 133000 / 100)  # Scale to motor steps
                steps = new_focus - self.current_focus  # Calculate relative movement
                if steps != 0:  # Only move if position changed
                    self.theia.move_axis("B", steps)
                    self.current_focus = new_focus
                    self.dart.config.update_theia_position(focus=self.current_focus)
                    self.focus_label.configure(text=f"Focus: {int(value)}%")
                    self.update_position_display()
            else:
                self.status_label.configure(text="Error: Lens controller not connected")
        except Exception as e:
            logging.error(f"Error setting focus: {e}")
            self.status_label.configure(text="Error setting focus")

    def home_zoom(self):
        """Home zoom axis"""
        try:
            if self.theia and self.theia.ser.is_open:
                self.home_zoom_button.configure(state="disabled")
                self.status_label.configure(text="Homing zoom axis...")
                self.theia.home_zoom()
                self.zoom_slider.set(0)
                self.current_zoom = 0
                self.zoom_label.configure(text="Zoom: 0%")
                self.update_position_display()
                self.status_label.configure(text="Zoom axis homed successfully")
                self.home_zoom_button.configure(state="normal")
            else:
                self.status_label.configure(text="Error: Lens controller not connected")
        except Exception as e:
            logging.error(f"Error homing zoom: {e}")
            self.status_label.configure(text="Error homing zoom")
            self.home_zoom_button.configure(state="normal")

    def home_focus(self):
        """Home focus axis"""
        try:
            if self.theia and self.theia.ser.is_open:
                self.home_focus_button.configure(state="disabled")
                self.status_label.configure(text="Homing focus axis...")
                self.theia.home_focus()
                self.focus_slider.set(0)
                self.current_focus = 0
                self.focus_label.configure(text="Focus: 0%")
                self.update_position_display()
                self.status_label.configure(text="Focus axis homed successfully")
                self.home_focus_button.configure(state="normal")
            else:
                self.status_label.configure(text="Error: Lens controller not connected")
        except Exception as e:
            logging.error(f"Error homing focus: {e}")
            self.status_label.configure(text="Error homing focus")
            self.home_focus_button.configure(state="normal")