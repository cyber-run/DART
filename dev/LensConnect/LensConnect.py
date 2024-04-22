import UsbCtrl
import LensCtrl
import ConfigVal as CV
import LensAccess as LA
import DefVal as DV
import cv2 as cv
import logging
import time

class LensController:
    def __init__(self):
        self.usbOpen_flag = False
        self.withZoom = False
        self.withFocus = False
        self.withIris = False

    def scan_devices(self):
        device_list = []
        retval, numDevice = UsbCtrl.UsbGetNumDevices()
        if numDevice >= 1:
            logging.info("No.: S/N")
            for i in range(0, numDevice):
                retval = UsbCtrl.UsbOpen(i)
                if retval == 0:
                    retval, SnString = UsbCtrl.UsbGetOpenedSnDevice(i)
                    retval, model = LensCtrl.ModelName()
                    retval, userName = LensCtrl.UserAreaRead()
                    logging.info("{:2d} : {} , {} {}".format(i, SnString, model, userName))
                    device_list.append(i)
                else:
                    logging.error("{:2d} : {:35s} {}".format(i, "Device access error.", "The device may already be running."))
                UsbCtrl.UsbClose()
        else:
            logging.info("No LensConnect is connected.")
        return device_list

    def connect(self, deviceNumber):
        retval = UsbCtrl.UsbOpen(deviceNumber)
        if retval != DV.RET_SUCCESS:
            print(retval)
            return retval

        retval = UsbCtrl.UsbSetConfig()
        if retval != DV.RET_SUCCESS:
            print(retval)
            return retval

        retval, capabilities = LensCtrl.CapabilitiesRead()
        LensCtrl.Status2ReadSet()

        if capabilities & CV.ZOOM_MASK:
            LensCtrl.ZoomParameterReadSet()
            if LensCtrl.status2 & CV.ZOOM_MASK == DV.INIT_COMPLETED:
                LensCtrl.ZoomCurrentAddrReadSet()
            self.withZoom = True

        if capabilities & CV.FOCUS_MASK:
            LensCtrl.FocusParameterReadSet()
            if LensCtrl.status2 & CV.FOCUS_MASK == DV.INIT_COMPLETED:
                LensCtrl.FocusCurrentAddrReadSet()
            self.withFocus = True

        if capabilities & CV.IRIS_MASK:
            LensCtrl.IrisParameterReadSet()
            if LensCtrl.status2 & CV.IRIS_MASK == DV.INIT_COMPLETED:
                LensCtrl.IrisCurrentAddrReadSet()
            self.withIris = True

        self.usbOpen_flag = True
        return DV.RET_SUCCESS

    def disconnect(self):
        UsbCtrl.UsbClose()
        self.usbOpen_flag = False
        self.withZoom = False
        self.withFocus = False
        self.withIris = False

    def init_lens(self):
        # Initialize zoom, focus, and iris
        if self.withZoom:
            LensCtrl.ZoomInit()
        if self.withFocus:
            LensCtrl.FocusInit()
        if self.withIris:
            LensCtrl.IrisInit()

        # Init min and max values
        self.zoom_max = LensCtrl.zoomMaxAddr
        self.zoom_min = LensCtrl.zoomMinAddr
        self.focus_max = LensCtrl.focusMaxAddr
        self.focus_min = LensCtrl.focusMinAddr
        self.iris_max = LensCtrl.irisMaxAddr
        self.iris_min = LensCtrl.irisMinAddr

        # Init current values
        self.zoom_pos = LensCtrl.zoomCurrentAddr
        self.focus_pos = LensCtrl.focusCurrentAddr
        self.iris_pos = LensCtrl.irisCurrentAddr

    def move_zoom(self, position):
        if self.withZoom:
            # Check address is within the range
            if position < self.zoom_min or position > self.zoom_max:
                logging.error("Zoom position is out of range")
                return ValueError
            else:
                LensCtrl.ZoomMove(position)
        else:
            return ConnectionError

    def move_focus(self, position):
        if self.withFocus:
            # Check focus position is within range
            if position < self.focus_min or position > self.focus_max:
                logging.error("Focus position is out of range")
                return ValueError
            else:
                LensCtrl.FocusMove(position)
        else:
            return ConnectionError

    def move_iris(self, position):
        if self.withIris:
            # Check iris position is within range
            if position < self.iris_min or position > self.iris_max:
                logging.error("Iris position is out of range")
                return ValueError
            else:
                LensCtrl.IrisMove(position)
            return True
        else:
            return ConnectionError

    def get_zoom_pos(self):
        if self.withZoom:
            return LensCtrl.zoomCurrentAddr
        return ConnectionError

    def get_focus_pos(self):
        if self.withFocus:
            return LensCtrl.focusCurrentAddr
        return ConnectionError

    def get_iris_pos(self):
        if self.withIris:
            return LensCtrl.irisCurrentAddr
        return ConnectionError
    
    def calculate_focus_score(image, blur, position):
        image_filtered = cv.medianBlur(image, blur)
        laplacian = cv.Laplacian(image_filtered, cv.CV_64F)
        focus_score = laplacian.var()
        return focus_score

def main():
    logging.basicConfig(level=logging.DEBUG)
    lens_controller = LensController()
    lens_controller.scan_devices()
    lens_controller.connect(0)

    lens_controller.init_lens()

    lens_controller.move_focus(4100)
    print(f"Focus min: {lens_controller.focus_min}")

    time.sleep(1)
    focus_pos = 4250
    dir = -100
    n = 0
    start_t = time.perf_counter()
    try:
        while True:
            focus_pos += dir
            lens_controller.move_focus(focus_pos)
            print(f"Focus pos: {focus_pos}")

            if focus_pos > 4300:
                dir = -100
            elif focus_pos < 4200:
                dir = 100

            n += 1
            # time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    
    end_t = time.perf_counter()

    lens_controller.disconnect()

    # Print frequency
    print(f"Control frequency: {n / (end_t - start_t)}")


if __name__ == "__main__":
    main()
