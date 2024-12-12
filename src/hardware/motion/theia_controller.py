import serial
import time
import queue
import logging


class TheiaController:
    '''
    Class for controlling the kurokesu lens controller for 1250N6 lens.
    '''
    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 5):
        self.logger = logging.getLogger("Theia")
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
        self.logger.debug("Controller reset and initialized")

        # Timing register setup for microstepping DO NOT MODIFY
        self._ser_send("M243 A2")
        self._ser_send("M243 B2")
        self._ser_send("M243 C6")
        self.logger.debug("Timing registers set for microstepping")

        # Set all channels to normal move
        self._ser_send('M230')
        self.logger.debug("All channels set to normal move")

        # Set all channels to relative movement mode
        self._ser_send('G90')
        self.logger.debug("All channels set to relative movement mode")

        # Energize PI leds
        self._ser_send("M238")
        self.logger.debug("PI LEDs energized")

        # Set motor power
        self._ser_send("M234 A180 B180 C180 D90")
        self.logger.debug("Motor power set")

        # set motor sleep power
        self._ser_send("M235 A50 B50 C90")
        self.logger.debug("Motor sleep power set")

        # Set motor drive speed to initalised at 5000
        self._ser_send("M240 A5000 B5000 C2000")
        self.logger.debug("Motor drive speed set to 5000")

        # Set PI low/high detection voltage
        self._ser_send("M232 A2000 B2000 C2000 E3000 F3000 G3000")
        self.logger.debug("PI low/high detection voltage set")

    def read_status(self):
        status_str = self._ser_send("!1")
        self.status = self._parse_status(status_str)

        # Update zoom and focus positions
        self.zoom_pos = self.status[self.ZOOM_POS]
        self.focus_pos = self.status[self.FOCUS_POS]

        self.logger.debug(f"Status read: {self.status}")
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
            self.logger.debug("LEDs turned on")
        if mode is False:
            self._ser_send("M239")
            self.logger.debug("LEDs turned off")

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

    def set_absolute_position(self, channel: str, position: int):
        """Set the current position value for an axis
        Args:
            channel (str): The channel to set (A, B)
            position (int): The absolute position value
        """
        self._ser_send(f"G92 {channel}{position}")
        self.logger.info(f"Set {channel} axis position to {position}")

    def wait_for_motion_complete(self, timeout: int = 10) -> bool:
        """Wait for all motion to complete
        Returns:
            bool: True if motion completed, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.read_status()
            # Check motion flags (indices 6,7,8 in status)
            if not any(status[6:9]):  # If all motion flags are 0
                return True
            time.sleep(0.01)
        return False

    def get_current_positions(self):
        """Get current zoom and focus positions after ensuring motion is complete
        Returns:
            tuple[int, int]: (zoom_position, focus_position)
        """
        try:
            # First read to check motion flags
            status = self.read_status()
            
            # If any motion flags are set, wait for completion
            if any(status[6:9]):
                if not self.wait_for_motion_complete():
                    self.logger.warning("Timeout waiting for motion to complete")
                    return None, None
            
            # Read status again after motion is complete
            status = self.read_status()
            
            # Store positions
            zoom_pos = status[self.ZOOM_POS]
            focus_pos = status[self.FOCUS_POS]
            
            # Verify positions with a second read
            verify_status = self.read_status()
            if (verify_status[self.ZOOM_POS] != zoom_pos or 
                verify_status[self.FOCUS_POS] != focus_pos):
                self.logger.warning("Position values unstable between reads")
                return None, None
                
            self.logger.info(f"Verified positions - Zoom: {zoom_pos}, Focus: {focus_pos}")
            return zoom_pos, focus_pos
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return None, None
    
if __name__ == "__main__":
    import statistics
    import numpy as np
    from time import perf_counter_ns

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create an instance of TheiaController
    controller = TheiaController(port="/dev/cu.usbmodem48EF337A394D1")
    latencies = []
    n_samples = 100  # Number of measurements to take

    try:
        # Connect to the controller
        controller.connect()
        controller.initialise()
        
        # Measure command latency
        print("\nMeasuring serial command latency...")
        for i in range(n_samples):
            start_time = perf_counter_ns()
            controller._ser_send("!1")  # Status request command
            end_time = perf_counter_ns()
            
            latency_ms = (end_time - start_time) / 1e6  # Convert ns to ms
            latencies.append(latency_ms)
            
            if i % 10 == 0:  # Progress update every 10 samples
                print(f"Sample {i}/{n_samples}: {latency_ms:.2f}ms")
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        std_dev = statistics.stdev(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        p95_latency = np.percentile(latencies, 95)
        
        # Print results
        print("\nSerial Latency Statistics:")
        print(f"Average Latency: {avg_latency:.2f}ms")
        print(f"Standard Deviation: {std_dev:.2f}ms")
        print(f"Min Latency: {min_latency:.2f}ms")
        print(f"Max Latency: {max_latency:.2f}ms")
        print(f"95th Percentile: {p95_latency:.2f}ms")
        
        # Optional: Plot histogram
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            plt.hist(latencies, bins=30, edgecolor='black')
            plt.title('Serial Command Latency Distribution')
            plt.xlabel('Latency (ms)')
            plt.ylabel('Frequency')
            plt.axvline(avg_latency, color='r', linestyle='dashed', linewidth=2, label=f'Mean ({avg_latency:.2f}ms)')
            plt.axvline(p95_latency, color='g', linestyle='dashed', linewidth=2, label=f'95th Percentile ({p95_latency:.2f}ms)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.show()
            
        except ImportError:
            print("\nMatplotlib not available for plotting.")

    except Exception as e:
        controller.logger.exception("An error occurred:")

    finally:
        # Stop and disconnect the controller
        controller.stop()