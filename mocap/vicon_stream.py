import socket
import json
import time
import math
import numpy as np
from pyvicon_datastream import PyViconDatastream, StreamMode, Result
import threading
from typing import List, Optional, Tuple
from mocap_base import MocapBase

class ViconStream(MocapBase):
    def __init__(self, 
                 vicon_host: str = "localhost",
                 udp_ip: str = "0.0.0.0",
                 udp_port: int = 51001):
        """
        Initialize Vicon streaming class.
        
        Args:
            vicon_host: Hostname/IP of the Vicon system
            udp_ip: UDP broadcast IP
            udp_port: UDP port to stream on
        """
        super().__init__()
        self.vicon_host = vicon_host
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.client = None
        self.udp_socket = None
        
        # Thread control
        self._thread: Optional[threading.Thread] = None
        
        # State variables
        self._lock = threading.Lock()
        self._markers: List[List[float]] = []
        self._last_frame_time = 0.0
        
    def connect(self) -> bool:
        """Connect to the Vicon system and setup UDP."""
        try:
            self.client = PyViconDatastream()
            
            # Connect to the Vicon system
            print(f"Connecting to Vicon system at {self.vicon_host}")
            result = self.client.connect(self.vicon_host)
            if not self.client.is_connected():
                print("Failed to connect to Vicon system")
                return False
                
            # Enable the data types we need
            self.client.enable_marker_data()
            self.client.enable_unlabeled_marker_data()
            
            # Set streaming mode
            self.client.set_stream_mode(StreamMode.ClientPull)
            
            # Get initial frame to verify connection
            for _ in range(40):  # Try a few times to get a frame
                if self.client.get_frame() == Result.Success:
                    break
                time.sleep(0.1)
            
            print(f"Connected to Vicon system at {self.vicon_host}")
            
            # Setup UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print(f"UDP socket setup complete on {self.udp_ip}:{self.udp_port}")
            
            return True
        except Exception as e:
            print(f"Failed to connect: {str(e)}")
            return False
            
    def disconnect(self):
        """Stop streaming and disconnect."""
        self.stop()
        if self.udp_socket:
            self.udp_socket.close()
        if self.client:
            self.client.disconnect()
        print("Disconnected from Vicon system")
    
    def get_unlabeled_markers(self) -> List[List[float]]:
        """Get all unlabeled marker positions."""
        if not self.client or not self.client.is_connected():
            return []
            
        try:
            # Get a new frame
            if self.client.get_frame() != Result.Success:
                return []
                
            # Get marker count
            marker_count = self.client.get_unlabeled_marker_count()
            if marker_count is None:
                return []
                
            markers = []
            for i in range(marker_count):
                # Get marker position
                marker_data = self.client.get_unlabeled_marker_global_translation(i)
                if marker_data is not None:
                    markers.append([
                        float(marker_data[0]),  # x
                        float(marker_data[1]),  # y
                        float(marker_data[2])   # z
                    ])
            return markers
        except Exception as e:
            print(f"Error getting markers: {str(e)}")
            return []
    
    def _stream_thread(self, frequency: float):
        """Thread function for continuous streaming."""
        period = 1.0 / frequency
        
        while self._running:
            start_time = time.time()
            
            # Get marker data
            markers = self.get_unlabeled_markers()
            
            # Update internal state
            with self._lock:
                self._markers = markers
                self._last_frame_time = start_time
            
            # Create and send UDP packet
            data = {
                "timestamp": start_time,
                "num_markers": len(markers),
                "markers": markers
            }
            
            try:
                data_bytes = json.dumps(data).encode('utf-8')
                self.udp_socket.sendto(data_bytes, (self.udp_ip, self.udp_port))
            except Exception as e:
                print(f"Error sending UDP data: {str(e)}")
            
            # Maintain frequency
            elapsed = time.time() - start_time
            if elapsed < period:
                time.sleep(period - elapsed)
    
    def start(self, frequency: float = 200.0):
        """Start the streaming thread."""
        if self._thread is not None and self._thread.is_alive():
            print("Already streaming")
            return
            
        if not self.connect():
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._stream_thread, args=(frequency,))
        self._thread.daemon = True
        self._thread.start()
        print(f"Started Vicon streaming at {frequency}Hz")
    
    def stop(self):
        """Stop the streaming thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        print("Stopped Vicon streaming")
    
    def get_current_markers(self) -> Tuple[List[List[float]], float]:
        """Get the most recent marker positions and timestamp."""
        with self._lock:
            return self._markers.copy(), self._last_frame_time

if __name__ == "__main__":
    # Example usage
    streamer = ViconStream(
        vicon_host="192.168.0.100", 
        udp_ip="192.168.0.100",    
        udp_port=51001
    )
    
    try:
        streamer.start(frequency=200)  # Start streaming at 200Hz
        while True:
            markers, timestamp = streamer.get_current_markers()
            # print(f"\rMarkers: {len(markers)}, Time: {timestamp:.3f}", end="")
            # Print marker positions
            for i, marker in enumerate(markers):
                print(f"Marker {i+1}: {marker}")

            # time.sleep(0.1)  # Print update rate
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        streamer.disconnect()