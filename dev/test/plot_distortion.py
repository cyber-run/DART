import numpy as np
import matplotlib.pyplot as plt

def plot_distortion_coefficients(dist: np.ndarray):
    """
    Plot the radial distortion coefficients from the camera calibration.

    Args:
    - dist: The distortion coefficients array returned by cv2.calibrateCamera.
            Expected to contain at least two values.
    """
    k1, k2 = dist[0][0], dist[0][1]
    r = np.linspace(0, 1, 100)  # Normalized distance from the center to the corner of the image
    distortion = k1 * r**2 + k2 * r**4  # Radial distortion model for demonstration
    
    plt.figure(figsize=(8, 4))
    plt.plot(r, distortion, label='Radial Distortion')
    plt.title('Camera Radial Distortion Plot')
    plt.xlabel('Normalized Radial Distance')
    plt.ylabel('Distortion (Normalized Units)')
    plt.grid(True)
    plt.legend()
    plt.show()


mtx, dist, _, _ = np.load('calibration_data.npz').values()
print(f"Distorion coefficients: {dist}")
plot_distortion_coefficients(dist)
