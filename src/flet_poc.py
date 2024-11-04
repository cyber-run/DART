import flet as ft
import cv2
import numpy as np
from PIL import Image
import io
from threading import Thread
import time
import logging
from hardware.camera.camera_manager import CameraManager
import base64

class DARTVideoFeed:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "DART Video Feed"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20
        
        # Configure window
        self.page.window_width = 1000
        self.page.window_height = 800
        self.page.window_resizable = True
        
        # Initialize camera manager
        self.camera_manager = CameraManager()
        
        # Create UI elements
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize all UI elements"""
        # Create image display
        self.video_image = ft.Image(
            width=800,
            height=600,
            fit=ft.ImageFit.CONTAIN,
            src=None  # Start with no image
        )
        
        # Create control buttons
        self.toggle_button = ft.ElevatedButton(
            text="Start",
            icon=ft.icons.PLAY_ARROW,
            on_click=self.toggle_video,
            style=ft.ButtonStyle(
                color={ft.MaterialState.DEFAULT: ft.colors.WHITE},
                bgcolor={
                    ft.MaterialState.DEFAULT: ft.colors.BLUE,
                    ft.MaterialState.HOVERED: ft.colors.BLUE_700,
                },
            )
        )
        
        # Create camera selection dropdown
        available_cameras = self.camera_manager.get_available_cameras()
        self.camera_dropdown = ft.Dropdown(
            width=150,
            options=[ft.dropdown.Option(cam) for cam in available_cameras],
            label="Select Camera",
            on_change=self.on_camera_selected
        )
        
        # Create exposure and gain sliders
        self.exposure_slider = ft.Slider(
            min=4,
            max=4000,
            value=1000,
            label="Exposure (μs)",
            on_change=self.update_exposure
        )
        
        self.gain_slider = ft.Slider(
            min=0,
            max=47,
            value=10,
            label="Gain (dB)",
            on_change=self.update_gain
        )
        
        # FPS display
        self.fps_text = ft.Text(f"FPS: {self.camera_manager.fps}", color=ft.colors.WHITE70)
        
        # Add recording button
        self.record_button = ft.ElevatedButton(
            text="Record",
            icon=ft.icons.FIBER_MANUAL_RECORD,
            on_click=self.toggle_recording
        )
        
        # Layout
        self.page.add(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[self.video_image],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            self.camera_dropdown,
                            self.toggle_button,
                            self.fps_text,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Exposure"),
                                    self.exposure_slider,
                                ]
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Gain"),
                                    self.gain_slider,
                                ]
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    def on_camera_selected(self, e):
        """Handle camera selection"""
        if e.data:
            camera_index = int(e.data.split(" ")[1])
            self.camera_manager.connect_camera(camera_index)
            self.update_fps_display()

    def toggle_video(self, e):
        """Toggle video feed on/off"""
        if not self.camera_manager.is_reading:
            self.start_video()
            self.toggle_button.text = "Stop"
            self.toggle_button.icon = ft.icons.STOP
        else:
            self.stop_video()
            self.toggle_button.text = "Start"
            self.toggle_button.icon = ft.icons.PLAY_ARROW
        
        self.toggle_button.update()

    def start_video(self):
        """Start video capture"""
        self.camera_manager.start_frame_thread()
        Thread(target=self.update_frame, daemon=True).start()

    def stop_video(self):
        """Stop video capture"""
        self.camera_manager.stop_frame_thread()

    def update_frame(self):
        """Update video frame"""
        while self.camera_manager.is_reading:
            frame = self.camera_manager.latest_frame
            if frame is not None:
                try:
                    # Convert frame to format suitable for display
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame)
                    
                    # Convert to base64 without data URI prefix
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    img_base64 = base64.b64encode(buf.getvalue()).decode()
                    
                    # Update image with new frame
                    self.video_image.src_base64 = img_base64
                    self.video_image.update()
                except Exception as e:
                    logging.error(f"Error updating frame: {e}")
            
            time.sleep(0.03)  # ~30 FPS

    def update_exposure(self, e):
        """Update camera exposure"""
        if self.camera_manager.cap:
            self.camera_manager.cap.set(cv2.CAP_PROP_EXPOSURE, e.data)
            self.update_fps_display()

    def update_gain(self, e):
        """Update camera gain"""
        if self.camera_manager.cap:
            self.camera_manager.cap.set(cv2.CAP_PROP_GAIN, e.data)

    def update_fps_display(self):
        """Update FPS display"""
        if self.camera_manager.cap:
            self.fps_text.value = f"FPS: {round(self.camera_manager.fps, 2)}"
            self.fps_text.update()

    def cleanup(self):
        """Clean up resources"""
        self.stop_video()
        self.camera_manager.release()

def main(page: ft.Page):
    app = DARTVideoFeed(page)
    page.on_close = app.cleanup

if __name__ == "__main__":
    ft.app(target=main)