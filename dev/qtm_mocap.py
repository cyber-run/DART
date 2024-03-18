import logging, asyncio, qtm, time
from threading import Thread

class QTMStream(Thread):
    def __init__(self, qtm_ip="192.168.100.1"):
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
        self._connection = None
        self._stay_open = True

        # Kinematic data vars
        self.position = [0,0,0]
        self.position2 = [0,0,0]
        self.lost = False
        self.calibration_target = False
        self.num_markers = 0

        self.log_flag = None

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

        # Register index of body for 6D tracking
        params_xml = await self._connection.get_parameters(parameters=['3d'])

        # Assign 6D streaming callback
        await self._connection.stream_frames(components=["3dnolabels"], on_packet=self._on_packet)

    def _on_packet(self, packet) -> None:
        """
        Process a packet stream 6D or 3D data.
        ----------
        packet : QRTPacket
            Incoming packet from QTM
        """
        # Extract new unlabelled 3d component from packet
        _, new_component = packet.get_3d_markers_no_label()

        # If no new component: mark as lost and return from function
        if not new_component:
            if self.lost is False:
                logging.warning('[QTM] 3D Unlabelled marker not found.')

            self.lost = True
            return

        pos = new_component[0]
        self.position = [pos.x, pos.y, pos.z]
        self.num_markers = len(new_component)

        # Ensure there is more than one component before accessing it
        if self.calibration_target and len(new_component) > 1:
            pos = new_component[1]
            self.position2 = [pos.x, pos.y, pos.z]

            self.log_flag = True
        else:
            if self.log_flag is True:
                logging.info('Calibration target is set but only one marker detected.')

            self.log_flag = False

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


class QTMControl:
    def __init__(self, qtm_ip="192.168.100.1", password='password123'):
        # QTM Connection vars
        self.qtm_ip = qtm_ip
        self._connection = None
        self._stay_open = True
        self.password = password

    async def start(self):
        await self._connect()

    async def _connect(self) -> None:
        """
        Connect to QTM machine.
        """
        # Establish connection
        logging.info('[QTM] Connecting to QTM at %s', self.qtm_ip)
        self._connection = await qtm.connect(self.qtm_ip)

        # Take control of QTM
        await self.take_control(self.password)

    async def take_control(self, password):
        await self._connection.take_control(password)

    async def release_control(self):
        await self._connection.release_control()

    async def start_recording(self, rtfromfile=False):
        await self._connection.start(rtfromfile)

    async def stop_recording(self):
        await self._connection.stop()

    async def _close(self) -> None:
        """
        End lifecycle by disconnecting from QTM machine.
        """
        await self._connection.stream_frames_stop()
        self._connection.disconnect()

async def main():
    target = QTMControl()
    await target.start()

    await asyncio.sleep(5)

    try:
        # Start recording
        await target.start_recording()

        # Record for 10 seconds
        await asyncio.sleep(5)

        # Stop recording
        await target.stop_recording()

        # Wait for a short duration before saving the recording
        await asyncio.sleep(3)

        # Save the recording
        filename = "recording.qtm"
        overwrite = True
        await target._connection.save(filename, overwrite)

        # Release control of QTM
        await target.release_control()

    except qtm.QRTCommandException as e:
        logging.error(f"QTM command exception: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected exception: {str(e)}")
    finally:
        # Close the connections
        await target._close()


if __name__ == '__main__':
    target = QTMStream()
    asyncio.run(main()) 
    time.sleep(5)
    target.close()
