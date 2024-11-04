from ui.views.track_view import TrackView
from ui.views.dashboard_view import DashboardView
from ui.components.navbar import Navbar
from ui.components.status_bar import StatusBar
from ui.components.menu_bar import MenuBar
from hardware.motion.theia_controller import TheiaController
from ui.views.theia_control_window import TheiaLensControlWindow

class DARTGUI:
    def __init__(self, window, dart_instance):
        self.window = window
        self.dart = dart_instance
        self.views = {}

        # Set up persistent GUI elements
        self.setup_layout()
        self.setup_menu()
        
        # Create initial view
        self.create_view("track")  # Create initial view
        self.switch_view("track")  # Switch to initial view

    def create_view(self, view_name: str) -> None:
        """Create a new view if it doesn't exist"""
        if view_name not in self.views:
            if view_name == "track":
                self.views[view_name] = TrackView(self.window, self.dart)
            elif view_name == "data":
                self.views[view_name] = DashboardView(self.window, self.dart)

    def switch_view(self, view_name: str):
        """Switch between views"""
        # Create the new view if it doesn't exist
        self.create_view(view_name)
        
        # Hide current view if exists
        current_view = self.dart.state.get_current_view()
        if current_view in self.views:
            self.views[current_view].grid_remove()
        
        # Show new view
        self.views[view_name].grid(row=0, column=1, columnspan=2, sticky="nsew")
        self.dart.state.set_current_view(view_name)
        self.navbar.set_active_button(view_name)

    def setup_layout(self):
        """Set up main layout and persistent components"""
        # Configure grid
        self.window.grid_columnconfigure(0, weight=0)  # Navbar column
        self.window.grid_columnconfigure(1, weight=1)  # Main content
        self.window.grid_columnconfigure(2, weight=0)  # Right panel
        self.window.grid_rowconfigure(0, weight=1)     # Main content
        
        # Add navbar
        self.navbar = Navbar(
            self.window, 
            self.dart.state,
            self.switch_view
        )
        self.navbar.grid(row=0, column=0, rowspan=5, sticky="nsw", padx=(0,5))
        
        # Add status bar
        self.status_bar = StatusBar(
            self.window,
            self.dart.state,
            self.dart.calibrator
        )
        self.status_bar.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(5,0))

    def setup_menu(self):
        """Set up the menu bar"""
        self.menu_bar = MenuBar(
            parent=self.window,
            track_callback=self.dart.track,
            exit_callback=self.dart.on_closing,
            lens_control_callback=self.open_theia_control_window
        )

    def open_theia_control_window(self):
        """Open the Theia lens control window"""
        if not hasattr(self, 'theia_controller'):
            self.theia_controller = TheiaController(port="COM17")
        
        self.theia_window = TheiaLensControlWindow(self.window, self.theia_controller)
        self.theia_window.grab_set()

    def cleanup_resources(self):
        """Clean up resources before closing"""
        for view in self.views.values():
            view.cleanup()
        
        for widget in self.window.winfo_children():
            widget.destroy()