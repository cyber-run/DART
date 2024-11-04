import customtkinter as ctk

class BaseView(ctk.CTkFrame):
    """Base class for all views"""
    def __init__(self, parent, dart_instance):
        super().__init__(parent)
        self.dart = dart_instance
        self.configure(fg_color="#151518")  # Darker background for main view
        self.setup_ui()
    
    def setup_ui(self):
        """To be implemented by child classes"""
        raise NotImplementedError
        
    def cleanup(self):
        """Cleanup resources when view is closed"""
        pass 