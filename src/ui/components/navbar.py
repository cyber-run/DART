import customtkinter as ctk
from typing import Callable

class Navbar(ctk.CTkFrame):
    def __init__(self, parent, state_manager, switch_view_callback: Callable):
        super().__init__(
            parent, 
            width=50, 
            corner_radius=0, 
            border_width=-2, 
            border_color="#1c1c1c"
        )
        
        self.state = state_manager
        self.switch_view = switch_view_callback
        self.fg_color1 = self.cget("fg_color")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize navbar UI elements"""
        self.home_button = ctk.CTkButton(
            self,
            text="",
            image=self.state.get_icon('home'),
            height=40,
            width=40,
            corner_radius=5,
            fg_color="#27272a",
            hover_color="#1c1c1c",
            command=lambda: self.switch_view("track")
        )
        self.home_button.pack(side="top", padx=5, pady=5)

        self.data_button = ctk.CTkButton(
            self,
            text="",
            image=self.state.get_icon('data'),
            height=40,
            width=40,
            corner_radius=5,
            fg_color=self.fg_color1,
            hover_color="#1c1c1c",
            command=lambda: self.switch_view("data")
        )
        self.data_button.pack(side="top", padx=5, pady=5)
    
    def set_active_button(self, view: str):
        """Update button states based on active view"""
        if view == "track":
            self.home_button.configure(fg_color="#27272a")
            self.data_button.configure(fg_color=self.fg_color1)
        else:
            self.data_button.configure(fg_color="#27272a")
            self.home_button.configure(fg_color=self.fg_color1) 