import customtkinter as ctk

class TheiaLensControlWindow(ctk.CTkToplevel):
    def __init__(self, master, theia_controller):
        super().__init__(master)
        self.title("Theia Lens Control")
        self.geometry("800x600")
        self.resizable(False, False)

        self.theia_controller = theia_controller

        self.setup_ui()

    def setup_ui(self):
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Connection frame
        connection_frame = ctk.CTkFrame(main_frame)
        connection_frame.pack(fill="x", padx=10, pady=10)

        self.port_entry = ctk.CTkEntry(connection_frame, placeholder_text="Enter COM port")
        self.port_entry.pack(side="left", padx=(0, 10))

        self.connect_button = ctk.CTkButton(connection_frame, text="Connect", command=self.connect_theia)
        self.connect_button.pack(side="left")

        # Zoom control frame
        zoom_frame = ctk.CTkFrame(main_frame)
        zoom_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(zoom_frame, text="Zoom Control").pack()

        self.zoom_slider = ctk.CTkSlider(zoom_frame, from_=0, to=100, command=self.set_zoom)
        self.zoom_slider.pack(fill="x", padx=10, pady=5)

        self.zoom_label = ctk.CTkLabel(zoom_frame, text="Zoom: 0")
        self.zoom_label.pack()

        # Focus control frame
        focus_frame = ctk.CTkFrame(main_frame)
        focus_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(focus_frame, text="Focus Control").pack()

        self.focus_slider = ctk.CTkSlider(focus_frame, from_=0, to=100, command=self.set_focus)
        self.focus_slider.pack(fill="x", padx=10, pady=5)

        self.focus_label = ctk.CTkLabel(focus_frame, text="Focus: 0")
        self.focus_label.pack()

        # Home buttons frame
        home_frame = ctk.CTkFrame(main_frame)
        home_frame.pack(fill="x", padx=10, pady=10)

        self.home_zoom_button = ctk.CTkButton(home_frame, text="Home Zoom", command=self.home_zoom)
        self.home_zoom_button.pack(side="left", padx=(0, 10))

        self.home_focus_button = ctk.CTkButton(home_frame, text="Home Focus", command=self.home_focus)
        self.home_focus_button.pack(side="left")

        # Status label
        self.status_label = ctk.CTkLabel(main_frame, text="Not connected")
        self.status_label.pack(pady=10)

    def connect_theia(self):
        port = self.port_entry.get()
        try:
            self.theia_controller.connect()
            self.theia_controller.initialise()
            self.status_label.configure(text="Connected and initialized")
            self.connect_button.configure(state="disabled")
        except Exception as e:
            self.status_label.configure(text=f"Connection failed: {str(e)}")

    def set_zoom(self, value):
        if self.theia_controller.ser.is_open:
            zoom_value = int(value * 50000 / 100)  # Assuming 128000 is the max zoom value
            self.theia_controller.move_axis("A", zoom_value)
            self.zoom_label.configure(text=f"Zoom: {int(value)}")
        else:
            self.status_label.configure(text="Not connected")

    def set_focus(self, value):
        if self.theia_controller.ser.is_open:
            focus_value = int(value * 133000 / 100)  # Assuming 128000 is the max focus value
            self.theia_controller.move_axis("B", focus_value)
            self.focus_label.configure(text=f"Focus: {int(value)}")
        else:
            self.status_label.configure(text="Not connected")

    def home_zoom(self):
        if self.theia_controller.ser.is_open:
            self.theia_controller.home_zoom()
            self.zoom_slider.set(0)
            self.zoom_label.configure(text="Zoom: 0")
            self.status_label.configure(text="Zoom homed")
        else:
            self.status_label.configure(text="Not connected")

    def home_focus(self):
        if self.theia_controller.ser.is_open:
            self.theia_controller.home_focus()
            self.focus_slider.set(0)
            self.focus_label.configure(text="Focus: 0")
            self.status_label.configure(text="Focus homed")
        else:
            self.status_label.configure(text="Not connected")

if __name__ == "__main__":
    import os
    import sys

    # Add the parent directory of 'dev' to the Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    sys.path.append(parent_dir)

    # This block allows you to run and test the Theia Lens Control Window independently
    import tkinter as tk
    from dev.controllers.theia_controller import TheiaController


    # Create a dummy root window (it won't be shown)
    root = tk.Tk()
    root.withdraw()

    # Create a TheiaController instance
    theia_controller = TheiaController(port="COM17")

    # Create and run the Theia Lens Control Window
    app = TheiaLensControlWindow(root, theia_controller)
    app.protocol("WM_DELETE_WINDOW", root.quit)  # Ensure the app closes properly
    app.mainloop()