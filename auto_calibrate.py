import logging
import time
import cv2
from pathlib import Path
import sys
import numpy as np

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))
from tracking.calibration_manager import CalibrationManager
from hardware.camera.camera_manager import CameraManager
from hardware.mocap.qtm_mocap import QTMStream
from hardware.motion.dyna_controller import DynaController

def run_calibration():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("CalibrationTest")
    
    try:
        # Initialize hardware
        camera = CameraManager(1)
        time.sleep(2)
        
        mocap = QTMStream()
        
        dyna = DynaController('COM5')
        if not dyna.open_port():
            logger.error("Failed to open Dynamixel port")
            return
            
        # Set initial motor configurations
        dyna.set_op_mode(dyna.pan_id, 3)
        dyna.set_op_mode(dyna.tilt_id, 3)
        dyna.set_torque(dyna.pan_id, True)
        dyna.set_torque(dyna.tilt_id, True)

        # Set tilt to default center position
        dyna.set_pos(dyna.tilt_id, 26.4)
        
        # Create calibration manager
        cal_manager = CalibrationManager(camera, mocap, dyna)
        
        # First, capture the initial poses
        logger.info("Capturing initial poses...")
        if not cal_manager.capture_initial_poses():
            logger.error("Failed to capture initial poses")
            return
            
        # Now compute the transformation
        if not cal_manager.compute_calibration():
            logger.error("Failed to compute transformation")
            return
        
        # Perform mirror scan
        logger.info("Starting mirror scan...")
        
        # Try to get current position, if fails use default center position
        current_tilt = None
        retry_count = 0
        while current_tilt is None and retry_count < 5:
            current_tilt = dyna.get_pos(dyna.tilt_id)
            retry_count += 1
            time.sleep(0.5)
        
        if current_tilt is None:
            logger.error("Could not read current position, using default center position")
            current_tilt = 26.4  # Default center position
            
            # Move to center position
            for _ in range(5):  # Try up to 5 times
                dyna.set_pos(dyna.tilt_id, current_tilt)
                time.sleep(1.0)  # Longer wait for initial positioning
                if dyna.get_pos(dyna.tilt_id) is not None:
                    break
        
        # Set scan range
        start_angle = current_tilt - 2
        end_angle = current_tilt + 2
        step_size = 0.1
        
        logger.info(f"Scanning from {start_angle:.1f}° to {end_angle:.1f}° in {step_size:.2f}° steps")
        
        for angle in np.arange(start_angle, end_angle + step_size, step_size):
            # Keep trying to set position until it succeeds
            retry_count = 0
            while retry_count < 10:  # Limit retries to avoid infinite loop
                dyna.set_pos(dyna.tilt_id, angle)
                time.sleep(0.5)  # Wait for motor movement and settling
                
                actual_pos = dyna.get_pos(dyna.tilt_id)
                if actual_pos is not None:
                    logger.info(f"Motor moved to {actual_pos:.2f}°")
                    if abs(actual_pos - angle) > 0.1:  # 0.1° tolerance
                        logger.error(f"Position error: requested={angle:.2f}°, actual={actual_pos:.2f}°")
                    break
                    
                retry_count += 1
                time.sleep(0.1)
            
            if retry_count >= 10:
                logger.error(f"Failed to verify position at {angle:.2f}°, continuing anyway")
            
            # Collect mirror point
            retry_count = 0
            while not cal_manager.collect_mirror_point(angle) and retry_count < 10:
                retry_count += 1
                time.sleep(0.1)
                
            if retry_count < 10:
                logger.info(f"Collected mirror point at {angle:.2f}°")
            else:
                logger.error(f"Failed to collect mirror point at {angle:.2f}°")
        
        # Before computing mirror center
        logger.info(f"Collected {len(cal_manager.mirror_data)} mirror points")

        # Compute mirror center
        result = cal_manager.compute_mirror_center()
        if result is not None:
            center, error = result
            logger.info(f"Mirror center found at {center} with error {error:.2f}mm")
            logger.debug(f"Mirror data points: {len(cal_manager.mirror_data)}")
            cal_manager.save_calibration()
            logger.info("Calibration saved successfully")
            
            # Get ArUco origin in mocap space (center of long edge)
            aruco_origin = (cal_manager.l_shape_markers[0] + cal_manager.l_shape_markers[1]) / 2
            
            logger.info(f"ArUco origin (mocap space): {aruco_origin}")
            logger.info(f"Mirror center (mocap space): {center}")
            
            # Compute relative position
            relative_pos = center - aruco_origin
            logger.info(f"Mirror center relative to ArUco: {relative_pos}")
            
            # Expected relationships
            logger.info("Validation checks:")
            logger.info(f"Mirror center above ArUco? {center[2] > aruco_origin[2]}")
            logger.info(f"Distance from ArUco to mirror: {np.linalg.norm(relative_pos):.1f}mm")
        
    finally:
        cv2.destroyAllWindows()
        if 'camera' in locals():
            camera.release()
        if 'mocap' in locals():
            mocap.close()
        if 'dyna' in locals():
            dyna.set_torque(dyna.pan_id, False)
            dyna.set_torque(dyna.tilt_id, False)
            dyna.close_port()

if __name__ == "__main__":
    run_calibration() 