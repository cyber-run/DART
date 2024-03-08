from threading import Thread
from scipy.io import savemat
import logging
import asyncio
import math
import qtm

# System imports
import os
import psutil


class MoCap(Thread):

    def __init__(self, qtm_ip="192.168.100.1", stream_type='6d'):
        """
        Constructs QtmWrapper object.

        Args:\n
        `qtm_ip` IP of QTM instance, but doesn't seem to matter\n
        `stream_type` Specify components to receive,
        see: https://github.com/qualisys/qualisys_python_sdk/tree/afce59ea6be47974029d476960d960c05009ef60
        """

        Thread.__init__(self)

        # QTM Connection vars
        self.qtm_ip = qtm_ip
        self.stream_type = stream_type
        self._connection = None
        self._stay_open = True

        # Kinematic data vars
        self.state = [0, 0, 0, 0, 0, 0]
        self.position = [0,0,0]
        self.position2 = [0,0,0]
        self.matrix = None
        self.yaw = 0
        self.pitch = 0
        self.lost = False
        self.calibration_target = False

        self.start()

    def run(self) -> None:
        """
        Run QTM wrapper coroutine.
        """
        asyncio.run(self._life_cycle())

    async def _life_cycle(self) -> None:
        """
        QTM wrapper coroutine.
        """
        await self._connect()
        while(self._stay_open):
            await asyncio.sleep(1)
        await self._close()

    async def _connect(self) -> None:
        """
        Connect to QTM machine.
        """
        # Establish connection
        logging.info('[QTM] Connecting to QTM at %s', self.qtm_ip)
        self._connection = await qtm.connect(self.qtm_ip)

        if self.stream_type == '6d':
            # Register index of body for 6D tracking
            params_xml = await self._connection.get_parameters(parameters=['6d'])

            # Assign 6D streaming callback
            await self._connection.stream_frames(components=['6d'], on_packet=self._on_packet)

        if self.stream_type == '3d':
            # Register index of body for 6D tracking
            params_xml = await self._connection.get_parameters(parameters=['3d'])

            # Assign 6D streaming callback
            await self._connection.stream_frames(components=["3dnolabels"], on_packet=self._on_packet)

    def _on_packet(self, packet) -> None:
        """
        Process 6D packet stream into Pose object and pass on.
        Parameters
        ----------
        packet : QRTPacket
            Incoming packet from QTM
        """
        if self.stream_type == '6d':
            # Extract new 6D component from packet
            header, new_component = packet.get_6d()

            # If no new component: mark as lost and return from function
            if not new_component:
                logging.warning('[QTM] 6DoF rigid body not found.')
                self.lost = True
                return

            pos, mat = new_component[0]
            self.position = [pos.x, pos.y, pos.z]
            self.matrix = [mat.matrix[0:3], mat.matrix[3:6], mat.matrix[6:9]]

            self.lost = False

        elif self.stream_type == '3d': 
            # Extract new unlabelled 3d component from packet
            header, new_component = packet.get_3d_markers_no_label()

            # If no new component: mark as lost and return from function
            if not new_component:
                logging.warning('[QTM] 3D Unlabelled marker not found.')
                self.lost = True
                return

            pos = new_component[0]
            self.position = [pos.x, pos.y, pos.z]

            # Ensure there is more than one component before accessing it
            if self.calibration_target and len(new_component) > 1:
                pos = new_component[1]
                self.position2 = [pos.x, pos.y, pos.z]
            else:
                logging.info('Calibration target is set but only one marker detected.')

        self.lost = False

    async def _close(self) -> None:
        """
        End lifecycle by disconnecting from QTM machine.
        """
        await self._connection.stream_frames_stop()
        self._connection.disconnect()

    def close(self) -> None:
        """
        Stop QTM wrapper thread.
        """
        self._stay_open = False
        self.join()


def set_realtime_priority():
    try:
        p = psutil.Process(os.getpid())
        if psutil.WINDOWS:
            p.nice(psutil.REALTIME_PRIORITY_CLASS)
        elif psutil.LINUX or psutil.MACOS:
            # Set a high priority; be cautious with setting it to -20 (maximum priority)
            p.nice(-10)  # Modify this value as needed
        else:
            print("Platform not supported for priority setting.")
    except Exception as e:
        print(f"Error setting priority: {e}")


class DataLogger:
    def __init__(self):
        self.velocity = []
        self.timeStamp = []
        self.ref = []

    def log(self, data):
        self.velocity.append(data[0])
        self.timeStamp.append(data[2])
        self.ref.append(data[3])

    def save_file(self, file_path='data.mat'):
        mdic = {'height': self.height, 'velocity': self.velocity, 'time_stamp': self.timeStamp, 'estimate_height': self.ref}
        savemat(file_path, mdic)


if __name__ == '__main__':
    target = MoCap(stream_type='3d')
    tracker = MoCap(stream_type='6d')