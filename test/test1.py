import tkinter as tk
from tkinter import ttk
import logging
import asyncio
import threading
from qtm_mocap import QTMControl  # Assuming this is your custom module or adjust the import as necessary

class TkinterAsyncioBridge:
    def __init__(self, loop):
        self.loop = loop
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)

    def start(self):
        self.thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

    def run_coroutine(self, coro):
        asyncio.run_coroutine_threadsafe(coro, self.loop)

class QTMApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QTM Control")

        # Setup the asyncio event loop for the bridge
        loop = asyncio.new_event_loop()
        self.bridge = TkinterAsyncioBridge(loop)
        self.bridge.start()

        # Setup the QTMControl instance
        self.control = QTMControl()

        # Setup the GUI
        self.setup_gui()

    def setup_gui(self):
        self.start_button = ttk.Button(self.root, text="Start Recording", command=self.start_recording)
        self.start_button.pack(pady=10)

        self.stop_button = ttk.Button(self.root, text="Stop Recording", command=self.stop_recording)
        self.stop_button.pack(pady=10)

        self.pause_button = ttk.Button(self.root, text="Pause Recording", command=lambda: self.set_qtm_event('Paused'))
        self.pause_button.pack(pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def start_recording(self):
        self.bridge.run_coroutine(self.control.start_recording())

    def stop_recording(self):
        self.bridge.run_coroutine(self.control.stop_recording())

    def set_qtm_event(self, event_str='Paused'):
        self.bridge.run_coroutine(self.control.set_qtm_event(event_str))

    def close_app(self):
        # Schedule the control's close coroutine in the asyncio event loop
        self.control.close()

        # Stop the bridge's event loop
        self.bridge.stop()

        # Destroy the Tkinter root window, ensuring it's done from the main thread
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = QTMApp(root)
    root.mainloop()
