from .mocap_base import MocapBase
import threading
import socket
import json
import time
from pyvicon_datastream import PyViconDatastream, StreamMode, Result

class ViconStream(MocapBase):
    def __init__(self, vicon_host="localhost", udp_port=51001):
        super().__init__()
        self.vicon_host = vicon_host
        self.udp_ip = vicon_host
        self.udp_port = udp_port
        self.client = None
        self.udp_socket = None
        
        # Thread control
        self._thread = None
        self._running = False
        self._lock = threading.Lock()
        self._markers = []
        self._last_frame_time = 0.0

    def connect(self) -> bool:
        """Connect to the Vicon system and setup UDP."""
        try:
            self.client = PyViconDatastream()
            
            # Connect to the Vicon system
            print(f"Connecting to Vicon system at {self.vicon_host}")
            
            # Create an event for connection status
            connection_success = threading.Event()
            connection_error = None
            
            def connect_with_timeout():
                nonlocal connection_error
                try:
                    result = self.client.connect(self.vicon_host)
                    if self.client.is_connected():
                        connection_success.set()
                except Exception as e:
                    connection_error = e
                    
            # Start connection in thread
            connect_thread = threading.Thread(target=connect_with_timeout)
            connect_thread.daemon = True
            connect_thread.start()
            
            # Wait for connection with timeout
            if not connection_success.wait(timeout=2.0):  # 2 second timeout
                print("Connection attempt timed out")
                return False
                
            if connection_error:
                print(f"Connection failed: {str(connection_error)}")
                return False
                
            # Enable the data types we need
            self.client.enable_marker_data()
            self.client.enable_unlabeled_marker_data()
            
            # Set streaming mode
            self.client.set_stream_mode(StreamMode.ClientPull)
            
            # Get initial frame with timeout
            connection_timeout = time.time() + 2  # 2 second timeout
            while time.time() < connection_timeout:
                if self.client.get_frame() == Result.Success:
                    break
                time.sleep(0.1)
            else:
                print("Timeout waiting for first frame")
                return False
            
            print(f"Connected to Vicon system at {self.vicon_host}")
            
            # Setup UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print(f"UDP socket setup complete on {self.udp_ip}:{self.udp_port}")
            
            return True
        except Exception as e:
            print(f"Failed to connect: {str(e)}")
            return False

    def start(self, frequency: float = 200.0):
        """Start the Vicon stream"""
        if self._thread is not None and self._thread.is_alive():
            print("Already streaming")
            return
            
        if not self.connect():
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._stream_thread, args=(frequency,))
        self._thread.daemon = True
        self._thread.start()

    def _stream_thread(self, frequency: float):
        """Thread function for continuous streaming."""
        period = 1.0 / frequency
        last_update = 0
        update_interval = 1.0 / 30  # Limit internal updates to 30Hz
        
        while self._running:
            start_time = time.time()
            
            # Get marker data
            markers = self.get_unlabeled_markers()
            
            current_time = time.time()
            # Only update internal state at a lower frequency
            if current_time - last_update >= update_interval:
                # Update internal state
                with self._lock:
                    self._markers = markers
                    self._last_frame_time = start_time
                last_update = current_time
            
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

    def get_unlabeled_markers(self) -> list:
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

    def close(self):
        """Match QTMStream interface"""
        self.disconnect()

    def disconnect(self):
        """Stop streaming and disconnect."""
        self._running = False
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        if self.udp_socket:
            self.udp_socket.close()
        if self.client:
            self.client.disconnect()
        print("Disconnected from Vicon system")
        
    @property
    def position(self):
        """Match QTMStream interface"""
        markers, _ = self.get_current_markers()
        if markers and len(markers) > 0:
            return markers[0]
        return [0, 0, 0]
        
    @property
    def position2(self):
        """Match QTMStream interface"""
        markers, _ = self.get_current_markers()
        if markers and len(markers) > 1:
            return markers[1]
        return [0, 0, 0]
        
    @property
    def num_markers(self):
        """Match QTMStream interface with minimal locking"""
        try:
            with self._lock:
                return len(self._markers)
        except:
            return 0

    def get_current_markers(self):
        """Get the most recent marker positions and timestamp."""
        with self._lock:
            return self._markers.copy(), self._last_frame_time