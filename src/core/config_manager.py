import json
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

class ConfigManager:
    """Manages centralized application configuration"""
    def __init__(self, config_path: str = "config/app_config.json"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.logger = logging.getLogger("ConfigManager")
        
    def get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            "devices": {
                "cameras": {
                    "tracking": "24211773",  # Visual tracking camera
                    "recording": "23473307"  # Recording camera
                },
                "dynamixel_port": "",
                "theia_port": "",
                "last_detected": None,
                "theia_state": {
                    "zoom_position": 0,
                    "focus_position": 0,
                    "iris_position": 0
                }
            },
            "calibration": {
                "pan_origin": None,
                "tilt_origin": None,
                "rotation_matrix": None,
                "timestamp": None,
                "is_calibrated": False
            },
            "tracking": {
                "use_kalman": True,
                "mode": "mocap",  # Can be 'mocap' or 'visual'
                "visual_tracking": {
                    "frame_history": 60,
                    "deviation_threshold": 4.0,
                    "min_contour_area": 100,
                    "max_object_distance": 75,
                    "learning_rate": 0.005,
                    "min_object_lifespan": 3
                }
            }
        }
    
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.logger.error("Invalid configuration file")
                return self.get_default_config()
        return self.get_default_config()
    
    def reload_config(self) -> None:
        """Reload configuration from JSON file"""
        self.config = self.load_config()
        
    def save_config(self) -> None:
        """Save configuration to JSON file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert numpy arrays to lists for JSON serialization
        config_copy = self.config.copy()
        
        # Only convert to list if it's a numpy array
        if config_copy["calibration"]["pan_origin"] is not None:
            if hasattr(config_copy["calibration"]["pan_origin"], 'tolist'):
                config_copy["calibration"]["pan_origin"] = config_copy["calibration"]["pan_origin"].tolist()
                
        if config_copy["calibration"]["tilt_origin"] is not None:
            if hasattr(config_copy["calibration"]["tilt_origin"], 'tolist'):
                config_copy["calibration"]["tilt_origin"] = config_copy["calibration"]["tilt_origin"].tolist()
                
        if config_copy["calibration"]["rotation_matrix"] is not None:
            if hasattr(config_copy["calibration"]["rotation_matrix"], 'tolist'):
                config_copy["calibration"]["rotation_matrix"] = config_copy["calibration"]["rotation_matrix"].tolist()
                
        with open(self.config_path, 'w') as f:
            json.dump(config_copy, f, indent=4)
    
    def update_device_config(self, devices: Dict) -> None:
        """Update device configuration"""
        self.config["devices"].update(devices)
        self.save_config()
    
    def update_calibration(self, pan_origin: np.ndarray, tilt_origin: np.ndarray, 
                          rotation_matrix: np.ndarray) -> None:
        """Update calibration data"""
        self.config["calibration"].update({
            "pan_origin": pan_origin,
            "tilt_origin": tilt_origin,
            "rotation_matrix": rotation_matrix,
            "timestamp": datetime.now().isoformat(),
            "is_calibrated": True
        })
        self.save_config()
    
    def get_calibration_age(self) -> Optional[float]:
        """Get calibration age in hours"""
        if not self.config["calibration"]["timestamp"]:
            return None
            
        timestamp = datetime.fromisoformat(self.config["calibration"]["timestamp"])
        return (datetime.now() - timestamp).total_seconds() / 3600
    
    def get_calibration_data(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], 
                                          Optional[np.ndarray]]:
        """Get calibration data as numpy arrays"""
        cal = self.config["calibration"]
        
        if not cal["is_calibrated"]:
            return None, None, None
            
        return (
            np.array(cal["pan_origin"]),
            np.array(cal["tilt_origin"]),
            np.array(cal["rotation_matrix"])
        )
    
    def update_theia_position(self, zoom: int = None, focus: int = None, iris: int = None) -> None:
        """Update stored Theia lens positions"""
        if "theia_state" not in self.config["devices"]:
            self.config["devices"]["theia_state"] = {
                "zoom_position": 0,
                "focus_position": 0,
                "iris_position": 0,
                "is_homed": False  # Track whether axes have been homed
            }
            
        if zoom is not None:
            self.config["devices"]["theia_state"]["zoom_position"] = zoom
        if focus is not None:
            self.config["devices"]["theia_state"]["focus_position"] = focus
        if iris is not None:
            # Ensure iris value is within valid range
            iris = max(0, min(150, iris))
            self.config["devices"]["theia_state"]["iris_position"] = iris
        self.save_config()

    def set_theia_homed(self, axis: str, status: bool = True) -> None:
        """Update homing status for Theia axes"""
        if "theia_state" not in self.config["devices"]:
            self.config["devices"]["theia_state"] = {
                "zoom_position": 0,
                "focus_position": 0,
                "is_homed": False
            }
            
        if axis.upper() == "A":
            self.config["devices"]["theia_state"]["zoom_homed"] = status
        elif axis.upper() == "B":
            self.config["devices"]["theia_state"]["focus_homed"] = status
            
        # If both axes are homed, set overall homed status
        if (self.config["devices"]["theia_state"].get("zoom_homed", False) and 
            self.config["devices"]["theia_state"].get("focus_homed", False)):
            self.config["devices"]["theia_state"]["is_homed"] = True
            
        self.save_config()