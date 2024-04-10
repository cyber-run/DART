import numpy as np
import cv2
import glob
import os

# Parameters
capture_folder = "calibration_images"
chessboard_size = (7, 6)
save_img_key = 32  # Space bar to capture the image
exit_key = 27  # ESC key to exit the capture mode and start calibration

if not os.path.exists(capture_folder):
    os.makedirs(capture_folder)

# Capture images for calibration
cap = cv2.VideoCapture(0)

img_counter = 0
print("Press SPACE to capture the image or ESC to exit...")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break
    cv2.imshow("Calibration Image Capture", frame)

    k = cv2.waitKey(1)
    if k == exit_key:
        print("Exiting image capture mode...")
        break
    elif k == save_img_key:
        img_name = os.path.join(capture_folder, f"calibration_{img_counter}.png")
        cv2.imwrite(img_name, frame)
        print(f"{img_name} saved!")
        img_counter += 1

cap.release()
cv2.destroyAllWindows()

# Calibration process
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)

objpoints = []
imgpoints = []

images = glob.glob(f'{capture_folder}/*.png')

for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)

    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)

# Calibrate the camera
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

# Save the camera matrix and the distortion coefficients
np.savez('calibration_data.npz', mtx=mtx, dist=dist, rvecs=rvecs, tvecs=tvecs)

print("Calibration is complete. The camera matrix and distortion coefficients are saved.")
