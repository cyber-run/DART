import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import time
import threading
from typing import Callable

class DeviceDetectionWizard(ctk.CTkToplevel):
    def __init__(self, parent, device_manager):
        super().__init__(parent)
        
        # Window setup
        self.title("DART Device Detection")
        self.geometry("400x300")
        self.resizable(False, False)
        
        # Store references
        self.device_manager = device_manager
        
        # Initialize UI elements
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        self.message_label = ctk.CTkLabel(
            self.content_frame,
            text="Please disconnect the DART device\nbefore proceeding.",
            font=("default_theme", 14),
            wraplength=350
        )
        self.message_label.pack(pady=20)
        
        self.progress_bar = ctk.CTkProgressBar(self.content_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=20)
        self.progress_bar.pack_forget()  # Hide initially
        
        self.proceed_button = ctk.CTkButton(
            self.content_frame,
            text="Proceed",
            command=self.start_detection
        )
        self.proceed_button.pack(pady=20)
        
        # Detection state
        self.detection_state = "start"  # start -> scanning -> complete
        
    def start_detection(self):
        """Handle the detection process flow"""
        if self.detection_state == "start":
            # Take initial snapshot
            self.device_manager.get_initial_state()
            
            # Update UI for connection step
            self.message_label.configure(
                text="Please connect the DART device now.\n\n"
                "Ensure both cameras and motor controllers\n"
                "are properly connected."
            )
            self.detection_state = "scanning"
            
        elif self.detection_state == "scanning":
            # Update UI for detection process
            self.message_label.configure(text="Detecting DART device...")
            self.proceed_button.pack_forget()
            self.progress_bar.pack(pady=20)
            
            # Start detection in separate thread
            threading.Thread(target=self.run_detection, daemon=True).start()
    
    def run_detection(self):
        """Run the device detection process"""
        # Update message to show we're checking for devices
        self.message_label.configure(text="Checking for FLIR cameras...")
        self.progress_bar.set(0.3)
        
        # Attempt device detection
        success, message = self.device_manager.detect_devices()
        
        if not success:
            self.progress_bar.set(1.0)
            CTkMessagebox(
                title="Error",
                message=f"Device detection failed:\n{message}\n\nPlease ensure:\n"
                "1. Both FLIR cameras are connected\n"
                "2. Both motor controllers are connected\n"
                "3. All USB connections are secure",
                icon="cancel"
            )
            # Reset UI for retry
            self.progress_bar.pack_forget()
            self.proceed_button.pack(pady=20)
            self.message_label.configure(
                text="Detection failed. Please ensure all devices\n"
                "are properly connected and try again."
            )
            self.detection_state = "start"
        else:
            self.progress_bar.set(1.0)
            CTkMessagebox(
                title="Success",
                message="DART device detected and configured successfully!\n\n"
                f"Found:\n"
                f"• 2 FLIR cameras\n"
                f"• Dynamixel controller on {self.device_manager.config['dynamixel_port']}\n"
                f"• Theia controller on {self.device_manager.config['theia_port']}",
                icon="check"
            )
            self.destroy()