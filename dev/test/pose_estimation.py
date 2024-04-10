import cv2
import cv2.aruco as aruco
import numpy as np

with np.load('calibration_data.npz') as X:
    mtx, dist = [X[i] for i in ('mtx', 'dist')]

def my_estimatePoseSingleMarkers(corners, marker_size, mtx, distortion):
    '''
    This will estimate the rvec and tvec for each of the marker corners detected by:
       corners, ids, rejectedImgPoints = detector.detectMarkers(image)
    corners - is an array of detected corners for each detected marker in the image
    marker_size - is the size of the detected markers
    mtx - is the camera matrix
    distortion - is the camera distortion matrix
    RETURN list of rvecs, tvecs, and trash (so that it corresponds to the old estimatePoseSingleMarkers())
    '''
    marker_points = np.array([[-marker_size / 2, marker_size / 2, 0],
                              [marker_size / 2, marker_size / 2, 0],
                              [marker_size / 2, -marker_size / 2, 0],
                              [-marker_size / 2, -marker_size / 2, 0]], dtype=np.float32)
    trash = []
    rvecs = []
    tvecs = []
    
    for c in corners:
        nada, R, t = cv2.solvePnP(marker_points, c, mtx, distortion, False, cv2.SOLVEPNP_IPPE_SQUARE)
        rvecs.append(R)
        tvecs.append(t)
        trash.append(nada)
    return rvecs, tvecs, trash

def detect_aruco_and_estimate_pose(frame, mtx, dist):
    """
    Detects ArUco markers in the given frame and estimates their pose.

    Args:
    - frame: The image frame from the camera.
    - mtx: The camera matrix from calibration.
    - dist: The distortion coefficients from calibration.

    Returns:
    - The modified frame with the marker detected and axis drawn.
    - The translation vectors, indicating the marker positions.
    """
    # Define dictionary and parameters for ArUco detection
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_250)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(dictionary, parameters)
    
    # Detect the markers in the image
    markerCorners, markerIds, rejectedCandidates = detector.detectMarkers(frame, mtx, dist)
    
    if markerIds is not None:
        # Estimate pose of each marker (assuming a marker size of 0.05 meters)
        rvecs, tvecs, _objPoints = my_estimatePoseSingleMarkers(markerCorners, 0.05, mtx, dist)
        
        for rvec, tvec in zip(rvecs, tvecs):
            # Draw the detected marker and its axis
            aruco.drawDetectedMarkers(frame, markerCorners, markerIds)
            cv2.drawFrameAxes(frame, mtx, dist, rvec, tvec, 0.03)  # Length of the axis in meters
        
        return frame, tvecs
    else:
        return frame, None


cap = cv2.VideoCapture(0)  # Adjust the device index as needed

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame, tvecs = detect_aruco_and_estimate_pose(frame, mtx, dist)
    
    if tvecs is not None:
        for tvec in tvecs:
            distance = np.linalg.norm(tvec)
            print(f"Distance to marker: {distance:.2f} meters")

    cv2.imshow('Frame', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
        break

cap.release()
cv2.destroyAllWindows()
