import cv2
import numpy as np
import logging
import time
import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, PathPatch
from matplotlib.path import Path

class CameraCalibrator:
    def __init__(self, camera_manager):
        self.logger = logging.getLogger("CameraCalibrator")
        self.camera = camera_manager
        
        # ChArUco board parameters - smaller size
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
        self.board_size = (4, 6)  # Slightly smaller board
        self.square_length = 0.03  # 30mm squares
        self.marker_length = 0.022  # 22mm markers
        
        # Create ChArUco board
        self.charuco_board = cv2.aruco.CharucoBoard(
            self.board_size, 
            self.square_length, 
            self.marker_length, 
            self.aruco_dict
        )
        
        # Initialize calibration data storage
        self.all_corners = []
        self.all_ids = []
        self.collected_frames = 0
        self.required_frames = 15  # Number of frames to collect
        
    def save_board_image(self, output_path="charuco_board.pdf"):
        """Save ChArUco board as high-quality PDF"""
        # Generate high-resolution board image
        board_img = self.charuco_board.generateImage((2000, 2000))
        
        # Convert to RGB for matplotlib
        board_img_rgb = cv2.cvtColor(board_img, cv2.COLOR_GRAY2RGB)
        
        # Create figure with exact size in inches
        width_inches = self.board_size[0] * self.square_length * 39.37
        height_inches = self.board_size[1] * self.square_length * 39.37
        
        fig = plt.figure(figsize=(width_inches, height_inches))
        ax = fig.add_subplot(111)
        
        # Remove axes and margins
        ax.set_axis_off()
        plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        plt.margins(0,0)
        
        # Display the board
        ax.imshow(board_img_rgb)
        
        # Add dimensions as text
        total_width_mm = self.board_size[0] * self.square_length * 1000
        total_height_mm = self.board_size[1] * self.square_length * 1000
        plt.figtext(0.5, 0.02, 
                    f'Total size: {total_width_mm:.1f}mm x {total_height_mm:.1f}mm\n'
                    f'Square size: {self.square_length*1000:.1f}mm\n'
                    f'Marker size: {self.marker_length*1000:.1f}mm', 
                    ha='center', va='center')
        
        # Save as PDF
        plt.savefig(output_path, format='pdf', bbox_inches='tight', 
                    pad_inches=0, dpi=1200)
        plt.close()
        
        self.logger.info(f"ChArUco board saved to {output_path}")
        
    def process_frame(self, frame):
        """Process a single frame for calibration"""
        detector = cv2.aruco.ArucoDetector(self.aruco_dict, cv2.aruco.DetectorParameters())
        charuco_detector = cv2.aruco.CharucoDetector(self.charuco_board)
        
        corners, ids, rejected = detector.detectMarkers(frame)
        
        if ids is not None:
            result = charuco_detector.detectBoard(frame)
            if result[0] is not None and len(result[0]) > 10:  # Reduced threshold to 10
                self.all_corners.append(result[0])
                self.all_ids.append(result[1])
                self.collected_frames += 1
                return True
                
        return False
        
    def calibrate(self):
        """Perform camera calibration with collected frames"""
        if self.collected_frames < 5:
            self.logger.error("Not enough frames collected for calibration")
            return None, None
        
        try:
            # Convert data format for calibration
            objpoints = []  # 3D points in real world space
            imgpoints = []  # 2D points in image plane
            
            for corners, ids in zip(self.all_corners, self.all_ids):
                # Create object points only for the detected corners
                num_corners = len(corners)
                
                # Create object points for each detected corner
                objp = np.zeros((num_corners, 3), np.float32)
                for i, corner_id in enumerate(ids):
                    row = corner_id // (self.board_size[0] - 1)
                    col = corner_id % (self.board_size[0] - 1)
                    objp[i] = np.array([col * self.square_length, 
                                      row * self.square_length, 
                                      0.0])
                
                objpoints.append(objp)
                imgpoints.append(corners)
            
            # Perform calibration using standard OpenCV calibration
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, self.camera.frame_size, None, None
            )
            
            if ret:
                self.logger.info("Camera calibration successful")
                return mtx, dist
            else:
                self.logger.error("Calibration failed")
                return None, None
                
        except Exception as e:
            self.logger.error(f"Calibration error: {e}")
            return None, None

    def validate_calibration(self, camera_matrix, dist_coeffs):
        """Validate calibration results"""
        if camera_matrix is None or dist_coeffs is None:
            return False
        
        # Check focal lengths are reasonable
        fx, fy = camera_matrix[0,0], camera_matrix[1,1]
        if fx <= 0 or fy <= 0:
            return False
        
        return True

