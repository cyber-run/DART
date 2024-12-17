from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import threading

class MocapBase(ABC):
    """Base class for motion capture systems."""
    
    def __init__(self):
        self.markers = None
        self.position = [0, 0, 0]
        self.position2 = [0, 0, 0]
        self.lost = False
        self.calibration_target = False
        self.num_markers = 0
        self._stay_open = True
        
    @abstractmethod
    def start(self) -> None:
        """Start the mocap system and begin streaming data."""
        pass
        
    @abstractmethod
    def stop(self) -> None:
        """Stop the mocap system and clean up resources."""
        pass
        
    @abstractmethod
    def get_current_markers(self) -> Tuple[List[List[float]], float]:
        """Get the current marker positions and timestamp.
        
        Returns:
            Tuple containing:
            - List of marker positions [[x, y, z], ...]
            - Timestamp of the frame
        """
        pass
