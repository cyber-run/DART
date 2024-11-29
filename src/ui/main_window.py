from ui.views.track_view import TrackView
from ui.views.dashboard_view import DashboardView
from ui.components.navbar import Navbar
from ui.components.status_bar import StatusBar
from ui.components.menu_bar import MenuBar
from hardware.motion.theia_controller import TheiaController
from ui.views.theia_control_window import TheiaLensControlWindow
import logging
from CTkMessagebox import CTkMessagebox

class MainWindow:
    """Manages the main application window and its layout components."""
    def __init__(self, window, dart_instance):
        self.window = window
        self.dart = dart_instance
        self.views = {}
        self.theia_window = None  # Initialize as None

        # Set up persistent GUI elements
        self.setup_layout()
        self.setup_menu()
        
        # Create initial view
        self.create_view("track")
        self.switch_view("track")

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

        # Start memory monitoring
        self.dart.get_mem()

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

    def setup_menu(self):
        """Set up the menu bar"""
        self.menu_bar = MenuBar(
            parent=self.window,
            dart_instance=self.dart,
            track_callback=self.dart.track,
            exit_callback=self.dart.on_closing,
            lens_control_callback=self.open_theia_control_window
        )

    def open_theia_control_window(self):
        """Open the Theia lens control window"""
        # Check if window exists and is valid
        if self.theia_window is not None:
            try:
                if self.theia_window.winfo_exists():
                    self.theia_window.lift()
                    self.theia_window.focus_force()
                    return
            except Exception:
                # Window is invalid, clean up reference
                self.theia_window = None

        # Check Theia controller connection
        if not self.dart.theia or not hasattr(self.dart.theia, 'ser') or not self.dart.theia.ser.is_open:
            try:
                # Try to reconnect
                device_config = self.dart.config.config["devices"]
                if device_config["theia_port"]:
                    self.dart.theia = TheiaController(device_config["theia_port"])
                    self.dart.theia.connect()
                    self.dart.theia.initialise()
                    logging.info(f"Reconnected to Theia controller")
            except Exception as e:
                logging.error(f"Failed to connect to Theia controller: {e}")
                CTkMessagebox(
                    title="Error",
                    message="Could not connect to Theia controller. Please check hardware connection.",
                    icon="cancel"
                )
                return

        # Create new window
        try:
            self.theia_window = TheiaLensControlWindow(self.window, self.dart)
            self.theia_window.protocol("WM_DELETE_WINDOW", self.on_theia_window_close)
            self.theia_window.grab_set()
        except Exception as e:
            logging.error(f"Error creating Theia control window: {e}")
            self.theia_window = None

    def on_theia_window_close(self):
        """Handle Theia window closing"""
        if self.theia_window is not None:
            self.theia_window.grab_release()
            self.theia_window.destroy()
            self.theia_window = None

    def cleanup_resources(self):
        """Clean up resources before closing"""
        # Close Theia window if open
        if self.theia_window is not None:
            self.on_theia_window_close()
            
        # Clean up other resources
        for view in self.views.values():
            view.cleanup()
        
        for widget in self.window.winfo_children():
            widget.destroy()