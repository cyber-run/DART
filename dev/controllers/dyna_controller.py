import threading, time, math, logging, cProfile
from utils.misc_funcs import set_realtime_priority
from typing import Dict, Tuple
from dynamixel_sdk import *
import numpy as np


class DynaController:
    def __init__(self, com_port: str = 'COM5', baud_rate: int = 4000000) -> None:
        # EEPROM addresses for X-series:
        self.X_TORQUE_ENABLE = 64       # Torque enable
        self.X_OP_MODE = 11             # Operating mode
        self.X_VEL_LIM = 44             # Velocity limit
        self.X_SET_VEL = 104            # Set velocity
        self.X_SET_POS = 116            # Set position
        self.X_GET_VEL = 128            # Get velocity
        self.X_GET_POS = 132            # Get position
        self.X_SET_CURRENT = 102         # Set torque
        self.X_GET_CURRENT = 126         # Get torque
        self.X_SET_PWM = 100            # Set PWM
        self.X_P_GAIN = 84              # P gain
        self.X_D_GAIN = 80              # D gain
        self.X_FF_2_GAIN = 88           # Feedforward 2 gain
        self.I_GAIN = 82                # I gain

        # Protocol version : # X-series uses protocol version 2.0
        self.PROTOCOL_VERSION = 2.0

        # Dynamixel motors IDs (crossref with wizard)
        self.pan_id = int(1)
        self.tilt_id = int(2)

        # COM and U2D2 params
        self.baud = baud_rate
        self.com = com_port

        self.read_positions_flag = True
        self.lock = threading.Lock()

        self.port_handler = PortHandler(self.com)
        self.packet_handler = PacketHandler(self.PROTOCOL_VERSION)

        # Initialize GroupSyncWrite instance
        self.pos_sync_write = GroupSyncWrite(self.port_handler, self.packet_handler, self.X_SET_POS, 4)
        # Prepare empty byte array for initial parameter storage
        empty_byte_array = [0, 0, 0, 0]
        # Add initial parameters for pan and tilt motors
        for motor_id in [self.pan_id, self.tilt_id]:
            self.pos_sync_write.addParam(motor_id, empty_byte_array)

        # Initialize GroupSyncRead instance for position data
        self.pos_sync_read = GroupSyncRead(self.port_handler, self.packet_handler, self.X_GET_POS, 4)
        # Add parameters (motor IDs) to sync read
        for motor_id in [self.pan_id, self.tilt_id]:
            dxl_addparam_result = self.pos_sync_read.addParam(motor_id)
            if dxl_addparam_result != True:
                logging.error("[ID:%03d] groupSyncRead addparam failed" % motor_id)
                quit()

        # Initialize GroupSyncWrite instance
        self.pwm_sync_write = GroupSyncWrite(self.port_handler, self.packet_handler, self.X_SET_PWM, 2)
        # Prepare empty byte array for initial parameter storage
        empty_byte_array = [0, 0]
        # Add initial parameters for pan and tilt motors
        for motor_id in [self.pan_id, self.tilt_id]:
            self.pwm_sync_write.addParam(motor_id, empty_byte_array)

        # Open port
        # self.open_port()

        # Init motor rotations to normal forward gaze
        # self.set_sync_pos(225, 315)

    def open_port(self) -> bool:
        '''
        Open serial port for communication with servo.
        
        Returns:
        - bool: True if port opened successfully, False otherwise.'''

        try:
            if self.port_handler.openPort():
                logging.info("Succeeded to open the port")
            else:
                logging.error("Failed to open the port")
                return False

            if self.port_handler.setBaudRate(self.baud):
                logging.info("Succeeded to change the baudrate")
            else:
                logging.error("Failed to change the baudrate")
                return False
            return True
        except Exception as e:
            print(f"Error opening port: {e}")
            return False

    def set_sync_current(self, pan_current: int, tilt_current: int) -> None:
        """
        Synchronously set the current for the pan and tilt motors.

        Parameters:
        - pan_current (int): The current value to set for the pan motor.
        - tilt_current (int): The current value to set for the tilt motor.
        """
        # Initialize GroupSyncWrite instance for current
        current_sync_write = GroupSyncWrite(self.port_handler, self.packet_handler, self.X_SET_CURRENT, 2)
        
        # Convert current values into byte arrays
        pan_current_bytes = [DXL_LOBYTE(pan_current), DXL_HIBYTE(pan_current)]
        tilt_current_bytes = [DXL_LOBYTE(tilt_current), DXL_HIBYTE(tilt_current)]
        
        # Add parameter for pan and tilt motors
        current_sync_write.addParam(self.pan_id, pan_current_bytes)
        current_sync_write.addParam(self.tilt_id, tilt_current_bytes)
        
        # Execute sync write
        dxl_comm_result = current_sync_write.txPacket()
        if dxl_comm_result != COMM_SUCCESS:
            logging.error(f"Failed to set sync current: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        
        # Clear sync write parameter storage
        current_sync_write.clearParam()

    def get_sync_current(self) -> Tuple[int, int]:
        """
        Synchronously get the current for the pan and tilt motors.

        Returns:
        - Tuple[int, int]: The current values of the pan and tilt motors.
        """
        # Initialize GroupSyncRead instance for current
        current_sync_read = GroupSyncRead(self.port_handler, self.packet_handler, self.X_GET_CURRENT, 2)
        
        # Add motor IDs to sync read
        current_sync_read.addParam(self.pan_id)
        current_sync_read.addParam(self.tilt_id)
        
        # Execute sync read
        dxl_comm_result = current_sync_read.txRxPacket()
        if dxl_comm_result != COMM_SUCCESS:
            logging.error(f"Failed to get sync current: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
            return (-1, -1)  # Indicate an error

        # Retrieve the data
        pan_current = current_sync_read.getData(self.pan_id, self.X_GET_CURRENT, 2)
        tilt_current = current_sync_read.getData(self.tilt_id, self.X_GET_CURRENT, 2)

        # Convert from 2 bytes to integers
        pan_current_value = DXL_MAKEWORD(pan_current[0], pan_current[1]) if pan_current is not None else -1
        tilt_current_value = DXL_MAKEWORD(tilt_current[0], tilt_current[1]) if tilt_current is not None else -1

        # Clear sync read parameter storage
        current_sync_read.clearParam()
        
        return (pan_current_value, tilt_current_value)
    
    def set_pos(self, motor_id: int = 1, pos: float = 180) -> None:
        '''
        Set servo position in degrees for a specified motor.

        Parameters:
        - motor_id (int): ID of the motor.
        - pos (float): Desired position in degrees.
        '''
        # Convert from degrees to encoder position
        pos = int(pos * 4095 / 360)
        logging.debug(f"Setting motor {motor_id} position to {pos} ticks")
        # Write to servo
        self.write4ByteData(motor_id, self.X_SET_POS, pos)

    def set_sync_pos(self, pan_pos: float = 180, tilt_pos: float = 180) -> None:
        '''
        Set servo position synchronously for both motors.
        
        Parameters:
        - pan_pos (float): Desired pan position in degrees.
        - tilt_pos (float): Desired tilt position in degrees.
        '''
        # Convert from degrees to encoder position
        pan_pos = int(pan_pos * 4095 / 360)
        tilt_pos = int(tilt_pos * 4095 / 360)

        # Allocate goal positions value into byte array
        pan_byte_array = [DXL_LOBYTE(DXL_LOWORD(pan_pos)), DXL_HIBYTE(DXL_LOWORD(pan_pos)), DXL_LOBYTE(DXL_HIWORD(pan_pos)), DXL_HIBYTE(DXL_HIWORD(pan_pos))]
        tilt_byte_array = [DXL_LOBYTE(DXL_LOWORD(tilt_pos)), DXL_HIBYTE(DXL_LOWORD(tilt_pos)), DXL_LOBYTE(DXL_HIWORD(tilt_pos)), DXL_HIBYTE(DXL_HIWORD(tilt_pos))]

        # Change the parameters in the syncwrite storage
        self.pos_sync_write.changeParam(self.pan_id, pan_byte_array)
        self.pos_sync_write.changeParam(self.tilt_id, tilt_byte_array)

        # Syncwrite goal position
        self.pos_sync_write.txPacket()

    def set_sync_pwm(self, pan_pwm: float = 0, tilt_pwm: float = 0) -> None:
        '''
        Set servo position synchronously for both motors.
        
        Parameters:
        - pan_pwm (float): Desired pan pwm %
        - tilt_pwm (float): Desired tilt pwm %.
        '''

        # Allocate goal positions value into byte array
        pan_byte_array = [DXL_LOBYTE(DXL_LOWORD(pan_pwm)), DXL_HIBYTE(DXL_LOWORD(pan_pwm))]
        tilt_byte_array = [DXL_LOBYTE(DXL_LOWORD(tilt_pwm)), DXL_HIBYTE(DXL_LOWORD(tilt_pwm))]

        # Change the parameters in the syncwrite storage
        self.pwm_sync_write.changeParam(self.pan_id, pan_byte_array)
        self.pwm_sync_write.changeParam(self.tilt_id, tilt_byte_array)

        # Syncwrite goal position
        self.pwm_sync_write.txPacket()

    def get_pos(self, motor_id: int = 1) -> float:
        '''
        Retrieve the current position of a specified motor in degrees.

        Parameters:
        - motor_id (int): ID of the motor.

        Returns:
        - float: Current position in degrees.
        '''
        # Retrieve current encoder position as unsigned 32-bit integer
        pos = self.read4ByteData(motor_id, self.X_GET_POS)
        if pos is None:
            return None
        # Convert to degrees
        pos = round(360 * (pos / 4095), 3)
        return pos
    
    def get_sync_pos(self) -> Tuple[float, float]:
        '''
        Get synchronous positions of the pan and tilt motors using fast sync read method.

        Returns:
        - Tuple[float, float]: Current positions of the pan and tilt motors in degrees.
        '''
        # Perform sync read
        dxl_comm_result = self.pos_sync_read.txRxPacket()
        if dxl_comm_result != COMM_SUCCESS:
            logging.error(self.packet_handler.getTxRxResult(dxl_comm_result))

        # Retrieve the data
        pan_pos = self.pos_sync_read.getData(self.pan_id, self.X_GET_POS, 4)
        tilt_pos = self.pos_sync_read.getData(self.tilt_id, self.X_GET_POS, 4)

        # Convert from ticks to degrees
        pan_pos_deg = self.convert_ticks_to_degrees(pan_pos)
        tilt_pos_deg = self.convert_ticks_to_degrees(tilt_pos)

        return pan_pos_deg, tilt_pos_deg

    def set_vel(self, motor_id: int = 1, vel: float = 0) -> None:
        '''
        Set servo velocity for a specified motor in degrees per second.

        Parameters:
        - motor_id (int): ID of the motor.
        - vel (float): Desired velocity in degrees per second.
        '''
        # Convert from degrees per second to encoder velocity
        vel = int(vel * 41.7)
        # Write to servo
        self.write4ByteData(motor_id, self.X_SET_VEL, vel)

    def get_vel(self, motor_id: int = 1) -> float:
        '''
        Retrieve the current velocity of a specified motor in degrees per second.

        Parameters:
        - motor_id (int): ID of the motor.

        Returns:
        - float: Current velocity in degrees per second.
        '''
        # Retrieve current encoder velocity as unsigned 32-bit integer
        vel = self.read4ByteData(motor_id, self.X_GET_VEL)
        if vel is None:
            return None
        # Convert to degrees per second
        vel = vel / 41.7
        return vel

    def set_torque(self, motor_id: int = 1, torque: bool = False) -> None:
        '''
        Enable/disable servo torque.

        Parameters:
        - torque (bool): True to enable torque, False to disable.
        '''
        self.write1ByteData(motor_id, self.X_TORQUE_ENABLE, int(torque))

        check = self.read1ByteData(motor_id, self.X_TORQUE_ENABLE)

        if check == int(torque):
            return True
        else:
            return False

    def get_torque(self, motor_id: int = 1) -> bool:
        '''
        Get current torque status.

        Returns:
        - bool: True if torque is enabled, False otherwise.
        '''
        torque = self.read1ByteData(motor_id, self.X_TORQUE_ENABLE)

        if torque == 1:
            return True
        else:
            return False

    def set_op_mode(self, motor_id: int = 1, mode: int = 3) -> bool:
        '''
        Set servo operating mode.

        Parameters:
        - mode (int): Operating mode to set: 3 => position control, 1 => velocity control, 0 => torque control.
        '''
        # Disable torque to set operating mode
        self.set_torque(motor_id, False)

        # Set the operating mode
        self.write1ByteData(motor_id, self.X_OP_MODE, mode)

        # Verify that the operating mode was set correctly
        check = self.read1ByteData(motor_id, self.X_OP_MODE)

        # Re-enable torque
        self.set_torque(motor_id, True)

        # Return True if the operating mode was set correctly, False otherwise
        if check == mode:
            return True
        else:
            return False

    def get_op_mode(self, motor_id: int = 1) -> int:
        '''
        Get current operating mode.

        Returns:
        - int: Current operating mode. 3 => position control, 1 => velocity control.
        '''
        op_mode = self.read1ByteData(motor_id, self.X_OP_MODE)

        return op_mode

    def set_gains(self, motor_id: int = 1, p_gain: int = 800, i_gain: int = 0, d_gain: int = 0, ff_2_gain: int = 0) -> None:
        '''
        Set servo motor gains.

        Parameters:
        - motor_id (int): ID of the motor.
        - p_gain (int): Proportional gain.
        - i_gain (int): Integral gain.
        - d_gain (int): Derivative gain.
        - ff_2_gain (int): Feedforward 2 gain.
        '''
        self.write2ByteData(motor_id, self.X_P_GAIN, p_gain)
        self.write2ByteData(motor_id, self.X_D_GAIN, d_gain)
        self.write2ByteData(motor_id, self.I_GAIN, i_gain)
        self.write2ByteData(motor_id, self.X_FF_2_GAIN, ff_2_gain)

    def get_gains(self, motor_id: int = 1) -> Dict[str, int]:
        '''
        Get current motor gains.

        Parameters:
        - motor_id (int): ID of the motor.

        Returns:
        - Dict[str, int]: Dictionary containing the current PID gains.
        '''
        p_gain = self.read2ByteData(motor_id, self.X_P_GAIN)
        i_gain = self.read2ByteData(motor_id, self.I_GAIN)
        d_gain = self.read2ByteData(motor_id, self.X_D_GAIN)
        ff_2_gain = self.read2ByteData(motor_id, self.X_FF_2_GAIN)

        gains = {
            "p_gain": p_gain,
            "d_gain": d_gain,
            "ff_2_gain": ff_2_gain
        }

        return gains
        
    def write1ByteData(self, motor_id, address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(self.port_handler, motor_id, address, value)
        if dxl_comm_result != COMM_SUCCESS:
            logging.debug(self.packet_handler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            logging.error(self.packet_handler.getRxPacketError(dxl_error))

    def write2ByteData(self, motor_id, address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, address, value)
        if dxl_comm_result != COMM_SUCCESS:
            logging.debug(self.packet_handler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            logging.error(self.packet_handler.getRxPacketError(dxl_error))

    def write4ByteData(self, motor_id, address, value):
        dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(self.port_handler, motor_id, address, value)
        if dxl_comm_result != COMM_SUCCESS:
            logging.debug(self.packet_handler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            logging.error(self.packet_handler.getRxPacketError(dxl_error))

    def read1ByteData(self, motor_id, address):
        dxl_data, dxl_comm_result, dxl_error = self.packet_handler.read1ByteTxRx(self.port_handler, motor_id, address)
        if dxl_comm_result != COMM_SUCCESS:
            logging.debug(self.packet_handler.getTxRxResult(dxl_comm_result))
            return None
        elif dxl_error != 0:
            logging.error(self.packet_handler.getRxPacketError(dxl_error))
            return None
        else:
            return dxl_data

    def read2ByteData(self, motor_id, address):
        dxl_data, dxl_comm_result, dxl_error = self.packet_handler.read2ByteTxRx(self.port_handler, motor_id, address)
        if dxl_comm_result != COMM_SUCCESS:
            logging.debug(self.packet_handler.getTxRxResult(dxl_comm_result))
            return None
        elif dxl_error != 0:
            logging.error(self.packet_handler.getRxPacketError(dxl_error))
            return None
        else:
            return dxl_data

    def read4ByteData(self, motor_id, address):
        dxl_data, dxl_comm_result, dxl_error = self.packet_handler.read4ByteTxRx(self.port_handler, motor_id, address)
        if dxl_comm_result != COMM_SUCCESS:
            logging.debug(self.packet_handler.getTxRxResult(dxl_comm_result))
            return None
        elif dxl_error != 0:
            logging.error(self.packet_handler.getRxPacketError(dxl_error))
            return None
        else:
            return dxl_data
        
    @staticmethod
    def convert_ticks_to_degrees(ticks: int) -> float:
        return 360 * (ticks / 4095)

    @staticmethod
    def to_signed32(n):
        n = n & 0xffffffff
        return (n ^ 0x80000000) - 0x80000000

    def start_position_reading(self, interval=0.5):
        self.read_positions_thread = threading.Thread(target=self._read_positions, args=(interval,))
        self.read_positions_thread.start()

    def stop_position_reading(self):
        with self.lock:
            self.read_positions_flag = False
        self.read_positions_thread.join()

    def _read_positions(self, interval):
        pan_positions = []
        tilt_positions = []
        while self.read_positions_flag:
            with self.lock:
                pan_pos, tilt_pos = self.get_sync_pos()
            pan_positions.append(pan_pos)
            tilt_positions.append(tilt_pos)
            time.sleep(interval)
        self.save_positions(pan_positions, tilt_positions, "position_data.npz")

    def save_positions(self, pan_positions, tilt_positions, filename):
        pan_positions_array = np.array(pan_positions)
        tilt_positions_array = np.array(tilt_positions)
        np.savez(filename, pan_positions=pan_positions_array, tilt_positions=tilt_positions_array)

    def set_sync_pos_with_lock(self, pan_pos: float = 180, tilt_pos: float = 180) -> None:
        with self.lock:
            self.set_sync_pos(pan_pos, tilt_pos)

    def close_port(self):
        # Disable torque for both motors
        self.set_torque(self.pan_id, False)
        self.set_torque(self.tilt_id, False)

        # Close port
        self.port_handler.closePort()

def get_pwm_bode():
    set_realtime_priority()

    dyna = DynaController()
    dyna.open_port()

    dyna.set_op_mode(dyna.pan_id, 0)
    dyna.set_op_mode(dyna.tilt_id, 0)

    # dyna.set_gains(dyna.pan_id, 650, 1300, 1200)
    # dyna.set_gains(dyna.tilt_id, 1400, 500, 900)

    print(dyna.get_gains(dyna.pan_id))
    print(dyna.get_gains(dyna.tilt_id))

    # Set the frequency range for the Bode plot
    start_freq = 0.2
    end_freq = 5
    num_points = 20

    frequencies = np.round(np.logspace(np.log10(start_freq), np.log10(end_freq), num_points), num_points)

    for frequency in frequencies:
            # Center tracking servo to begin
            # Starting delay
            print(f"Frequency: {frequency} Hz")
            curr_d_list = []
            pan_pos_list = []
            tilt_pos_list = []
            time_list = []

            dyna.set_sync_current(16, 16)

            dyna.set_op_mode(dyna.pan_id, 3)
            dyna.set_op_mode(dyna.tilt_id, 3)
            dyna.set_sync_pos(225, 315)
            time.sleep(0.3)

            dyna.set_op_mode(dyna.pan_id, 16)
            dyna.set_op_mode(dyna.tilt_id, 16)

            time.sleep(1/2)

            # Collect data for 8 periods
            # duration = 8 * (1 / frequency)
            start_time = time.perf_counter()

            if frequency < 10:
                duration = 10
            else:
                duration = 2

            while time.perf_counter() - start_time < duration:
                curr_d = (math.sin(2 * math.pi * frequency * (time.perf_counter() - start_time))) * 400
                dyna.set_sync_pwm(int(curr_d), int(curr_d))
                pan_pos, tilt_pos = dyna.get_sync_pos()

                time_list.append(time.perf_counter() - start_time)
                curr_d_list.append(int(curr_d))
                pan_pos_list.append(pan_pos)
                tilt_pos_list.append(tilt_pos)

            # Save data for analysis
            data_filename = f'data/data_{frequency}Hz'
            np.savez(data_filename, time_list,curr_d_list, pan_pos_list, tilt_pos_list)
            time.sleep(1)
            dyna.set_sync_current(0, 0)

def get_theta_bode():
    set_realtime_priority()

    dyna = DynaController()
    dyna.open_port()

    dyna.set_op_mode(dyna.pan_id, 3)
    dyna.set_op_mode(dyna.tilt_id, 3)

    dyna.set_gains(dyna.pan_id, 2432, 720, 3200, 0)
    dyna.set_gains(dyna.tilt_id, 2432, 720, 3200, 0)

    print(dyna.get_gains(dyna.pan_id))
    print(dyna.get_gains(dyna.tilt_id))

    # Set the frequency range for the Bode plot
    start_freq = 0.2
    end_freq = 5
    num_points = 20

    frequencies = np.round(np.logspace(np.log10(start_freq), np.log10(end_freq), num_points), num_points)

    for frequency in frequencies:
            # Center tracking servo to begin
            # Starting delay
            print(f"Frequency: {frequency} Hz")
            theta_d_list = []
            pan_pos_list = []
            tilt_pos_list = []
            time_list = []

            dyna.set_sync_pos(225, 315)
            time.sleep(0.3)

            time.sleep(1/2)

            # Collect data for 8 periods
            # duration = 8 * (1 / frequency)
            start_time = time.perf_counter()

            if frequency < 10:
                duration = 10
            else:
                duration = 2

            while time.perf_counter() - start_time < duration:
                theta_d = (math.sin(2 * math.pi * frequency * (time.perf_counter() - start_time))) * 30
                dyna.set_sync_pos(225 + theta_d, 315 + theta_d)
                pan_pos, tilt_pos = dyna.get_sync_pos()

                time_list.append(time.perf_counter() - start_time)
                theta_d_list.append(int(theta_d))
                pan_pos_list.append(pan_pos)
                tilt_pos_list.append(tilt_pos)

            # Save data for analysis
            data_filename = f'data/data_{frequency}Hz'
            np.savez(data_filename, time_list, theta_d_list, pan_pos_list, tilt_pos_list)
            time.sleep(1)

def main():
    dyna = DynaController()
    dyna.open_port()

    dyna.set_op_mode(dyna.pan_id, 3)
    dyna.set_op_mode(dyna.tilt_id, 3)

    # Start position reading
    dyna.start_position_reading()

    # Oscillate the pan and tilt motors
    start_time = time.perf_counter()
    direction = 1
    while time.perf_counter() - start_time < 10:
        pan_pos = 225 + direction * 30 * math.sin(2 * math.pi * (time.perf_counter() - start_time))
        tilt_pos = 315 + direction * 30 * math.sin(2 * math.pi * (time.perf_counter() - start_time))
        dyna.set_sync_pos(pan_pos, tilt_pos)
        time.sleep(0.01)

    dyna.stop_position_reading()

    # Stop position reading and save the data to a file
    dyna.stop_position_reading()

def main2():
    dyna = DynaController()
    dyna.open_port()

    dyna.set_op_mode(dyna.pan_id, 1)
    dyna.set_op_mode(dyna.tilt_id, 1)

    dyna.set_vel(dyna.pan_id, 5)
    dyna.set_vel(dyna.tilt_id, 5)

    dyna.set_torque(dyna.pan_id, False)
    dyna.set_torque(dyna.tilt_id, False)

if __name__ == "__main__":
    # main()
    get_theta_bode()
    # get_pwm_bode()