import numpy as np
import logging
from typing import List, Tuple, Dict, Optional

class CalibrationSolver:
    """Handles the mathematical computations for calibration"""
    def __init__(self):
        self.logger = logging.getLogger("CalibrationSolver")

    def compute_camera_mocap_transform(self, 
                                     aruco_poses: List[Tuple[np.ndarray, np.ndarray]], 
                                     mocap_poses: List[Tuple[np.ndarray, np.ndarray]]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute transformation between camera and mocap space
        Returns: (rotation_matrix, translation_vector)
        """
        if len(aruco_poses) < 1:  # Only need one pose since ArUco is stationary
            raise ValueError("Need at least 1 pose pair")
            
        try:
            # We only need the first pose pair since ArUco is stationary
            R_cam, t_cam = aruco_poses[0]
            R_mocap, t_mocap = mocap_poses[0]
            
            # Debug prints
            self.logger.debug(f"ArUco R:\n{R_cam}")
            self.logger.debug(f"ArUco t: {t_cam}")
            self.logger.debug(f"Mocap R:\n{R_mocap}")
            self.logger.debug(f"Mocap t: {t_mocap}")
            
            # Direct computation of rotation and translation
            R = R_mocap @ R_cam.T
            T = t_mocap - R @ t_cam
            
            # Verify transformation with a test point
            test_point_cam = t_cam
            test_point_mocap = R @ test_point_cam + T
            self.logger.debug(f"Test point camera space: {test_point_cam}")
            self.logger.debug(f"Test point mocap space: {test_point_mocap}")
            self.logger.debug(f"Should be close to mocap t: {t_mocap}")
            
            return R, T
            
        except Exception as e:
            self.logger.error(f"Error computing transformation: {e}")
            raise

    def compute_mirror_center(self, mirror_data: List[Dict]) -> Tuple[np.ndarray, float]:
        """
        Compute mirror center from collected ray data using ray intersection method
        Returns: (mirror_center_position, RMS_error)
        """
        if len(mirror_data) < 5:
            raise ValueError("Need at least 5 mirror calibration points")
            
        try:
            # Extract ray origins and directions
            origins = np.array([data['ray_origin'] for data in mirror_data])
            directions = np.array([data['ray_direction'] for data in mirror_data])
            angles = np.array([data['tilt_angle'] for data in mirror_data])
            
            # Ensure proper shapes
            origins = origins.reshape(-1, 3)
            directions = directions.reshape(-1, 3)
            
            # Normalize all direction vectors
            directions = directions / np.linalg.norm(directions, axis=1)[:, np.newaxis]
            
            # Set up least squares problem for finding closest point to all rays
            n_rays = len(mirror_data)
            A = np.zeros((n_rays * 3, 3))
            b = np.zeros(n_rays * 3)
            
            for i in range(n_rays):
                # Projection matrix for each ray
                P = np.eye(3) - np.outer(directions[i], directions[i])
                A[i*3:(i+1)*3] = P
                b[i*3:(i+1)*3] = P @ origins[i]
            
            # Solve for mirror center
            mirror_center, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
            
            # Compute RMS error
            errors = []
            for i in range(n_rays):
                # Vector from ray origin to mirror center
                v = mirror_center - origins[i]
                # Project this vector onto ray direction
                proj = np.dot(v, directions[i]) * directions[i]
                # Distance from mirror center to ray
                error = np.linalg.norm(v - proj)
                errors.append(error)
            
            rms_error = np.sqrt(np.mean(np.array(errors)**2))
            
            # Log successful points
            self.logger.info(f"Successfully used {n_rays} points for mirror center computation")
            self.logger.info(f"Angle range: {min(angles):.1f}° to {max(angles):.1f}°")
            
            # Validate result
            if rms_error > 10:  # More than 10mm average error
                self.logger.warning(f"Large RMS error in mirror center computation: {rms_error:.1f}mm")
            
            return mirror_center, rms_error
            
        except Exception as e:
            self.logger.error(f"Error computing mirror center: {e}")
            raise