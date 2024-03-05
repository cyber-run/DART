import cv2
import time
import EasyPySpin
 
capture = EasyPySpin.VideoCapture(0)
fps_x = capture.get(cv2.CAP_PROP_FPS)
time.sleep(3)
ret, frame = capture.read()

# Correct fourcc code for MacOS and correct frame size
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
videoWriter = cv2.VideoWriter('test/video.mp4', fourcc, fps_x, (frame.shape[1], frame.shape[0]))
 
while True:
    ret, frame = capture.read()
     
    if ret:
        cv2.imshow('video', frame)
        videoWriter.write(frame)
 
    if cv2.waitKey(1) == 27:
        break
 
capture.release()
videoWriter.release()
 
cv2.destroyAllWindows()