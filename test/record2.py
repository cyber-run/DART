# import required libraries
import EasyPySpin
from vidgear.gears import WriteGear
import cv2

# Open live video stream on webcam at first index(i.e. 0) device
stream = EasyPySpin.VideoCapture(0)

# change with your webcam soundcard, plus add additional required FFmpeg parameters for your writer
output_params = {
    "-input_framerate": 200,
}

# Define writer with defined parameters and suitable output filename for e.g. `Output.mp4
writer = WriteGear(output="Output.mp4", logging=True, **output_params)

# loop over
while True:

    # read frames from stream
    _, frame = stream.read()

    # check for frame if Nonetype
    if frame is None:
        break

    # {do something with the frame here}

    # write frame to writer
    writer.write(frame)

    # Show output window
    cv2.imshow("Output Frame", frame)

    # check for 'q' key if pressed
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

# close output window
cv2.destroyAllWindows()

# safely close video stream
stream.stop()

# safely close writer
writer.close()