def main():
    # Setup paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    sys.path.append(project_root)
    sys.path.append(os.path.join(project_root, 'src'))
    
    from src.hardware.camera.camera_manager import CameraManager
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("CameraCalibrator_Test")
    
    # Initialize camera
    camera = CameraManager(1)  # Adjust index if needed
    time.sleep(2)  # Wait for camera to initialize
    
    # Create calibrator
    calibrator = CameraCalibrator(camera)
    
    # Create display window
    cv2.namedWindow('Camera Calibration', cv2.WINDOW_NORMAL)
    
    try:
        logger.info("Starting automatic calibration. Hold the board in different positions.")
        logger.info("Collecting 60 frames with position variety checks...")
        
        last_capture_time = time.time()
        min_capture_interval = 1.0  # Back to 1 second interval
        position_buffer = []
        
        # Create detectors
        detector = cv2.aruco.ArucoDetector(calibrator.aruco_dict, cv2.aruco.DetectorParameters())
        charuco_detector = cv2.aruco.CharucoDetector(calibrator.charuco_board)
        
        while True:
            # Replace frame thread access with direct camera read
            ret, frame = camera.cap.read()
            if frame is None:
                time.sleep(0.1)
                continue
                
            # Convert frame to RGB for display
            display_frame = cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB)
            
            corners, ids, rejected = detector.detectMarkers(display_frame)
            
            current_time = time.time()
            ready_for_capture = (current_time - last_capture_time) >= min_capture_interval
            
            if ids is not None:
                cv2.aruco.drawDetectedMarkers(display_frame, corners, ids)
                
                try:
                    result = charuco_detector.detectBoard(frame)
                    if result[0] is not None:
                        charuco_corners = result[0]
                        charuco_ids = result[1]
                        
                        # Adjusted corner threshold to 10 (most of the corners)
                        if ready_for_capture and len(charuco_corners) > 10:
                            board_center = np.mean(charuco_corners, axis=0)
                            
                            is_new_position = True
                            for old_center in position_buffer:
                                if np.linalg.norm(board_center - old_center) < 30:
                                    is_new_position = False
                                    break
                            
                            if is_new_position or not position_buffer:
                                if calibrator.process_frame(frame):
                                    logger.info(f"Frame {calibrator.collected_frames} captured")
                                    last_capture_time = current_time
                                    position_buffer.append(board_center)
                                    if len(position_buffer) > 5:
                                        position_buffer.pop(0)
                        
                        # Draw detected corners
                        cv2.aruco.drawDetectedCornersCharuco(display_frame, charuco_corners, charuco_ids)
                        
                        # Add debug info - bright green color (0, 255, 0)
                        cv2.putText(display_frame, f"Corners: {len(charuco_corners)}", 
                                  (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                except Exception as e:
                    logger.debug(f"ChArUco detection error: {e}")
                    continue
            
            # Display info and guidance - bright green color
            cv2.putText(display_frame, f"Captured: {calibrator.collected_frames}/60", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if calibrator.collected_frames < 20:
                message = "Hold board flat, facing camera"
            elif calibrator.collected_frames < 40:
                message = "Tilt board left/right/up/down"
            else:
                message = "Move board closer/further"
            
            cv2.putText(display_frame, message, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow('Camera Calibration', display_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            # Check if we have enough frames (changed to 60)
            if calibrator.collected_frames >= 60:
                logger.info("Sufficient frames collected. Performing calibration...")
                camera_matrix, dist_coeffs = calibrator.calibrate()
                if camera_matrix is not None:
                    np.save('camera_matrix.npy', camera_matrix)
                    np.save('dist_coeffs.npy', dist_coeffs)
                    logger.info("Calibration saved to files")
                    break
                
    except KeyboardInterrupt:
        logger.info("Calibration interrupted by user")
        
    finally:
        camera.release()
        cv2.destroyAllWindows()
        logger.info("Calibration completed")

if __name__ == "__main__":
    main() 