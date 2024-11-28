import numpy as np
import logging
import time
import cv2
from typing import Optional, Tuple

from .calibration_solver import CalibrationSolver
from .aruco_detector import ArucoDetector
from .visualisation import CalibrationVisualizer

class CalibrationManager:
    """Manages the calibration process and hardware interactions"""
    def __init__(self, camera_manager, mocap_stream, dyna_controller):
        self.logger = logging.getLogger("CalibrationManager")
        self.camera = camera_manager
        self.mocap = mocap_stream
        self.dyna = dyna_controller
        
        self.aruco = ArucoDetector(marker_size=0.04)
        self.solver = CalibrationSolver()
        self.visualizer = CalibrationVisualizer()
        
        # Calibration data storage
        self.aruco_pose = None  # (R, t)
        self.mocap_pose = None  # (R, t)
        self.mirror_data = []
        self.l_shape_markers = None
        
        # Results storage
        self.rotation = None
        self.translation = None
        self.mirror_center = None

    def capture_initial_poses(self) -> bool:
        """Capture the initial static poses of ArUco and mocap markers"""
        # First capture L-shape markers
        if len(self.mocap.markers) < 3:
            return False
            
        # Get L-shape marker positions
        self.l_shape_markers = np.array([(m.x, m.y, m.z) for m in self.mocap.markers[:3]])
        
        # Get mocap pose from L-shape
        mocap_pos = self.l_shape_markers
        long_axis = mocap_pos[1] - mocap_pos[0]
        short_axis = mocap_pos[2] - mocap_pos[0]
        
        # Compute orthonormal basis
        x_axis = long_axis / np.linalg.norm(long_axis)
        z_axis = np.cross(long_axis, short_axis)
        z_axis = z_axis / np.linalg.norm(z_axis)
        y_axis = np.cross(z_axis, x_axis)
        
        R_mocap = np.column_stack([x_axis, y_axis, z_axis])
        t_mocap = (mocap_pos[0] + mocap_pos[1]) / 2  # Center of long edge
        self.mocap_pose = (R_mocap, t_mocap)
        
        # Get ArUco pose
        ret, frame = self.camera.cap.read()
        if not ret:
            return False
            
        success, rvec, tvec, _, _ = self.aruco.process_frame(frame)
        if not success:
            return False
            
        R_aruco, _ = cv2.Rodrigues(rvec)
        tvec_mm = tvec * 1000  # Convert to millimeters
        self.aruco_pose = (R_aruco, tvec_mm)
        
        # Compute transformation immediately
        return self.compute_calibration()

    def collect_mirror_point(self, tilt_angle: float) -> bool:
        """Collect a single mirror calibration point"""
        if self.l_shape_markers is None or self.rotation is None:
            self.logger.error("Initial poses not captured yet")
            return False
            
        ret, frame = self.camera.cap.read()
        if not ret:
            return False
            
        success, rvec, tvec, _, _ = self.aruco.process_frame(frame)
        if not success:
            return False
            
        # Get camera position and direction in camera space
        R_cam, _ = cv2.Rodrigues(rvec)
        camera_pos = -R_cam.T @ tvec * 1000  # Convert to mm
        camera_dir = R_cam[:, 2]  # Unit vector
        
        # Debug logging to verify calculations
        self.logger.debug(f"Raw tvec (m): {tvec}")
        self.logger.debug(f"Camera pos (mm): {camera_pos}")
        self.logger.debug(f"Camera dir: {camera_dir}")
        
        # Transform to mocap space
        ray_origin = self.transform_to_mocap(camera_pos.flatten())
        ray_direction = self.transform_to_mocap(camera_dir.flatten(), vector=True)
        self.logger.debug(f"Mocap space ray origin: {ray_origin}")
        self.logger.debug(f"Mocap space ray direction: {ray_direction}")
        
        self.mirror_data.append({
            'tilt_angle': tilt_angle,
            'ray_origin': ray_origin,
            'ray_direction': ray_direction,
            'mocap_pos': self.l_shape_markers
        })
        return True

    def compute_calibration(self) -> bool:
        """Compute camera-mocap transformation"""
        try:
            self.rotation, self.translation = self.solver.compute_camera_mocap_transform(
                [self.aruco_pose], [self.mocap_pose])
            return True
        except Exception as e:
            self.logger.error(f"Calibration computation failed: {e}")
            return False

    def compute_mirror_center(self) -> Optional[Tuple[np.ndarray, float]]:
        """Compute mirror center as closest point to all rays"""
        try:
            center, error = self.solver.compute_mirror_center(self.mirror_data)
            self.mirror_center = center
            
            # Create visualization
            self.visualizer.visualize_calibration(
                mirror_data=self.mirror_data,
                mirror_center=center,
                save_html='calibration_visualization.html'
            )
            
            return center, error
        except Exception as e:
            self.logger.error(f"Mirror center computation failed: {e}")
            return None

    def transform_to_mocap(self, points_camera: np.ndarray, vector: bool = False) -> np.ndarray:
        """
        Transform points from camera to mocap space
        Args:
            points_camera: Points in camera space
            vector: If True, only apply rotation (for directions)
        """
        if self.rotation is None or self.translation is None:
            raise ValueError("Transformation not computed yet")
            
        points_camera = np.array(points_camera)
        if points_camera.ndim == 1:
            points_camera = points_camera.reshape(1, -1)
            
        transformed = (self.rotation @ points_camera.T).T
        if not vector:
            transformed = transformed + self.translation
            
        return transformed.squeeze()

    def save_calibration(self, filename: str = 'calibration_results.npz'):
        """Save calibration results"""
        if (self.rotation is None or 
            self.translation is None or 
            self.mirror_center is None):
            raise ValueError("Calibration not complete")
        
        np.savez(filename,
                mirror_center=self.mirror_center,
                mocap_rotation=self.rotation,
                mocap_translation=self.translation)
        self.logger.info(f"Calibration saved to {filename}") 