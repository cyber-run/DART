import numpy as np
import cv2

class ImageProcessor:
    def __init__(self):
        # Initialize default values for image processing
        self.threshold_value = 70
        self.strength_value = 60

        self.show_crosshair = False
        self.detect_circle_flag = False

    def process_frame(self, frame):
        """
        Process the given frame based on the specified flags.

        :param frame: The input frame to be processed.
        :param show_crosshair: Boolean flag to determine if a crosshair should be drawn.
        :param detect_circle: Boolean flag to determine if circles should be detected.
        :return: The processed frame.
        """
        # Convert to grayscale if needed
        if self.needs_grayscale():
            if len(frame.shape) == 3 and frame.shape[2] == 3:  # Check if the image has 3 channels
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect circles if the flag is set
        if self.detect_circle_flag:
            frame = self.detect_circle(frame)

        # Draw a crosshair if the flag is set
        if self.show_crosshair:
            frame = self.draw_crosshair(frame)

        return frame

    def needs_grayscale(self):
        """
        Check if the grayscale conversion is needed based on the current flags.

        :return: Boolean indicating if grayscale conversion is needed.
        """
        return self.detect_circle_flag

    def detect_circle(self, frame):
        """
        Detect and draw circles in the given frame.

        :param frame: The frame in which circles will be detected.
        :return: The frame with detected circles drawn.
        """
        try:
            blurred_frame = cv2.medianBlur(frame, 5)
            circles = cv2.HoughCircles(blurred_frame, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
                                       param1=self.threshold_value, param2=self.strength_value,
                                       minRadius=0, maxRadius=0)

            if circles is not None:
                circles = np.uint16(np.around(circles))
                for i in circles[0, :]:
                    cv2.circle(frame, (i[0], i[1]), i[2], (255, 0, 255), 2)  # Draw the circle outline
                    cv2.circle(frame, (i[0], i[1]), 1, (255, 0, 255), 3)  # Draw the circle center
        except Exception as e:
            print(f"Error in circle detection: {e}")

        return frame

    def draw_crosshair(self, frame):
        """
        Draw a crosshair on the given frame.

        :param frame: The frame on which the crosshair will be drawn.
        :return: The frame with a crosshair.
        """
        height, width = frame.shape[:2]
        cv2.line(frame, (width // 2, 0), (width // 2, height), (0, 255, 0), 2)
        cv2.line(frame, (0, height // 2), (width, height // 2), (0, 255, 0), 2)
        return frame
