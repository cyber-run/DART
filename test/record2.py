# import required libraries
import EasyPySpin
from vidgear.gears import WriteGear
import cv2, time
 
# Open live video stream on webcam at first index(i.e. 0) device
stream = EasyPySpin.VideoCapture(0)
 
# change with your webcam soundcard, plus add additional required FFmpeg parameters for your writer
output_params = {
    "-input_framerate": 200,
    "-r" : 200,
    "-preset": "ultrafast",
    "-crf": 24
}
 
# Define writer with defined parameters and suitable output filename for e.g. `Output.mp4
writer = WriteGear(output="Output.mp4", logging=True, **output_params)
 
# loop over
while True:
 
    # read frames from stream
    _, frame = stream.read()
 
    # Convert ndarray to cv2.imshow compatible format
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
 
    # check for frame if Nonetype
    if frame is None:
        break
 
    # {do something with the frame here}
 
    # write frame to writer
    writer.write(frame)
    start_t = time.perf_counter()
    # Show output window
    cv2.imshow("Output Frame", frame)
 
    # check for 'q' key if pressed
    key = cv2.waitKey(1) & 0xFF
    if time.perf_counter() - start_t > 10:
        break
 
# close output window
cv2.destroyAllWindows()
 
# safely close video stream
stream.release()
 
# safely close writer
writer.close()