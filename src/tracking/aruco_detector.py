import cv2
import numpy as np
import logging
import os
import sys

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class ArucoDetector:
    def __init__(self, marker_size=0.04):
        """
        Initialize ArUco detector with specified marker size.
        
        Args:
            marker_size (float): Size of ArUco marker in meters (default: 0.04 = 40mm)
        """
        self.logger = logging.getLogger("ArucoDetector")
        
        # ArUco setup
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        # ArUco marker properties
        self.marker_size = marker_size
        
        # Load camera calibration
        try:
            self.camera_matrix = np.load('camera_matrix.npy')
            self.dist_coeffs = np.load('dist_coeffs.npy')
            self.logger.info("Camera calibration loaded successfully")
            self.logger.info(f"Camera matrix:\n{self.camera_matrix}")
        except Exception as e:
            self.logger.error(f"Failed to load camera calibration: {e}")
            self.logger.warning("Using placeholder calibration values")
            self.camera_matrix = np.array([
                [800, 0, 320],
                [0, 800, 240],
                [0, 0, 1]
            ])
            self.dist_coeffs = np.zeros(5)

    def detect_markers(self, frame):
        """
        Detect ArUco markers in the given frame.
        
        Args:
            frame: Input image frame
            
        Returns:
            tuple: (corners, ids, rejected)
        """
        if frame is None:
            return None, None, None
        return self.aruco_detector.detectMarkers(frame)

    def estimate_pose(self, corners):
        """
        Estimate pose of detected marker.
        
        Args:
            corners: Corners of detected marker
            
        Returns:
            tuple: (success, rotation_vector, translation_vector)
        """
        if corners is None or len(corners) == 0:
            return False, None, None
            
        pose_estimator = cv2.solvePnP(
            objectPoints=np.array([
                [-self.marker_size/2, self.marker_size/2, 0],
                [self.marker_size/2, self.marker_size/2, 0],
                [self.marker_size/2, -self.marker_size/2, 0],
                [-self.marker_size/2, -self.marker_size/2, 0]
            ], dtype=np.float32),
            imagePoints=corners[0].reshape(-1, 2),
            cameraMatrix=self.camera_matrix,
            distCoeffs=self.dist_coeffs
        )
        
        if pose_estimator[0]:
            return True, pose_estimator[1], pose_estimator[2]
        return False, None, None

    def draw_markers(self, frame, corners, ids):
        """
        Draw detected markers on frame.
        
        Args:
            frame: Input image frame
            corners: Detected marker corners
            ids: Marker IDs
            
        Returns:
            frame: Frame with markers drawn
        """
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        return frame

    def process_frame(self, frame):
        """
        Complete frame processing pipeline.
        
        Args:
            frame: Input image frame
            
        Returns:
            tuple: (success, rotation_vector, translation_vector, corners, ids)
        """
        if frame is None:
            return False, None, None, None, None
            
        corners, ids, rejected = self.detect_markers(frame)
        
        if ids is not None:
            success, rvec, tvec = self.estimate_pose(corners)
            if success:
                return True, rvec, tvec, corners, ids
                
        return False, None, None, corners, ids
