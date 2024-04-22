from SLABHIDDevice import HID_DEVICE_SUCCESS
from perf_sleeper import PerfSleeper
import DevAddr as DA
import ConfigVal as CV
import UsbCtrl
import time

zoomMaxAddr = 0
zoomMinAddr = 0
zoomCurrentAddr = 0
zoomSpeedPPS = 0

focusMaxAddr = 0
focusMinAddr = 0
focusCurrentAddr = 0
focusSpeedPPS = 0

irisMaxAddr = 0
irisMinAddr = 0
irisCurrentAddr = 0
irisSpeedPPS = 0

optFilMaxAddr = 0
optCurrentAddr = 0
status2 = 0

SLEEPER = PerfSleeper()

def NoErrChk2BytesIntRead(segmentOffset):
    retval, IntData = UsbCtrl.UsbRead2BytesInt(segmentOffset)
    return IntData

def ModelName():
    retval, data = UsbCtrl.UsbRead(DA.LENS_MODEL_NAME, CV.LENSMODEL_LENGTH)
    model = str(data,'utf-8')
    return retval, model

def UserAreaRead():
    retval, data = UsbCtrl.UsbRead(DA.USER_AREA, CV.USERAREA_LENGTH)
    userName = str(data,'utf-8')
    return retval, userName

def FWVersion():
    retval, data = UsbCtrl.UsbRead(DA.FIRMWARE_VERSION, CV.DATA_LENGTH)
    version = str(data[0]) + "." + format(data[1], '02d')
    return retval, version

def ProtocolVersion():
    retval, data = UsbCtrl.UsbRead(DA.PROTOCOL_VERSION, CV.DATA_LENGTH)
    version = str(data[0]) + "." + format(data[1], '02d')
    return retval, version

def LensRevision():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.LENS_REVISION)
    return retval, data

def LensAddress():
    retval, data = UsbCtrl.UsbRead(DA.LENS_ADDRESS, CV.DATA_LENGTH)
    i2cAddress = int(data[0])
    return retval, i2cAddress

def CapabilitiesRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.CAPABILITIES)
    return retval, data

def Status1Read():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.STATUS1)
    return retval, data

def Status2ReadSet():
    global status2
    retval, status2 = UsbCtrl.UsbRead2BytesInt(DA.STATUS2)
    return retval, status2

def TempKelvinVal():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.TEMPURATURE_VAL)
    return retval, data

def TempKelvinMin():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.TEMPURATURE_MIN)
    return retval, data

def TempKelvinMax():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.TEMPURATURE_MAX)
    return retval, data

def UserAreaWrite(UserName):
    UserNameSize = len(UserName)
    if (UserNameSize < CV.USERAREA_LENGTH):
        space = CV.USERAREA_LENGTH -UserNameSize
        for num in range(space):
            UserName = UserName + " "
            num += 1
    UserNameSize = len(UserName)
    retval = UsbCtrl.UsbWriteString(DA.USER_AREA, UserName)
    return retval

def WaitCalc(moveValue, speedPPS):
    waitTime = CV.WAIT_MAG *moveValue / speedPPS
    if (CV.MINIMUM_WAIT > waitTime):
        waitTime = CV.MINIMUM_WAIT
    return waitTime

def ZoomCurrentAddrReadSet():
    global zoomCurrentAddr
    retval, zoomCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_POSITION_VAL)
    return retval

def ZoomParameterReadSet():
    global zoomMinAddr
    global zoomMaxAddr
    global zoomSpeedPPS
    retval, zoomMinAddr = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_POSITION_MIN)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    retval, zoomMaxAddr = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_POSITION_MAX)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    retval, zoomSpeedPPS = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_SPEED_VAL)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    return retval

def ZoomBacklashRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_BACKLASH_CANCEL)
    return retval, data

def ZoomBacklashWrite(flag):
    retval = UsbCtrl.UsbWrite(DA.ZOOM_BACKLASH_CANCEL, flag)
    return retval

def ZoomSpeedMinRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_SPEED_MIN)
    return retval, data

def ZoomSpeedMaxRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_SPEED_MAX)
    return retval, data

def ZoomSpeedWrite(speedPPS):
    global zoomSpeedPPS
    retval = UsbCtrl.UsbWrite(DA.ZOOM_SPEED_VAL, speedPPS)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    time.sleep(0.001)
    retval, zoomSpeedPPS = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_SPEED_VAL)
    return retval

def ZoomCountValRead():
    retval, count = UsbCtrl.CountRead(DA.ZOOM_COUNT_VAL)
    return retval, count

def ZoomCountMaxRead():
    retval, count = UsbCtrl.CountRead(DA.ZOOM_COUNT_MAX)
    return retval, count

