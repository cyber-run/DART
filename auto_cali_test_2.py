import numpy as np
import cv2
import EasyPySpin
from dev.controllers.qtm_mocap import QTMStream
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import logging

# reload logging module
import importlib
importlib.reload(logging)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraPoseEstimator:
    def __init__(self, calibration_file):
        self.load_calibration(calibration_file)
        self.qtm_stream = QTMStream()
        self.roi = None
        self.fig = None
        self.ax = None
        self.camera_positions = []
        self.running_mean = np.zeros(3)
        self.previous_image_points = None
        self.previous_world_points = None

    def load_calibration(self, calibration_file):
        calibration_data = np.load(calibration_file)
        self.camera_matrix = calibration_data['mtx']
        self.dist_coeffs = calibration_data['dist']

    def plot_camera_pose(self, world_points, camera_to_world):
        if self.fig is None:
            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
        else:
            self.ax.clear()

        self.ax.scatter(world_points[:, 0], world_points[:, 1], world_points[:, 2], c='r', marker='o')

        camera_position = camera_to_world[:3, 3]
        camera_orientation = camera_to_world[:3, :3]

        self.ax.scatter(camera_position[0], camera_position[1], camera_position[2], c='b', marker='^')

        axis_length = 100
        for i in range(3):
            self.ax.quiver(camera_position[0], camera_position[1], camera_position[2],
                      camera_orientation[0, i], camera_orientation[1, i], camera_orientation[2, i],
                      length=axis_length, color=['r', 'g', 'b'][i])

        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_title('Camera Pose Visualization')
        self.ax.set_box_aspect((1, 1, 1))

        plt.draw()
        plt.pause(0.001)

    def analyze_roi(self, frame):
        x, y, w, h = self.roi
        roi_image = frame[y:y+h, x:x+w]
        mean_intensity = np.mean(roi_image)
        max_dimension = max(w, h)
        return mean_intensity, max_dimension

    def get_marker_coordinates(self):
        while self.qtm_stream.num_markers < 4:
            pass
        markers = self.qtm_stream.markers
        unordered_points = np.array([(m.x, m.y, m.z) for m in markers], dtype=np.float32)
        return self.order_points(unordered_points)

    def define_l_frame(self, markers):
        corner = markers[0]
        x_axis = markers[1] - corner
        y_axis = markers[3] - corner
        z_axis = np.cross(x_axis, y_axis)
        
        x_axis /= np.linalg.norm(x_axis)
        y_axis /= np.linalg.norm(y_axis)
        z_axis /= np.linalg.norm(z_axis)
        
        rotation_matrix = np.column_stack((x_axis, y_axis, z_axis))
        
        transformation_matrix = np.eye(4)
        transformation_matrix[:3, :3] = rotation_matrix
        transformation_matrix[:3, 3] = corner
        
        return transformation_matrix

    def update_running_mean(self, new_position):
        self.camera_positions.append(new_position)
        if len(self.camera_positions) > 100:  # Keep only the last 100 positions
            self.camera_positions.pop(0)
        self.running_mean = np.mean(self.camera_positions, axis=0)

    def world_to_camera_transform(self, world_points, image_points):
        # Ensure correct data types
        image_points = np.array(image_points, dtype=np.float32)
        world_points = np.array(world_points, dtype=np.float32)
        
        logger.debug(f"World points shape: {world_points.shape}, Image points shape: {image_points.shape}")
        if world_points.shape[0] != 4 or image_points.shape[0] != 4:
            logger.error(f"Invalid number of points. World points: {world_points.shape[0]}, Image points: {image_points.shape[0]}")
            return None

        try:
            # Log the input points
            logger.debug(f"World points: {world_points}")
            logger.debug(f"Image points: {image_points}")
            success, rotation_vector, translation_vector = cv2.solvePnP(
                world_points, image_points, self.camera_matrix, self.dist_coeffs, flags=cv2.SOLVEPNP_P3P)
            
            if not success:
                logger.error("Failed to solve PnP")
                return None

            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            
            transform = np.eye(4)
            transform[:3, :3] = rotation_matrix
            transform[:3, 3] = translation_vector.ravel()
            
            # Update the running mean with the new camera position
            self.update_running_mean(translation_vector.ravel())
            
            return transform
        except cv2.error as e:
            logger.error(f"OpenCV error in world_to_camera_transform: {e}")
            return None
    
    def order_points(self, points):
        # Convert to numpy array if not already
        points = np.array(points)
        
        # Log the input points
        logger.debug(f"Input points to order_points: {points}")
        
        # Calculate pairwise distances
        dist_matrix = np.linalg.norm(points[:, None] - points, axis=2)
        
        # Find the two points farthest apart (arm endpoints)
        arm_indices = np.unravel_index(np.argmax(dist_matrix), dist_matrix.shape)
        arm_points = points[list(arm_indices)]
        
        # The remaining two points
        other_indices = list(set(range(4)) - set(arm_indices))
        other_points = points[other_indices]
        
        # Calculate angles to determine which of the other points is the corner
        def angle_between(v1, v2):
            v1_u = v1 / np.linalg.norm(v1)
            v2_u = v2 / np.linalg.norm(v2)
            return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))

        vectors1 = [arm_points[0] - other_points[0], arm_points[1] - other_points[0]]
        angle1 = angle_between(vectors1[0], vectors1[1])
        
        vectors2 = [arm_points[0] - other_points[1], arm_points[1] - other_points[1]]
        angle2 = angle_between(vectors2[0], vectors2[1])
        
        if angle1 > angle2:
            corner = other_points[0]
            fourth = other_points[1]
        else:
            corner = other_points[1]
            fourth = other_points[0]
        
        # Determine which arm point is on the x-axis (closer to the fourth point)
        if np.linalg.norm(arm_points[0] - fourth) < np.linalg.norm(arm_points[1] - fourth):
            x_end, y_end = arm_points
        else:
            y_end, x_end = arm_points
        
        ordered_points = np.array([corner, x_end, fourth, y_end])
        
        # Log the output points
        logger.debug(f"Ordered points: {ordered_points}")
        
        return ordered_points

    def detect_markers(self, frame):
        mean_intensity, marker_size = self.analyze_roi(frame)
        
        lower_thresh = int(mean_intensity * 0.7)
        upper_thresh = int(mean_intensity * 3)
        
        expected_area = np.pi * (marker_size / 2) ** 2
        min_area = int(expected_area * 0.7)
        max_area = int(expected_area * 1.3)

        _, thresh_lower = cv2.threshold(frame, lower_thresh, 255, cv2.THRESH_BINARY)
        _, thresh_upper = cv2.threshold(frame, upper_thresh, 255, cv2.THRESH_BINARY)
        thresh = cv2.bitwise_xor(thresh_lower, thresh_upper)

        kernel_size = max(3, int(marker_size / 10))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        
        eroded = cv2.erode(thresh, kernel, iterations=5)
        dilated = cv2.dilate(eroded, kernel, iterations=5)
        final = cv2.erode(dilated, kernel, iterations=1)

        contours, _ = cv2.findContours(final, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        markers = []
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            if min_area < area < max_area and circularity > 0.55:
                M = cv2.moments(contour)
                if M['m00'] != 0:
                    cx, cy = int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])
                    markers.append((cx, cy))

        logger.debug(f"Detected {len(markers)} markers in this frame")

        if len(markers) == 4:
            return self.order_points(markers)
        else:
            return None

    def visualize_detection(self, frame, markers):
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        x, y, w, h = self.roi
        cv2.rectangle(frame_bgr, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        for marker in markers:
            cv2.circle(frame_bgr, tuple(marker.astype(int)), 5, (0, 0, 255), -1)

        scale_factor = 0.5
        frame_small = cv2.resize(frame_bgr, None, fx=scale_factor, fy=scale_factor)

        cv2.imshow('Marker Detection', frame_small)

    def run(self):
        cap = EasyPySpin.VideoCapture(1)
        
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to grab frame")
            return

        self.roi = cv2.selectROI("Select Marker ROI", frame)
        cv2.destroyWindow("Select Marker ROI")

        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to grab frame")
                break

            image_points = self.detect_markers(frame)
            if image_points is None or len(image_points) < 4:
                logger.warning("Failed to detect 4 markers in the image")
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

            world_points = self.get_marker_coordinates()
            if world_points is None or len(world_points) < 4:
                logger.warning("Failed to get 4 marker coordinates from QTM")
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

            logger.debug(f"Detected image points: {image_points}")
            logger.debug(f"Received world points: {world_points}")

            camera_to_world = self.world_to_camera_transform(world_points, image_points)
            if camera_to_world is None:
                logger.warning("Failed to compute camera to world transform")
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

            l_frame_to_world = self.define_l_frame(world_points)
            camera_to_l_frame = np.linalg.inv(l_frame_to_world) @ camera_to_world

            logger.info("Camera to L-frame transformation matrix:\n%s", camera_to_l_frame)

            logger.info("Running mean of camera position (mm): X: %.2f, Y: %.2f, Z: %.2f",
                        self.running_mean[0], self.running_mean[1], self.running_mean[2])

            self.plot_camera_pose(world_points, camera_to_world)
                        
            self.visualize_detection(frame, image_points)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        plt.close('all')

        try:
            self.qtm_stream.close()
        except Exception as e:
            logger.error("Failed to close QTM stream: %s", e)

if __name__ == "__main__":
    estimator = CameraPoseEstimator('calibration_data.npz')
    
    while True:
        try:
            # Get qtm coordinates and print
            print(estimator.get_marker_coordinates())
        except Exception as e:
            print(e)
            continue
        except KeyboardInterrupt:
            break
