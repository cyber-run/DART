import os, pickle, logging, math
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Tuple
import numpy as np

class Calibrator:
    def __init__(self):
        self.positions = []
        self.rotation_matrix = None
        self.pan_origin = None
        self.calibration_step = 0
        self.calibrated = False
        self.calibration_age = None

        # Load calibration data if it exists
        calib_data_path = 'dev/config/calib_data.pkl'
        if os.path.exists(calib_data_path):
            with open(calib_data_path, 'rb') as f:
                self.pan_origin, self.tilt_origin, self.rotation_matrix, self.date_time = pickle.load(f)
                self.calibrated = True
                self.calibration_age = (datetime.now() - self.date_time).total_seconds() / 3600
                logging.info("Calibration data loaded successfully.")
                print(f"Local origin: {self.pan_origin}")
        else:
            logging.info("No calibration data found.")


    def run(self, p1: np.ndarray, p2: np.ndarray):
        self.positions.append(p1)
        self.positions.append(p2)

        print(f"Step: {self.calibration_step} ----> Positions recorded: {p1}, {p2}")

        self.calibration_step = 1

        if len(self.positions) < 6:
            print("More points needed for calibration.")
            return
        else:
            self.calibrate(*self.positions[:6])
            self.positions = []  # Reset positions after calibration
            self.calibrated = True
            self.calibration_step = 0
            print("Calibration completed.")

    def calibrate(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray, p5: np.ndarray, p6: np.ndarray):
        x1, x2 = self.find_closest_points(p1, p2, p3, p4)
        self.pan_origin = self.calculate_midpoint(x1, x2)

        x3, x4 = self.find_closest_points(p1, p2, p5, p6)
        self.tilt_origin = self.calculate_midpoint(x3, x4)

        vec1 = (p1 + p2) / 2 - self.pan_origin
        vec2 = (p3 + p4) / 2 - self.pan_origin

        vec1_normalized = vec1 / np.linalg.norm(vec1)
        vec2_normalized = vec2 / np.linalg.norm(vec2)

        # Ensure the third vector is orthogonal to the first two
        x_axis = vec1_normalized
        z_axis = np.cross(vec1_normalized, vec2_normalized)  # Cross product to find orthogonal vector
        z_axis = z_axis / np.linalg.norm(z_axis)  # Normalize
        y_axis = np.cross(x_axis, z_axis)  # Recompute to ensure orthogonality

        self.rotation_matrix = np.column_stack((x_axis, y_axis, z_axis))

        time_stamp = datetime.now()

        os.makedirs('config', exist_ok=True)  # Ensure the config directory exists
        with open('dev/config/calib_data.pkl', 'wb') as f:
            pickle.dump((self.pan_origin, self.tilt_origin, self.rotation_matrix, time_stamp), f)
            logging.info("Calibration data saved successfully.")

    def find_closest_points(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        d1 = p2 - p1
        d2 = p4 - p3
        n = np.cross(d1, d2)

        if np.allclose(n, 0):
            raise ValueError("Lines are parallel")
        

        A = np.array([d1, -d2, n]).T
        b = p3 - p1
        t, s, _ = np.linalg.solve(A, b)

        closest_point_on_line1 = p1 + t * d1
        closest_point_on_line2 = p3 + s * d2

        return closest_point_on_line1, closest_point_on_line2

    def calculate_midpoint(self, point1: np.ndarray, point2: np.ndarray) -> np.ndarray:
        return (point1 + point2) / 2

    def global_to_local(self, point_global: np.ndarray) -> np.ndarray:
        if self.rotation_matrix is None:
            raise ValueError("Calibration must be completed before transforming points.")
        return np.dot(np.linalg.inv(self.rotation_matrix), point_global - self.pan_origin)

    def calc_rot_comp(self, point_local: np.ndarray) -> Tuple[float, float]:
        pan_angle = math.degrees(math.atan2(point_local[1], point_local[0]))
        tilt_angle = math.degrees(math.atan2(point_local[2], math.sqrt(point_local[0]**2 + point_local[1]**2)))
        return pan_angle, tilt_angle

    def verify_orthogonality(self):
        if self.rotation_matrix is not None:
            # Check if the rotation matrix is orthogonal
            is_orthogonal = np.allclose(np.dot(self.rotation_matrix.T, self.rotation_matrix), np.eye(3))
            if not is_orthogonal:
                logging.warning("The rotation matrix is not orthogonal.")
            else:
                logging.info("The rotation matrix is orthogonal.")
        else:
            logging.info("Rotation matrix not set.")

    def plot_calibration(self, p1, p2, p3, p4):
        if self.rotation_matrix is None or self.pan_origin is None:
            logging.error("Calibration data not available.")
            return

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Plot axes of the rotation matrix from the intersection point
        axis_length = 1.0  # Adjust for better visualization
        for i, axis in enumerate(['X', 'Y', 'Z']):
            end_point = self.pan_origin + axis_length * self.rotation_matrix[:, i]
            ax.quiver(*self.pan_origin, *(self.rotation_matrix[:, i]), length=axis_length, label=f'{axis}-axis')

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.legend()
        plt.title('Calibration Axes')
        plt.show()

def main():
    calib = Calibrator()
    # Test find_closest_points function
    # Sample points for the lines
    p1 = np.random.uniform(-100, 100, size=(3,))
    p2 = np.random.uniform(-100, 100, size=(3,))
    calib.run(p1, p2)

    p3 = np.random.uniform(-100, 100, size=(3,))
    p4 = np.random.uniform(-100, 100, size=(3,))
    calib.run(p3,p4)
    print(f"Rotation Matrix: {calib.rotation_matrix}\n\nIntersection Point: {calib.local_origin}\n")

    point_global = np.array([1, 2, 3])
    point_local = calib.global_to_local(point_global)
    print(f"Local coordinates of {point_global}: {point_local}\n")

    # Test calc_rot_comp function
    pan_angle, tilt_angle = calib.calc_rot_comp(point_local)
    print(f"Pan angle: {pan_angle}, Tilt angle: {tilt_angle}\n")

    calib.verify_orthogonality()
    calib.plot_calibration(p1, p2, p3, p4)

if __name__ == "__main__":
    main()
