from CTkMenuBar import *
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import os
import tkinter as tk
from typing import Callable

class MenuBar:
    def __init__(self, parent: ctk.CTk, dart_instance, track_callback: Callable, 
                 exit_callback: Callable, lens_control_callback: Callable):
        """Initialize the menu bar with callbacks for actions"""
        self.parent = parent
        self.dart = dart_instance
        self.track_callback = track_callback
        self.exit_callback = exit_callback
        self.lens_control_callback = lens_control_callback
        
        self.setup_menu()
        
    def detect_devices_callback(self):
        """Launch device detection wizard"""
        from ui.views.device_detection_wizard import DeviceDetectionWizard
        wizard = DeviceDetectionWizard(self.parent, self.dart.device_manager)
        wizard.grab_set()  # Make window modal
    
    def setup_menu(self):
        """Set up the menu bar and its items"""
        if os.name == "nt":  # Windows
            # Create the CTk menu bar
            self.title_menu = CTkTitleMenu(self.parent)
            
            # File menu
            file_menu = self.title_menu.add_cascade(text="File")
            file_dropdown = CustomDropdownMenu(widget=file_menu)
            file_dropdown.add_option(option="Track", command=self.track_callback)
            file_dropdown.add_separator()
            file_dropdown.add_option(option="Exit", command=self.exit_callback)

            # Tools menu
            tools_menu = self.title_menu.add_cascade(text="Tools")
            tools_dropdown = CustomDropdownMenu(widget=tools_menu)
            tools_dropdown.add_option(option="Detect Device", 
                                    command=self.detect_devices_callback)
            tools_dropdown.add_option(option="Lens Control", 
                                    command=self.lens_control_callback)
        else:  # macOS and Linux
            # Create native tkinter menubar
            self.menubar = tk.Menu(self.parent)
            self.parent.configure(menu=self.menubar)
            
            # File menu
            file_menu = tk.Menu(self.menubar, tearoff=0)
            self.menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Track", command=self.track_callback)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.exit_callback)
            
            # Tools menu
            tools_menu = tk.Menu(self.menubar, tearoff=0)
            self.menubar.add_cascade(label="Tools", menu=tools_menu)
            tools_menu.add_command(label="Detect Device", 
                                 command=self.detect_devices_callback)
            tools_menu.add_command(label="Lens Control", 
                                 command=self.lens_control_callback)