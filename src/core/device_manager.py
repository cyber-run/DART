import json
import serial.tools.list_ports
import PySpin
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class DeviceManager:
    """Manages device detection and configuration persistence"""
    def __init__(self, config_manager):
        self.config = config_manager
        
    def get_device_config(self) -> Dict:
        """Get current device configuration"""
        return self.config.config["devices"]
    
    def save_device_config(self, config: Dict) -> None:
        """Save device configuration"""
        self.config.update_device_config(config)
    
    def detect_devices(self) -> Tuple[bool, str]:
        """Detect connected DART devices"""
        try:
            logging.info("Starting device detection...")
            
            # Look for new devices using stored initial state
            new_ports = set(self.get_com_ports()) - self.initial_ports
            new_cameras = set(self.get_camera_serials()) - self.initial_cameras
            
            logging.info(f"New ports detected: {new_ports}")
            logging.info(f"New cameras detected: {new_cameras}")
            
            # First check if we found both cameras
            if len(new_cameras) != 2:
                return False, f"Expected 2 FLIR cameras, found {len(new_cameras)}"
            
            # Then check if we found both COM ports
            if len(new_ports) != 2:
                return False, f"Expected 2 COM ports, found {len(new_ports)}"
            
            # Identify which port is which
            dyna_port, theia_port = self.identify_com_ports(new_ports)
            
            logging.info(f"Identified ports - Dyna: {dyna_port}, Theia: {theia_port}")
            
            if dyna_port and theia_port:
                # Update configuration through config manager
                self.save_device_config({
                    "dynamixel_port": dyna_port,
                    "theia_port": theia_port,
                    "cameras": list(new_cameras)
                })
                return True, "Device detected and configured successfully"
            
            return False, "Failed to identify COM ports"
            
        except Exception as e:
            logging.error(f"Error detecting devices: {e}")
            return False, f"Error during device detection: {str(e)}"
    
    def get_com_ports(self) -> List[str]:
        """Get list of available COM ports"""
        return [port.device for port in serial.tools.list_ports.comports()]
    
    def get_camera_serials(self) -> List[str]:
        """Get list of connected FLIR camera serials using PySpin"""
        cameras = []
        system = None
        cam_list = None
        
        try:
            # Initialize PySpin system
            system = PySpin.System.GetInstance()
            cam_list = system.GetCameras()
            num_cameras = cam_list.GetSize()
            
            logging.info(f"Found {num_cameras} cameras")
            
            if num_cameras == 0:
                return []
            
            for i in range(num_cameras):
                try:
                    # Get camera using index
                    cam = cam_list.GetByIndex(i)
                    
                    if not cam.IsValid():
                        continue
                        
                    # Initialize camera
                    if not cam.IsInitialized():
                        cam.Init()
                    
                    # Get TL device nodemap and serial number
                    nodemap = cam.GetTLDeviceNodeMap()
                    serial_node = PySpin.CStringPtr(nodemap.GetNode('DeviceSerialNumber'))
                    
                    if PySpin.IsReadable(serial_node):
                        serial_number = serial_node.GetValue()
                        cameras.append(str(serial_number))
                        logging.info(f"Found camera with serial: {serial_number}")
                    
                    # Deinitialize camera
                    cam.DeInit()
                    del cam
                    
                except PySpin.SpinnakerException as e:
                    logging.error(f"Error accessing camera {i}: {e}")
                    continue
            
            return cameras
            
        except PySpin.SpinnakerException as e:
            logging.error(f"Error in PySpin system: {e}")
            return []
            
        finally:
            # Clean up
            try:
                if cam_list is not None:
                    cam_list.Clear()
                if system is not None:
                    system.ReleaseInstance()
            except PySpin.SpinnakerException as e:
                logging.error(f"Error cleaning up PySpin system: {e}")
    
    def identify_com_ports(self, ports: set) -> Tuple[Optional[str], Optional[str]]:
        """
        Identify which COM port is for Dynamixel and which is for Theia
        Returns: (dynamixel_port, theia_port)
        """
        dyna_port = None
        theia_port = None
        remaining_ports = set(ports)  # Keep track of unidentified ports
        
        # First try to identify Dynamixel port
        for port in ports:
            try:
                from hardware.motion.dyna_controller import DynaController
                dyna = DynaController(port)
                if dyna.open_port():
                    dyna_port = port
                    dyna.close_port()
                    remaining_ports.remove(port)
                    logging.info(f"Identified Dynamixel port: {port}")
                    break  # Exit loop once Dynamixel is found
            except Exception as e:
                logging.debug(f"Port {port} is not Dynamixel: {e}")
                continue
        
        # If Dynamixel was found and only one port remains, assume it's Theia
        if dyna_port and len(remaining_ports) == 1:
            theia_port = remaining_ports.pop()
            logging.info(f"Assuming remaining port is Theia: {theia_port}")
            return dyna_port, theia_port
        
        # If Dynamixel wasn't found or multiple ports remain, try to identify Theia
        for port in remaining_ports:
            try:
                from hardware.motion.theia_controller import TheiaController
                theia = TheiaController(port)
                theia.connect()
                
                # Try to read status - if no error, assume it's Theia
                status = theia._ser_send("!1")
                if status:  # Add any specific validation of status format if needed
                    theia_port = port
                    logging.info(f"Identified Theia port through status check: {port}")
                
                theia.disconnect()
                
                if theia_port:
                    break
                    
            except Exception as e:
                logging.debug(f"Port {port} is not Theia: {e}")
                continue
        
        # Log the final identification results
        if dyna_port and theia_port:
            logging.info(f"Successfully identified both ports - Dyna: {dyna_port}, Theia: {theia_port}")
        elif dyna_port:
            logging.warning("Only Dynamixel port identified")
        elif theia_port:
            logging.warning("Only Theia port identified")
        else:
            logging.error("Failed to identify any ports")
            
        return dyna_port, theia_port
    
    def verify_camera_access(self, serial: str) -> bool:
        """Verify that a camera with given serial number is accessible"""
        try:
            system = PySpin.System.GetInstance()
            cam_list = system.GetCameras()
            
            cam = cam_list.GetBySerial(serial)
            if cam.IsValid():
                cam.Init()
                cam.DeInit()
                result = True
            else:
                result = False
                
            del cam
            cam_list.Clear()
            system.ReleaseInstance()
            
            return result
            
        except PySpin.SpinnakerException as e:
            logging.error(f"Error verifying camera {serial}: {e}")
            return False