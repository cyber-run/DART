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

        # Bind the closing event FIRST before any potential early returns
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Destroy>", self.on_destroy)
        logging.info("Window close protocol bound")

        # Make window modal
        self.grab_set()
        
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
        
        # Initialize current positions
        self.current_zoom = theia_state["zoom_position"]
        self.current_focus = theia_state["focus_position"]
        
        # Set the controller's absolute positions
        self.theia.set_absolute_position("A", self.current_zoom)
        self.theia.set_absolute_position("B", self.current_focus)

        self.setup_ui()
        
        # Set sliders to current positions
        self.zoom_slider.set(self.current_zoom)
        self.focus_slider.set(self.current_focus)
        
        # Update labels
        self.zoom_label.configure(text=f"Zoom: {self.current_zoom} steps")
        self.focus_label.configure(text=f"Focus: {self.current_focus} steps")

    def setup_ui(self):
        """Initialize the UI elements"""
        # Main container
        self.main_frame = ctk.CTkFrame(self, fg_color=TRANSPARENT)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Controls section
        self.setup_controls_section()
        
        # Home controls section
        self.setup_home_section()

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
            to=50000,
            command=self.set_zoom
        )
        self.zoom_slider.pack(fill="x", padx=20, pady=5)
        
        self.zoom_label = ctk.CTkLabel(zoom_frame, text="Zoom: 0 steps", font=GLOBAL_FONT)
        self.zoom_label.pack(pady=5)
        
        # Focus controls
        focus_frame = ctk.CTkFrame(controls_frame, fg_color=TRANSPARENT)
        focus_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(focus_frame, text="Focus Control", font=(GLOBAL_FONT[0], 14, "bold")).pack()
        
        self.focus_slider = ctk.CTkSlider(
            focus_frame,
            from_=0,
            to=65000,
            command=self.set_focus
        )
        self.focus_slider.pack(fill="x", padx=20, pady=5)
        
        self.focus_label = ctk.CTkLabel(focus_frame, text="Focus: 0 steps", font=GLOBAL_FONT)
        self.focus_label.pack(pady=5)

    def set_zoom(self, value: float):
        """Set zoom position"""
        try:
            if self.theia and self.theia.ser.is_open:
                new_zoom = int(value)  # Use steps directly
                self.theia.move_axis("A", new_zoom)  # Use absolute positioning
                self.current_zoom = new_zoom
                self.zoom_label.configure(text=f"Zoom: {new_zoom} steps")
        except Exception as e:
            logging.error(f"Error setting zoom: {e}")

    def set_focus(self, value: float):
        """Set focus position"""
        try:
            if self.theia and self.theia.ser.is_open:
                new_focus = int(value)  # Use steps directly
                self.theia.move_axis("B", new_focus)  # Use absolute positioning
                self.current_focus = new_focus
                self.focus_label.configure(text=f"Focus: {new_focus} steps")
        except Exception as e:
            logging.error(f"Error setting focus: {e}")

    def on_destroy(self, event):
        """Handle window destruction"""
        if event.widget == self:
            logging.info("Window destroy event triggered")
            # Call on_closing if it hasn't been called yet
            if hasattr(self, 'theia'):  # Check if window was properly initialized
                self.on_closing()
            self.grab_release()
            logging.info("Window grab released")

    def on_closing(self):
        """Save positions before closing"""
        logging.info("Theia control window closing...")
        try:
            if hasattr(self, '_closing_handled'):  # Prevent double execution
                return
            self._closing_handled = True
                
            if self.theia and self.theia.ser.is_open:
                logging.info('Getting current lens positions...')
                zoom_pos, focus_pos = self.theia.get_current_positions()
                logging.info(f'Current positions - Zoom: {zoom_pos}, Focus: {focus_pos}')
                
                if zoom_pos is not None and focus_pos is not None:
                    logging.info('Updating config with new positions...')
                    self.dart.config.update_theia_position(
                        zoom=zoom_pos,
                        focus=focus_pos
                    )
                    logging.info('Config updated successfully')
                else:
                    logging.warning('Could not get valid positions from controller')
        except Exception as e:
            logging.error(f"Error saving positions: {e}", exc_info=True)
        finally:
            logging.info("Destroying Theia control window")
            self.grab_release()
            self.destroy()

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

    def home_zoom(self):
        """Home zoom axis"""
        try:
            if self.theia and self.theia.ser.is_open:
                self.home_zoom_button.configure(state="disabled")
                self.theia.home_zoom()
                self.zoom_slider.set(0)
                self.current_zoom = 0
                self.zoom_label.configure(text=f"Zoom: 0 steps")
                self.home_zoom_button.configure(state="normal")
        except Exception as e:
            logging.error(f"Error homing zoom: {e}")
            self.home_zoom_button.configure(state="normal")

    def home_focus(self):
        """Home focus axis"""
        try:
            if self.theia and self.theia.ser.is_open:
                self.home_focus_button.configure(state="disabled")
                self.theia.home_focus()
                self.focus_slider.set(0)
                self.current_focus = 0
                self.focus_label.configure(text=f"Focus: 0 steps")
                self.home_focus_button.configure(state="normal")
        except Exception as e:
            logging.error(f"Error homing focus: {e}")
            self.home_focus_button.configure(state="normal")