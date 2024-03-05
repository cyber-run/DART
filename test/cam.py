import cv2
import EasyPySpin

cap = EasyPySpin.VideoCapture(0)
if not cap.isOpened():
    print("Camera could not be opened.")
else:
    ret, frame = cap.read()
    if ret:
        cv2.imshow("Test Frame", frame)
        cv2.waitKey(0)
    cap.release()
cv2.destroyAllWindows()
