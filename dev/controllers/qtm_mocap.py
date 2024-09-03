import logging, asyncio, qtm, time
from threading import Thread
import tkinter as tk
from tkinter import ttk
import threading


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
            await asyncio.sleep(0.5)
        await self._close()

    async def _connect(self) -> None:
        """
        Connect to QTM machine.
        """
        # Establish connection
        logging.info('[QTM] Connecting to QTM at %s', self.qtm_ip)
        self._connection = await qtm.connect(self.qtm_ip)

        # Register index of body for 3D tracking
        _ = await self._connection.get_parameters(parameters=['3d'])

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
            if not self.lost:
                logging.warning('[QTM] 3D Unlabelled marker not found.')
                self.lost = True
            return

        pos = new_component[0]
        self.position = [pos.x, pos.y, pos.z]
        self.num_markers = len(new_component)

        # Ensure there is more than one component before accessing it
        if self.calibration_target:
            if len(new_component) > 1:
                pos = new_component[1]
                self.position2 = [pos.x, pos.y, pos.z]
                if self.lost:
                    logging.info('Calibration target detected with two markers.')
                    self.lost = False
            elif not self.lost:
                logging.info('Calibration target is set but only one marker detected.')
                self.lost = True
        elif self.lost:
            logging.info('Calibration target detected with one marker.')
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


class QTMControl(Thread):
    def __init__(self, qtm_ip: str = "192.168.100.1", password: str = 'password123'):
        super().__init__()
        self.qtm_ip = qtm_ip
        self.password = password
        self._connection = None
        self._stay_open = True

        self.start()

    def run(self) -> None:
        """
        Start the asynchronous event loop and run the connection lifecycle.
        """
        asyncio.run(self._life_cycle())

    async def _life_cycle(self) -> None:
        """
        Handle the lifecycle of the QTM control connection.
        """
        await self._connect()
        while self._stay_open:
            await asyncio.sleep(1)  # Adjust sleep time as needed
        await self._close()

    async def _connect(self) -> None:
        """
        Connect to QTM machine and take control.
        """
        logging.info('[QTM] Connecting to QTM at %s', self.qtm_ip)
        self._connection = await qtm.connect(self.qtm_ip)
        await self.take_control(self.password)

    async def take_control(self, password: str) -> None:
        """
        Take control of the QTM system.
        """
        await self._connection.take_control(password)

    async def release_control(self) -> None:
        """
        Release control of the QTM system.
        """
        await self._connection.release_control()

    async def set_qtm_event(self, event: str) -> None:
        """
        Set an event in the QTM system.
        """
        await self._connection.set_qtm_event(event)

    async def start_recording(self, rtfromfile: bool = False) -> None:
        """
        Start recording in the QTM system.
        """
        await self._connection.start(rtfromfile=rtfromfile)

    async def stop_recording(self) -> None:
        """
        Stop recording in the QTM system.
        """
        await self._connection.stop()

    async def _close(self) -> None:
        """
        Close the QTM control connection gracefully.
        """
        await self.release_control()
        if self._connection:
            self._connection.disconnect()

    def close(self) -> None:
        """
        Close the QTM control connection.
        """
        self._stay_open = False
        self.join()

class TkinterAsyncioBridge:
    def __init__(self, loop):
        self.loop = loop
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)

    def start(self):
        self.thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

    def run_coroutine(self, coro):
        asyncio.run_coroutine_threadsafe(coro, self.loop)

def start_recording():
    global control
    bridge.run_coroutine(control.start_recording())

def stop_recording():
    global control
    bridge.run_coroutine(control.stop_recording())

def set_qtm_event(event_str: str='Paused'):
    global control, bridge
    bridge.run_coroutine(control.set_qtm_event(event_str))

def close_app():
    # Schedule the control's close coroutine in the asyncio event loop
    control.close()

    # Stop the bridge's event loop
    bridge.stop()

    # Destroy the Tkinter root window, ensuring it's done from the main thread
    root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    root.title("QTM Control")

    #  asyncio.get_event_loop().set_debug(True)
    loop = asyncio.get_event_loop()
    
    control = QTMControl()  # Assuming this is modified to not start automatically
    bridge = TkinterAsyncioBridge(root)
    bridge.start()

    start_button = ttk.Button(root, text="Start Recording", command=start_recording)
    start_button.pack(pady=10)

    stop_button = ttk.Button(root, text="Stop Recording", command=stop_recording)
    stop_button.pack(pady=10)

    pause_button = ttk.Button(root, text="Pause Recording", command=lambda: set_qtm_event('Paused'))
    pause_button.pack(pady=10)

    root.protocol("WM_DELETE_WINDOW", close_app)

    root.mainloop()