def ZoomInit():
    global zoomMaxAddr
    global zoomMinAddr
    global zoomSpeedPPS
    global zoomCurrentAddr
    waitTime = WaitCalc((zoomMaxAddr - zoomMinAddr), zoomSpeedPPS)
    retval = UsbCtrl.UsbWrite(DA.ZOOM_INITIALIZE, CV.INIT_RUN_BIT)
    if (retval == HID_DEVICE_SUCCESS):
        retval = StatusWait(DA.STATUS1, CV.ZOOM_MASK, waitTime)
        if (retval == HID_DEVICE_SUCCESS):
            retval, zoomCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.ZOOM_POSITION_VAL)
            if (retval == HID_DEVICE_SUCCESS):
                Status2ReadSet()
                return retval
    return retval

def ZoomMove(addrData):
    global zoomCurrentAddr
    global zoomSpeedPPS
    moveVal = abs(addrData - zoomCurrentAddr)
    waitTime = WaitCalc(moveVal, zoomSpeedPPS)
    retval, data = DeviceMove(DA.ZOOM_POSITION_VAL, addrData, CV.ZOOM_MASK, waitTime)
    if (retval == HID_DEVICE_SUCCESS):
        zoomCurrentAddr = data
    return retval

def FocusCurrentAddrReadSet():
    global focusCurrentAddr
    retval, focusCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_POSITION_VAL)
    return retval

def FocusParameterReadSet():
    global focusMinAddr
    global focusMaxAddr
    global focusSpeedPPS
    retval, focusMinAddr = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_MECH_STEP_MIN)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    retval, focusMaxAddr = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_MECH_STEP_MAX)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    retval, focusSpeedPPS = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_SPEED_VAL)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    return retval

def FocusBacklashRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_BACKLASH_CANCEL)
    return retval, data
    
def FocusBacklashWrite(flag):
    retval = UsbCtrl.UsbWrite(DA.FOCUS_BACKLASH_CANCEL, flag)
    return retval

def FocusSpeedMinRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_SPEED_MIN)
    return retval, data

def FocusSpeedMaxRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_SPEED_MAX)
    return retval, data

def FocusSpeedWrite(speedPPS):
    global focusSpeedPPS
    retval = UsbCtrl.UsbWrite(DA.FOCUS_SPEED_VAL, speedPPS)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    time.sleep(0.001)
    retval, focusSpeedPPS = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_SPEED_VAL)
    return retval

def FocusCountValRead():
    retval, count = UsbCtrl.CountRead(DA.FOCUS_COUNT_VAL)
    return retval, count

def FocusCountMaxRead():
    retval, count = UsbCtrl.CountRead(DA.FOCUS_COUNT_MAX)
    return retval, count

def FocusInit():
    global focusMaxAddr
    global focusMinAddr
    global focusSpeedPPS
    global focusCurrentAddr
    waitTime = WaitCalc((focusMaxAddr - focusMinAddr), focusSpeedPPS)
    retval = UsbCtrl.UsbWrite(DA.FOCUS_INITIALIZE, CV.INIT_RUN_BIT)
    if (retval == HID_DEVICE_SUCCESS):
        retval = StatusWait(DA.STATUS1, CV.FOCUS_MASK, waitTime)
        if (retval == HID_DEVICE_SUCCESS):
            retval, focusCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_POSITION_VAL)
            if (retval == HID_DEVICE_SUCCESS):
                Status2ReadSet()
                return retval
    return retval

def FocusMove(addrData):
    global focusCurrentAddr
    global focusSpeedPPS
    moveVal = abs(addrData - focusCurrentAddr)
    waitTime = WaitCalc(moveVal, focusSpeedPPS)
    retval, data = DeviceMove(DA.FOCUS_POSITION_VAL, addrData, CV.FOCUS_MASK, waitTime)
    if (retval == HID_DEVICE_SUCCESS):
        focusCurrentAddr = data
    return retval

def IrisCurrentAddrReadSet():
    global irisCurrentAddr
    retval, irisCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.IRIS_POSITION_VAL)
    return retval

def IrisParameterReadSet():
    global irisMinAddr
    global irisMaxAddr
    global irisSpeedPPS
    retval, irisMinAddr = UsbCtrl.UsbRead2BytesInt(DA.IRIS_MECH_STEP_MIN)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    retval, irisMaxAddr = UsbCtrl.UsbRead2BytesInt(DA.IRIS_MECH_STEP_MAX)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    retval, irisSpeedPPS = UsbCtrl.UsbRead2BytesInt(DA.IRIS_SPEED_VAL)
    if (retval != HID_DEVICE_SUCCESS):
        return retval 
    return retval

def IrisBacklashRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.IRIS_BACKLASH_CANCEL)
    return retval, data

def IrisBacklashWrite(flag):
    retval = UsbCtrl.UsbWrite(DA.IRIS_BACKLASH_CANCEL, flag)
    return retval

def IrisSpeedMinRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.IRIS_SPEED_MIN)
    return retval, data

def IrisSpeedMaxRead():
    retval, data = UsbCtrl.UsbRead2BytesInt(DA.IRIS_SPEED_MAX)
    return retval, data

def IrisSpeedWrite(speedPPS):
    global irisSpeedPPS
    retval = UsbCtrl.UsbWrite(DA.IRIS_SPEED_VAL, speedPPS)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    time.sleep(0.001)
    retval, irisSpeedPPS = UsbCtrl.UsbRead2BytesInt(DA.IRIS_SPEED_VAL)
    return retval

