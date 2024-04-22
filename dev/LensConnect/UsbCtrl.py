import ConfigVal as CV
import SLABHIDtoSMBUS as SS
import time

i2cAddr = CV.I2CSLAVEADDR * 2
instance = SS.HidSmbusDevice()

def UsbGetNumDevices():
    try:
        numDevices = SS.GetNumDevices(CV.VID, CV.PID)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    return retval, numDevices

def UsbGetOpenedSnDevice(index):
    try:
        SnString = instance.GetString(SS.HID_SMBUS.SERIAL_STR)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    return retval, SnString

def UsbGetSnDevice(index):
    try:
        SnString = SS.GetString(index, CV.VID, CV.PID, SS.HID_SMBUS.SERIAL_STR)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    return retval, SnString

def UsbOpen(deviceNumber):
    try:
        instance.Open(deviceNumber, CV.VID, CV.PID)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    return retval

def UsbClose():
    try:
        instance.Close()
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    return retval

def UsbSetConfig():
    try:
        instance.SetSmbusConfig(CV.BITRATE, i2cAddr, CV.AUTOREADRESPOND,
                                CV.WRITETIMEOUT, CV.READTIMEOUT, CV.SCLLOWTIMEOUT, CV.TRANSFARRETRIES)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
        return retval
    try:
        instance.SetGpioConfig(CV.DIRECTION, CV.MODE, CV.SPECIAL, CV.CLKDIV)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    try:
        instance.SetTimeouts(CV.RESPONSETIMEOUT)
        retval = 0
    except SS.HidSmbusError as e:
        retval =e
    return retval

def UsbRead(segmentOffset, receiveSize):
    sendData = segmentOffset.to_bytes(2, 'big')
    try:
        instance.WriteRequest(i2cAddr, sendData)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    try:
        instance.ReadRequest(i2cAddr, receiveSize)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    time.sleep(0.1)  ## important wait
    try:
        instance.ForceReadResponse(receiveSize)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    try:
        dataLen = 0
        countNum = 0
        while(dataLen == 0):
            receivedData = instance.GetReadResponse(i2cAddr, 62)
            dataLen = len(receivedData)
            if ( countNum > CV.RETRYNUM):
                retval = "USB Read Time Out"
                break
            countNum += 1
            retval = 0
    except SS.HidSmbusError as e:
        retval = e
    return retval, receivedData

def UsbRead2BytesInt(segmentOffset):
    retval, data = UsbRead(segmentOffset, CV.DATA_LENGTH)
    IntData = int.from_bytes(data, 'big')
    return retval, IntData

def CountRead(segmentOffset):
    retval, data = UsbRead(segmentOffset,CV.LENSCOUNT_LENGTH)
    count = int.from_bytes(data, 'big')
    return retval, count    

def UsbWrite(segmentOffset, writeData):
    sendData1 = segmentOffset.to_bytes(2, 'big')
    sendData2 = writeData.to_bytes(2, 'big')
    sendData = sendData1 + sendData2
    try:
        instance.WriteRequest(i2cAddr,sendData)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    return retval

def UsbWriteString(segmentOffset, writeData):
    sendData1 = segmentOffset.to_bytes(2, 'big')
    sendData2 = bytes(writeData, encoding='UTF-8')
    sendData = sendData1 + sendData2
    try:
        instance.WriteRequest(i2cAddr,sendData)
        retval = 0
    except SS.HidSmbusError as e:
        retval = e
    return retval
