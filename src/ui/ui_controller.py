import customtkinter as ctk
import logging
from typing import Any

class UIController:
    def __init__(self, dart_instance):
        self.dart = dart_instance
        
    def update_status_text(self, text: str) -> None:
        """Update the status bar text"""
        if self.dart.state.ui.status_label:
            self.dart.state.ui.status_label.configure(text=text)
            
    def update_memory_usage(self, usage: float) -> None:
        """Update the memory usage display"""
        if self.dart.state.ui.memory_label:
            try:
                self.dart.state.ui.memory_label.configure(
                    text=f"Memory usage: {round(usage, 1)}%"
                )
            except Exception as e:
                logging.error(f"Error updating memory label: {e}")
            
    def update_camera_status(self, status: str) -> None:
        """Update camera connection status"""
        if self.dart.state.ui.camera_status:
            self.dart.state.ui.camera_status.configure(text=f"Camera: {status}")
            
    def update_mocap_status(self, status: str) -> None:
        """Update motion capture status"""
        if self.dart.state.ui.mocap_status:
            self.dart.state.ui.mocap_status.configure(text=f"Mocap: {status}")
            
    def update_motors_status(self, status: str) -> None:
        """Update motor status"""
        if self.dart.state.ui.motors_status:
            self.dart.state.ui.motors_status.configure(text=f"Motors: {status}")
            
    def update_calibration_age(self, age: int) -> None:
        """Update calibration age display"""
        if self.dart.state.ui.age_label:
            self.dart.state.ui.age_label.configure(text=f"Calibration age: {age} h")
            
    def update_track_button(self, text: str, icon: Any) -> None:
        """Update the track button text and icon"""
        if self.dart.state.ui.track_button:
            self.dart.state.ui.track_button.configure(text=text, image=icon)

    def update_pan_label(self, value: float) -> None:
        """Update pan angle display"""
        if self.dart.state.ui.pan_label:
            self.dart.state.ui.pan_label.configure(text=f"Pan: {round(value,1)}°")

    def update_tilt_label(self, value: float) -> None:
        """Update tilt angle display"""
        if self.dart.state.ui.tilt_label:
            self.dart.state.ui.tilt_label.configure(text=f"Tilt: {round(value,1)}°")

    def update_slider_values(self, pan: float = 0, tilt: float = 0) -> None:
        """Update slider positions"""
        if self.dart.state.ui.pan_slider:
            self.dart.state.ui.pan_slider.set(pan)
        if self.dart.state.ui.tilt_slider:
            self.dart.state.ui.tilt_slider.set(tilt)

    def update_fps(self, fps: float) -> None:
        """Update FPS display"""
        if self.dart.state.ui.fps_label:
            self.dart.state.ui.fps_label.configure(text=f"FPS: {round(fps, 2)}")
            
    def update_exposure(self, value: float) -> None:
        """Update exposure display"""
        if self.dart.state.ui.exposure_label:
            self.dart.state.ui.exposure_label.configure(text=f"Exposure (us): {round(value, 2)}")
            
    def update_gain(self, value: float) -> None:
        """Update gain display"""
        if self.dart.state.ui.gain_label:
            self.dart.state.ui.gain_label.configure(text=f"Gain (dB): {round(value, 2)}")

    def update_video_button(self, text: str, icon: Any) -> None:
        """Update video toggle button state"""
        if self.dart.state.ui.toggle_video_button:
            self.dart.state.ui.toggle_video_button.configure(text=text, image=icon)

    def update_marker_count(self, count: int) -> None:
        """Update the marker count display"""
        if self.dart.state.ui.num_marker_label:
            self.dart.state.ui.num_marker_label.configure(text=f"No. Markers: {count}")

    def update_mocap_button(self, text: str, icon: Any) -> None:
        """Update the mocap button text and icon"""
        if self.dart.state.ui.mocap_button:
            self.dart.state.ui.mocap_button.configure(text=text, image=icon)