def IrisCountValRead():
    retval, count = UsbCtrl.CountRead(DA.IRIS_COUNT_VAL)
    return retval, count

def IrisCountMaxRead():
    retval, count = UsbCtrl.CountRead(DA.IRIS_COUNT_MAX)
    return retval, count

def IrisInit():
    global irisMaxAddr
    global irisMinAddr
    global irisSpeedPPS
    global irisCurrentAddr
    waitTime = WaitCalc((irisMaxAddr - irisMinAddr), irisSpeedPPS)
    retval = UsbCtrl.UsbWrite(DA.IRIS_INITIALIZE, CV.INIT_RUN_BIT)
    if (retval == HID_DEVICE_SUCCESS):
        retval = StatusWait(DA.STATUS1, CV.IRIS_MASK, waitTime)
        if (retval == HID_DEVICE_SUCCESS):
            retval, irisCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.IRIS_POSITION_VAL)
            if (retval == HID_DEVICE_SUCCESS):
                Status2ReadSet()
                return retval
    return retval

def IrisMove(addrData):
    global irisCurrentAddr
    global irisSpeedPPS
    moveVal = abs(addrData - irisCurrentAddr)
    waitTime = WaitCalc(moveVal, irisSpeedPPS)
    retval, data = DeviceMove(DA.IRIS_POSITION_VAL, addrData, CV.IRIS_MASK,waitTime)
    if (retval == HID_DEVICE_SUCCESS):
        irisCurrentAddr = data
    return retval

def OptFilterCurrentAddrReadSet():
    global optCurrentAddr
    retval, optCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.OPT_FILTER_POSITION_VAL)
    return retval

def OptFilterParameterReadSet():
    global optFilMaxAddr
    retval, optFilMaxAddr =UsbCtrl.UsbRead2BytesInt(DA.OPT_FILTER_MECH_STEP_MAX)
    if (retval != HID_DEVICE_SUCCESS):
        return retval
    OptFilterCurrentAddrReadSet()
    return retval

def OPtFilterCountValRead():
    retval, count = UsbCtrl.CountRead(DA.OPT_FILTER_COUNT_VAL)
    return retval, count

def OptFilterCountMaxRead():
    retval, count = UsbCtrl.CountRead(DA.OPT_FILTER_COUNT_MAX)
    return retval, count

def OptFilterInit():
    global optFilMaxAddr
    global optCurrentAddr
    waitTime = WaitCalc((optFilMaxAddr + 1), CV.OPT_FILTER_SPEED)
    retval = UsbCtrl.UsbWrite(DA.OPT_FILTER_INITIALIZE, CV.INIT_RUN_BIT)
    if (retval == HID_DEVICE_SUCCESS):
        retval  = StatusWait(DA.STATUS1, CV.OPT_FILTER_MASK, waitTime)
        if (retval == HID_DEVICE_SUCCESS):
            retval, optCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.OPT_FILTER_POSITION_VAL) 
            if (retval == HID_DEVICE_SUCCESS):
                Status2ReadSet()
                return retval
        return retval

def OptFilterMove(addrData):
    global optCurrentAddr
    moveVal = abs (addrData - optCurrentAddr)
    waitTime = WaitCalc(moveVal, CV.OPT_FILTER_SPEED)
    retval, data = DeviceMove(DA.OPT_FILTER_POSITION_VAL, addrData, waitTime)
    if (retval == HID_DEVICE_SUCCESS):
        optCurrentAddr = data
        return retval

def DeviceMove(segmentOffset, addrData, mask, waitTime):
    retval = UsbCtrl.UsbWrite(segmentOffset, addrData)
    if (retval == HID_DEVICE_SUCCESS):
        retval = StatusWait(DA.STATUS1, mask, waitTime)
        if (retval == HID_DEVICE_SUCCESS):
            retval, data = UsbCtrl.UsbRead2BytesInt(segmentOffset)
            if (retval != HID_DEVICE_SUCCESS):
                return retval, addrData
            addrData = data
    return retval, addrData

def StatusWait(segmentOffset, statusMask, waitTime):
    tmp = 0
    readStatus = 0
    while ((readStatus & statusMask) != statusMask):
        retval, data = UsbCtrl.UsbRead2BytesInt(segmentOffset)
        if (retval != HID_DEVICE_SUCCESS):
            return retval
        readStatus = data
        tmp += 1
        if (tmp >= CV.LOW_HIGH_WAIT):
            return CV.LOWHI_ERROR
    tmp = 0
    readStatus = 0xFF
    while ((readStatus & statusMask) != 0):
        retval, data = UsbCtrl.UsbRead2BytesInt(segmentOffset)
        if (retval != HID_DEVICE_SUCCESS):
            return retval
        readStatus = data
        tmp += 1
        if (tmp >= waitTime):
            return CV.HILOW_ERROR
        time.sleep(0.001)
    return retval
