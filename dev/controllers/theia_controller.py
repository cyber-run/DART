import serial
import time
import queue
import logging


class TheiaController:
    '''
    Class for controlling the kurokesu lens controller for 1250N6 lens.
    '''
    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 5):
        # Initialise serial port
        self.ser = serial.Serial()
        self.ser.port = str(port)
        self.ser.baudrate = int(baudrate)
        self.ser.timeout = timeout

        self.temp = None
        self.zoom_pos = None
        self.focus_pos = None

        # Declare idle timer variables
        self.timer = None
        self.idle_timer = 0
        self.idle_timeout = 100

        # Declare queue for commands
        self.queue = queue.Queue()

        # Declare status variables
        self.status = None

        self.ZOOM_POS = 0
        self.ZOOM_PI = 3
        self.ZOOM_MOVE = 6

        self.FOCUS_POS = 1
        self.FOCUS_PI = 4
        self.FOCUS_MOVE = 7

        self.IRIS_POS = 2
        self.IRIS_PI = 5
        self.IRIS_MOVE = 8

        # Initialize logger
        self.logger = logging.getLogger("Theia")
        self.logger.setLevel(logging.INFO)

        # Check if the logger already has handlers
        if not self.logger.hasHandlers():
            # Create a console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)

            # Create a formatter and add it to the handlers
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)

            # Add the handlers to the logger
            self.logger.addHandler(ch)

    def connect(self):
        self.ser.open()
        self.ser.flushInput()
        self.ser.flushOutput()
        self.logger.info("Connected to serial port")

    def disconnect(self):
        self.ser.close()
        self.logger.info("Disconnected from serial port")

    def initialise(self):
        '''
        Initialise procedure for the lens controller.
        Presets some defined values and sets channels(axes) to default modes
        '''
        # Reset and initialize the controller
        self._ser_send('$B2')
        self.logger.info("Controller reset and initialized")

        # Timing register setup for microstepping DO NOT MODIFY
        self._ser_send("M243 A2")
        self._ser_send("M243 B2")
        self._ser_send("M243 C6")
        self.logger.info("Timing registers set for microstepping")

        # Set all channels to normal move
        self._ser_send('M230')
        self.logger.info("All channels set to normal move")

        # Set all channels to relative movement mode
        self._ser_send('G90')
        self.logger.info("All channels set to relative movement mode")

        # Energize PI leds
        self._ser_send("M238")
        self.logger.info("PI LEDs energized")

        # Set motor power
        self._ser_send("M234 A180 B180 C180 D90")
        self.logger.info("Motor power set")

        # set motor sleep power
        self._ser_send("M235 A50 B50 C90")
        self.logger.info("Motor sleep power set")

        # Set motor drive speed to initalised at 5000
        self._ser_send("M240 A5000 B5000 C5000")
        self.logger.info("Motor drive speed set to 5000")

        # Set PI low/high detection voltage
        self._ser_send("M232 A2000 B2000 C2000 E3000 F3000 G3000")
        self.logger.info("PI low/high detection voltage set")

    def read_status(self):
        status_str = self._ser_send("!1")
        self.status = self._parse_status(status_str)

        # Update zoom and focus positions
        self.zoom_pos = self.status[self.ZOOM_POS]
        self.focus_pos = self.status[self.FOCUS_POS]

        self.logger.info(f"Status read: {self.status}")
        return self.status
    
    def _wait_till_status_change(self, initial_status: int, axis: int, timeout: int = 10):
        # Start timer
        elapsed_time = 0
        start_time = time.time()

        # Run status check loop until status changes or timeout
        while elapsed_time < timeout:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            # Get new status from register
            self.read_status()

            # Check if the status list has enough elements
            if len(self.status) > axis:
                # Check if status has changed
                if initial_status != self.status[axis]:
                    self.logger.info(f"Status changed for axis {axis} after {elapsed_time:.2f} seconds")
                    return elapsed_time
            else:
                self.logger.warning(f"Insufficient status elements for axis {axis}")

            # Wait for approx 10ms before checking again
            time.sleep(0.01)

        self.logger.warning(f"Timeout waiting for status change for axis {axis}")
        return -1
    
    def move_axis(self, channel: str, distance: int):
        '''
        Move the specified channel by the specified distance\n
        `Args:`\n
        channel (str) The channel to move (A, B, C)\n
        distance (int) The distance to move (positive or negative)\n
        `return:`\n
        The status of the controller
        '''
        self._ser_send(f"G0 {channel}{distance}")
        self.logger.info(f"Moving axis {channel} by {distance} steps")
        self.read_status()

        if channel == "A" and len(self.status) > self.ZOOM_POS:
            return self.status[self.ZOOM_POS]
        elif channel == "B" and len(self.status) > self.FOCUS_POS:
            return self.status[self.FOCUS_POS]
        elif channel == "C" and len(self.status) > self.IRIS_POS:
            return self.status[self.IRIS_POS]
        else:
            self.logger.warning(f"Invalid channel or insufficient status elements for channel {channel}")
            return None
    
    def home_zoom(self):
        '''
        Home the zoom channel
        '''
        # Set relative movement mode and move forward 5000 steps
        self._ser_send("G91")
        self.set_motion_mode("A", "normal")
        self.move_axis("A", 5000)
        self._wait_till_status_change(1, self.ZOOM_MOVE)
        self.logger.info("Zoom axis moved forward 5000 steps")

        # Read status and move backward till PI changes
        self.read_status()
        self.set_motion_mode("A", "forced")
        self.move_axis("A", -100)
        self._wait_till_status_change(self.status[self.ZOOM_PI], self.ZOOM_PI)
        self.logger.info("Zoom axis homed")
        
        # Setup lens params now it is homed
        self._ser_send("M230 A")    # Set channel A to normal move
        self._ser_send("G92 A0")    # Set current position to 0
        self._ser_send("G90")       # Set absolute movement mode
        self.logger.info("Zoom axis setup completed after homing")
    
    def home_focus(self):
        '''
        Home the focus channel
        '''
        # Set relative movement mode and move backward 5000 steps
        self._ser_send("G91")
        self.set_motion_mode("B", "normal")
        self.move_axis("B", -5000)
        self._wait_till_status_change(1, self.FOCUS_MOVE)
        self.logger.info("Focus axis moved backward 5000 steps")

        self.read_status()
        self.set_motion_mode("B", "forced")
        self.move_axis("B", 100)
        self._wait_till_status_change(self.status[self.FOCUS_PI], self.FOCUS_PI)
        self.logger.info("Focus axis homed")

        # Setup lens params for final homing adjustment
        self._ser_send("M230 B")    # Set channel A to normal move
        self._ser_send("G92 B0")    # Set current position to 0

        # Set lens to relative movement and adjust back to near limit to set to 0
        self._ser_send("G91")
        self.move_axis("B", -64000)
        self._wait_till_status_change(1, self.FOCUS_MOVE)

        self.move_axis("B", -64000)
        self._wait_till_status_change(1, self.FOCUS_MOVE)

        self.move_axis("B", -5000)
        self._wait_till_status_change(1, self.FOCUS_MOVE)
        self.logger.info("Focus axis adjusted to near limit")

        self._ser_send("G92 B0")    # Set current position to 0
        self._ser_send("G90")       # Set absolute movement mode
        self.logger.info("Focus axis setup completed after homing")
        
    def set_motion_mode(self, channel: str, mode: str):
        if channel not in ["A", "B", "C"]:
            raise ValueError("Invalid channel")

        if mode == "normal":
            self._ser_send(f"M230 {channel}")
            self.logger.info(f"Motion mode for channel {channel} set to normal")
        elif mode == "forced":
            self._ser_send(f"M231 {channel}")
            self.logger.info(f"Motion mode for channel {channel} set to forced")
        else:
            raise ValueError("Invalid mode")

    def set_leds(self, mode):
        if mode is True:
            self._ser_send("M238")
            self.logger.info("LEDs turned on")
        if mode is False:
            self._ser_send("M239")
            self.logger.info("LEDs turned off")

    def stop(self):
        # Set all axis to 0
        self.move_axis("A", 0)
        self._wait_till_status_change(1, self.ZOOM_MOVE)

        self.move_axis("B", 0)
        self._wait_till_status_change(1, self.FOCUS_MOVE)

        self.disconnect()
        self.logger.info("Stopped and disconnected")
    
    def _ser_send(self, command: str):
        self.ser.write(bytes(command + '\r\n', 'utf8'))
        r = self.ser.readline().decode("utf-8").strip()
        self.logger.debug(f"Serial command sent: {command}, response: {r}")
        return r

    def _parse_status(self, status_string: str):
        temp = status_string.split(",")
        ret = [int(t.strip()) for t in temp]
        return ret
    
if __name__ == "__main__":
    # Create an instance of TheiaController
    controller = TheiaController(port="COM17")

    try:
        # Connect to the controller
        controller.connect()

        # Initialize the controller
        controller.initialise()

        # Home the zoom axis
        controller.home_zoom()

        # Home the focus axis
        controller.home_focus()

        # Move zoom axis forward by 24000
        # controller.move_axis("A", 24000)
        # controller._wait_till_status_change(1, controller.ZOOM_MOVE)

        controller.read_status()

    except Exception as e:
        controller.logger.exception("An error occurred:")

    finally:
        # Stop and disconnect the controller
        controller.stop()