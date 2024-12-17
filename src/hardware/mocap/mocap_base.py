from abc import ABC, abstractmethod

class MocapBase(ABC):
    def __init__(self):
        self._position = [0, 0, 0]
        self._position2 = [0, 0, 0]
        self._lost = False
        self._calibration_target = False
        self._num_markers = 0

    @abstractmethod
    def start(self):
        """Start the motion capture stream"""
        pass

    @property
    @abstractmethod
    def position(self):
        pass

    @property
    @abstractmethod
    def position2(self):
        pass

    @property
    def lost(self):
        return self._lost

    @lost.setter
    def lost(self, value):
        self._lost = value

    @property
    def calibration_target(self):
        return self._calibration_target

    @calibration_target.setter
    def calibration_target(self, value):
        self._calibration_target = value

    @property
    @abstractmethod
    def num_markers(self):
        pass

    @abstractmethod
    def close(self):
        pass 