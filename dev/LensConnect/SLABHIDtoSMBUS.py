#!/usr/bin/env python2

## Copyright (c) 2013 by Silicon Laboratories.
## All rights reserved. This program and the accompanying materials
## are made available under the terms of the Silicon Laboratories End User
## License Agreement which accompanies this distribution, and is available at
## http://developer.silabs.com/legal/version/v10/License_Agreement_v10.htm
## Original content and implementation provided by Silicon Laboratories.

"""
Python wrapper for Silabs CP2112 library (SLABHIDtoSMBus.dll).

Documentation for the library is provided by CP2112_API_Specification.pdf.
"""
################################################################################
## This library has been partially modified by CBC corporation. 
## The changes are shown with a comment as "Modified by CBC".
## The original source are shown with origianl comments as "Origianl".
################################################################################

import ctypes as ct
import sys

__version__ = "0.0.2"
__date__ = "27 Aug 2013"

__all__ = ['HID_SMBUS', 'HID_SMBUS_S0', 'HID_SMBUS_S1', 'HID_SMBUS_STATUS_DESC',
    'HidSmbusDevice', 'HidSmbusError', 'IsOpened', 
    'GetNumDevices', 'GetAttributes', 'GetString', 
    'GetLibraryVersion', 'GetHidLibraryVersion', 'TestAll']

#==============================================================================
# Constants
#==============================================================================

class HID_SMBUS:
    VID = 0x10C4
    PID = 0xEA90

    VID_STR = 0x01
    PID_STR = 0x02
    PATH_STR = 0x03
    SERIAL_STR = 0x04
    MANUFACTURER_STR = 0x05
    PRODUCT_STR = 0x06

class HID_SMBUS_S0:
    IDLE = 0x00
    BUSY = 0x01
    COMPLETE = 0x02
    ERROR = 0x03

class HID_SMBUS_S1:
    BUSY_ADDRESS_ACKED = 0x00
    BUSY_ADDRESS_NACKED = 0x01
    BUSY_READING = 0x02
    BUSY_WRITING = 0x03

    ERROR_TIMEOUT_NACK = 0x00
    ERROR_TIMEOUT_BUS_NOT_FREE = 0x01
    ERROR_ARB_LOST = 0x02
    ERROR_READ_INCOMPLETE = 0x03
    ERROR_WRITE_INCOMPLETE = 0x04
    ERROR_SUCCESS_AFTER_RETRY = 0x05


#==============================================================================
# Error Handling
#==============================================================================
HID_SMBUS_DEVICE_NOT_FOUND	= 0x01

HID_SMBUS_STATUS_DESC = {
    0x00 : "HID_SMBUS_SUCCESS",
    0x01 : "HID_SMBUS_DEVICE_NOT_FOUND",
    0x02 : "HID_SMBUS_INVALID_HANDLE",
    0x03 : "HID_SMBUS_INVALID_DEVICE_OBJECT",
    0x04 : "HID_SMBUS_INVALID_PARAMETER",
    0x05 : "HID_SMBUS_INVALID_REQUEST_LENGTH",
    0x10 : "HID_SMBUS_READ_ERROR",
    0x11 : "HID_SMBUS_WRITE_ERROR",
    0x12 : "HID_SMBUS_READ_TIMED_OUT",
    0x13 : "HID_SMBUS_WRITE_TIMED_OUT",
    0x14 : "HID_SMBUS_DEVICE_IO_FAILED",
    0x15 : "HID_SMBUS_DEVICE_ACCESS_ERROR",
    0x16 : "HID_SMBUS_DEVICE_NOT_SUPPORTED",
    0xFF : "HID_SMBUS_UNKNOWN_ERROR",
}

class HidSmbusError(Exception):
    def __init__(self, status):
        self.status = status
        try:
            self.name = HID_SMBUS_STATUS_DESC[status]
        except:
            self.name = "HID_UART_STATUS_UNKNOWN: " + hex(status)
    def __str__(self):
        return self.name

def hidsmb_errcheck(result, func, args):
    if result != 0:
        raise HidSmbusError(result)


#==============================================================================
# CP2112 HIDtoSMBus DLL
#==============================================================================

if sys.platform == 'win32':
    _DLL = ct.windll.LoadLibrary("./SLABHIDtoSMBus.dll")
elif sys.platform.startswith('linux'):
    _DLL_prev = ct.CDLL("./libslabhiddevice.so.1.0", mode=ct.RTLD_GLOBAL)
    _DLL = ct.cdll.LoadLibrary("./libslabhidtosmbus.so.1.0")
elif sys.platform == 'darwin':
    _DLL = ct.cdll.LoadLibrary("libSLABHIDtoSMBus.dylib")

# for win_function in ["HidSmbus_GetHidGuid", 
    # "HidSmbus_GetIndexedString", "HidSmbus_GetOpenedIndexedString"]:
    # fnc = getattr(_DLL, win_function)
    # fnc.restype = ct.c_int
    # fnc.errcheck = hidsmb_errcheck

for hidsmb_function in ["HidSmbus_GetNumDevices", 
    "HidSmbus_GetAttributes", "HidSmbus_GetString", 
    "HidSmbus_GetLibraryVersion", "HidSmbus_GetHidLibraryVersion", 
    "HidSmbus_Open", "HidSmbus_Close", 
    "HidSmbus_IsOpened", "HidSmbus_GetPartNumber", 
    "HidSmbus_GetOpenedAttributes", "HidSmbus_GetOpenedString", 
    "HidSmbus_ReadRequest", "HidSmbus_AddressReadRequest", 
    "HidSmbus_ForceReadResponse", "HidSmbus_WriteRequest", 
    "HidSmbus_TransferStatusRequest", "HidSmbus_GetTransferStatusResponse", 
    "HidSmbus_CancelTransfer", "HidSmbus_CancelIo", "HidSmbus_Reset", 
    "HidSmbus_SetTimeouts", "HidSmbus_GetTimeouts", 
    "HidSmbus_SetSmbusConfig", "HidSmbus_GetSmbusConfig", 
    "HidSmbus_SetGpioConfig", "HidSmbus_GetGpioConfig", 
    "HidSmbus_ReadLatch", "HidSmbus_WriteLatch"]:
    fnc = getattr(_DLL, hidsmb_function)
    fnc.restype = ct.c_int
    fnc.errcheck = hidsmb_errcheck


#==============================================================================
# Library Functions
#==============================================================================
# Methods Not Implemented
#  HidSmbus_GetIndexedString(DWORD deviceNum, WORD vid, WORD pid, DWORD stringIndex, char* deviceString);
#  HidSmbus_GetHidGuid(void* guid);

# HidSmbus_GetNumDevices(DWORD* numDevices, WORD vid, WORD pid);
def GetNumDevices(vid=HID_SMBUS.VID, pid=HID_SMBUS.PID):
    """Returns the number of devices connected to the host with matching VID/PID."""
    ndev = ct.c_ulong()
    _DLL.HidSmbus_GetNumDevices(ct.byref(ndev), vid, pid)
    return ndev.value

# HidSmbus_GetAttributes(DWORD deviceNum, WORD vid, WORD pid, WORD* deviceVid, WORD* devicePid, WORD* deviceReleaseNumber);
def GetAttributes(index=0, vid=HID_SMBUS.VID, pid=HID_SMBUS.PID):
    """Returns VID, PID and release number for the indexed device with matching VID/PID."""
    dev_vid = ct.c_ushort()
    dev_pid = ct.c_ushort()
    dev_rel = ct.c_ushort()
    _DLL.HidSmbus_GetAttributes(index, vid, pid, ct.byref(dev_vid), ct.byref(dev_pid), ct.byref(dev_rel))
    return (dev_vid.value, dev_pid.value, dev_rel.value)

# HidSmbus_GetString(DWORD deviceNum, WORD vid, WORD pid, char* deviceString, DWORD options);
def GetString(index=0, vid=HID_SMBUS.VID, pid=HID_SMBUS.PID, opt=HID_SMBUS.SERIAL_STR):
    """Returns the selected string for the indexed device with matching VID/PID."""
    buf = ct.create_string_buffer(512)
    _DLL.HidSmbus_GetString(index, vid, pid, buf, opt)
    return buf.value.decode()

# HidSmbus_GetLibraryVersion(BYTE* major, BYTE* minor, BOOL* release);
def GetLibraryVersion():
    """Returns the SLABHIDtoSMBus library version number as a string."""
    major = ct.c_byte()
    minor = ct.c_byte()
    release = ct.c_long()
    _DLL.HidSmbus_GetLibraryVersion(ct.byref(major), ct.byref(minor), ct.byref(release))
    return "{}.{}.{}".format(major.value, minor.value, release.value)

# HidSmbus_GetHidLibraryVersion(BYTE* major, BYTE* minor, BOOL* release);
def GetHidLibraryVersion():
    """Returns the SLABHIDDevice library version number as a string."""
    major = ct.c_byte()
    minor = ct.c_byte()
    release = ct.c_long()
    _DLL.HidSmbus_GetHidLibraryVersion(ct.byref(major), ct.byref(minor), ct.byref(release))
    return "{}.{}.{}".format(major.value, minor.value, release.value)

def IsOpened(index=0, vid=HID_SMBUS.VID, pid=HID_SMBUS.PID):
    """Checks if the indexed device with matching VID/PID is already open."""
    status = 0
    try:
        GetAttributes(index, vid, pid)
    except HidSmbusError as e:
        status = e.status
    # 0x15 : "HID_SMBUS_DEVICE_ACCESS_ERROR"
    return bool(status == 0x15)


#==============================================================================
# HidSmb Class
#==============================================================================
# Methods Not Implemented:
#  HidSmbus_GetOpenedIndexedString(HID_SMBUS_DEVICE device, DWORD stringIndex, char* deviceString);
#
#  HidSmbus_SetLock(HID_SMBUS_DEVICE device, BYTE lock);
#  HidSmbus_GetLock(HID_SMBUS_DEVICE device, BYTE* lock);
#  HidSmbus_SetUsbConfig(HID_SMBUS_DEVICE device, WORD vid, WORD pid, BYTE power, BYTE powerMode, WORD releaseVersion, BYTE mask);
#  HidSmbus_GetUsbConfig(HID_SMBUS_DEVICE device, WORD* vid, WORD* pid, BYTE* power, BYTE* powerMode, WORD* releaseVersion);
#  HidSmbus_SetManufacturingString(HID_SMBUS_DEVICE device, char* manufacturingString, BYTE strlen);
#  HidSmbus_GetManufacturingString(HID_SMBUS_DEVICE device, char* manufacturingString, BYTE* strlen);
#  HidSmbus_SetProductString(HID_SMBUS_DEVICE device, char* productString, BYTE strlen);
#  HidSmbus_GetProductString(HID_SMBUS_DEVICE device, char* productString, BYTE* strlen);
#  HidSmbus_SetSerialString(HID_SMBUS_DEVICE device, char* serialString, BYTE strlen);
#  HidSmbus_GetSerialString(HID_SMBUS_DEVICE device, char* serialString, BYTE* strlen);

class HidSmbusDevice:
    """
    HidSmbusDevice instances are used to work with a specific CP2112 device.

    For help on the wrapped functions, refer to CP2112_API_Specification.pdf.
    """

    def __init__(self):
        self.handle = ct.c_void_p(0)
        self._S0 = ct.c_byte(0)
        self._S1 = ct.c_byte(0)
        GetNumDevices()

    @property
    def S0(self):
        return self._S0.value

    @property
    def S1(self):
        return self._S1.value

    # HidSmbus_Open(HID_SMBUS_DEVICE* device, DWORD deviceNum, WORD vid, WORD pid);
    def Open(self, index=0, vid=HID_SMBUS.VID, pid=HID_SMBUS.PID):
        _DLL.HidSmbus_Open(ct.byref(self.handle), index, vid, pid)

    # HidSmbus_Close(HID_SMBUS_DEVICE device);
    def Close(self):
        if self.handle:
            _DLL.HidSmbus_Close(self.handle)
            self.handle.value = 0

    # HidSmbus_IsOpened(HID_SMBUS_DEVICE device, BOOL* opened);
    def IsOpened(self):
        opened = ct.c_long(0)
        if self.handle:
            _DLL.HidSmbus_IsOpened(self.handle, ct.byref(opened))
        return bool(opened.value)

    # HidSmbus_GetOpenedAttributes(HID_SMBUS_DEVICE device, WORD* deviceVid, WORD* devicePid, WORD* deviceReleaseNumber);
    def GetAttributes(self):
        vid = ct.c_ushort(0)
        pid = ct.c_ushort(0)
        rel = ct.c_ushort(0)
        _DLL.HidSmbus_GetOpenedAttributes(self.handle, ct.byref(vid), ct.byref(pid), ct.byref(rel))
        return (vid.value, pid.value, rel.value)

    # HidSmbus_GetPartNumber(HID_SMBUS_DEVICE device, BYTE* partNumber, BYTE* version);
    def GetPartNumber(self):
        pno = ct.c_byte(0)
        ver = ct.c_byte(0)
        _DLL.HidSmbus_GetPartNumber(self.handle, ct.byref(pno), ct.byref(ver))
        return (pno.value, ver.value)

    # HidSmbus_GetOpenedString(HID_SMBUS_DEVICE device, char* deviceString, DWORD options);
    def GetString(self, opt=HID_SMBUS.SERIAL_STR):
        buf = ct.create_string_buffer(512)
        _DLL.HidSmbus_GetOpenedString(self.handle, buf, opt)
        return buf.value.decode()

    # HidSmbus_CancelTransfer(HID_SMBUS_DEVICE device);
    def CancelTransfer(self):
        _DLL.HidSmbus_CancelTransfer(self.handle)

    # HidSmbus_CancelIo(HID_SMBUS_DEVICE device);
    def CancelIo(self):
        _DLL.HidSmbus_CancelIo(self.handle)

    # HidSmbus_Reset(HID_SMBUS_DEVICE device);
    def Reset(self):
        _DLL.HidSmbus_Reset(self.handle)
        _DLL.HidSmbus_Close(self.handle)
        self.handle.value = 0

    # HidSmbus_ReadRequest(HID_SMBUS_DEVICE device, BYTE slaveAddress, WORD numBytesToRead);
    def ReadRequest(self, address=2, count=64):
        _DLL.HidSmbus_ReadRequest(self.handle, address, count)

    # HidSmbus_AddressReadRequest(HID_SMBUS_DEVICE device, BYTE slaveAddress, WORD numBytesToRead, BYTE targetAddressSize, BYTE targetAddress[16]);
    def AddressReadRequest(self, address=2, count=64, offset_size=2, offset=b'\x00\x00'):
        buf = ct.create_string_buffer(bytes(offset), size=16)
        _DLL.HidSmbus_AddressReadRequest(self.handle, address, count, offset_size, buf)

    # HidSmbus_ForceReadResponse(HID_SMBUS_DEVICE device, WORD numBytesToRead);
    def ForceReadResponse(self, count=64):
        _DLL.HidSmbus_ForceReadResponse(self.handle, count)

    # HidSmbus_GetReadResponse(HID_SMBUS_DEVICE device, HID_SMBUS_S0* status, BYTE* buffer, BYTE bufferSize, BYTE* numBytesRead);
    def GetReadResponse(self, address=2, count=64):
        buf = ct.create_string_buffer(count)
        n = ct.c_ulong(0)
        try:
            _DLL.HidSmbus_GetReadResponse(self.handle, ct.byref(self._S0), buf, count, ct.byref(n))
        except HidSmbusError as e:
            # Ignore timeout, return the data that was read
            if e.status != 0x12:
                raise
        data = buf.raw[0 : n.value]     # ***** Modified by CBC *****
        return data                     # ***** Modified by CBC *****
        # return buf.value              # ***** Original *****

    # HidSmbus_WriteRequest(HID_SMBUS_DEVICE device, BYTE slaveAddress, BYTE* buffer, BYTE numBytesToWrite);
    def WriteRequest(self, address, buffer, count=None):
        if count is None:
            count = len(buffer)
        _DLL.HidSmbus_WriteRequest(self.handle, address, bytes(buffer), count)

    # HidSmbus_TransferStatusRequest(HID_SMBUS_DEVICE device);
    def TransferStatusRequest(self):
        _DLL.HidSmbus_TransferStatusRequest(self.handle)

    # HidSmbus_GetTransferStatusResponse(HID_SMBUS_DEVICE device, HID_SMBUS_S0* status, HID_SMBUS_S1* detailedStatus, WORD* numRetries, WORD* bytesRead);
    def GetTransferStatusResponse(self):
        tries = ct.c_ushort(0)
        count = ct.c_ushort(0)
        _DLL.HidSmbus_GetTransferStatusResponse(self.handle, ct.byref(self._S0), ct.byref(self._S1), ct.byref(tries), ct.byref(count))
        return (self._S0.value, self._S1.value, tries.value, count.value)

    # HidSmbus_SetTimeouts(HID_SMBUS_DEVICE device, DWORD responseTimeout);
    def SetTimeouts(self, timeout=1000):
        _DLL.HidSmbus_SetTimeouts(self.handle, timeout)

    # HidSmbus_GetTimeouts(HID_SMBUS_DEVICE device, DWORD* responseTimeout);
    def GetTimeouts(self):
        timeout = ct.c_ulong(0)
        _DLL.HidSmbus_GetTimeouts(self.handle, ct.byref(timeout))
        return timeout.value

    # HidSmbus_SetSmbusConfig(HID_SMBUS_DEVICE device, DWORD bitRate, BYTE address, BOOL autoReadRespond, WORD writeTimeout, WORD readTimeout, BOOL sclLowTimeout, WORD transferRetries);
    def SetSmbusConfig(self, bitRate=100000, address=2, autoReadRespond=False, writeTimeout=0, readTimeout=0, sclLowTimeout=False, transferRetries=0):
        _DLL.HidSmbus_SetSmbusConfig(self.handle, 
            bitRate, address, autoReadRespond, writeTimeout, readTimeout, sclLowTimeout, transferRetries)

    # HidSmbus_GetSmbusConfig(HID_SMBUS_DEVICE device, DWORD* bitRate, BYTE* address, BOOL* autoReadRespond, WORD* writeTimeout, WORD* readTimeout, BOOL* sclLowtimeout, WORD* transferRetries);
    def GetSmbusConfig(self):
        rate = ct.c_ulong()
        addr = ct.c_byte()
        auto = ct.c_bool()
        wto = ct.c_ushort()
        rto = ct.c_ushort()
        scl = ct.c_bool()
        retry = ct.c_ushort()
        _DLL.HidSmbus_GetSmbusConfig(self.handle, 
            ct.byref(rate), ct.byref(addr), ct.byref(auto), ct.byref(wto), 
            ct.byref(rto), ct.byref(scl), ct.byref(retry))
        return (rate.value, addr.value, auto.value, wto.value, rto.value, scl.value, retry.value)

    # HidSmbus_SetGpioConfig(HID_SMBUS_DEVICE device, BYTE direction, BYTE mode, BYTE function, BYTE clkDiv);
    def SetGpioConfig(self, direction=0, mode=0, function=0, clkDiv=0):
        _DLL.HidSmbus_SetGpioConfig(self.handle, direction, mode, function, clkDiv)

    # HidSmbus_GetGpioConfig(HID_SMBUS_DEVICE device, BYTE* direction, BYTE* mode, BYTE* function, BYTE* clkDiv);
    def GetGpioConfig(self):
        dir = ct.c_byte()
        mode = ct.c_byte()
        fnc = ct.c_byte()
        div = ct.c_byte()
        _DLL.HidSmbus_GetGpioConfig(self.handle, ct.byref(dir), ct.byref(mode), ct.byref(fnc), ct.byref(div))
        return (dir.value, mode.value, fnc.value, div.value)

    # HidSmbus_ReadLatch(HID_SMBUS_DEVICE device, BYTE* latchValue);
    def ReadLatch(self):
        latch = ct.c_ushort()
        _DLL.HidSmbus_ReadLatch(self.handle, ct.byref(latch))
        return latch.value

    # HidSmbus_WriteLatch(HID_SMBUS_DEVICE device, BYTE latchValue, BYTE latchMask);
    def WriteLatch(self, latch, mask=0xFF):
        _DLL.HidSmbus_WriteLatch(self.handle, latch, mask)

def PRINTV(*arg):
#    print(arg)
    pass

def Test( DevIndex):

    PRINTV("--- device #%d" % DevIndex)
    PRINTV("SLABHIDtoSMBus:", GetLibraryVersion())
    PRINTV(" SLABHIDDevice:", GetHidLibraryVersion())

    rc = -1
    try:
        smb = HidSmbusDevice()
        smb.Open(DevIndex)
        PRINTV('')
        PRINTV("    VID:", smb.GetString(HID_SMBUS.VID_STR))
        PRINTV("    PID:", smb.GetString(HID_SMBUS.PID_STR))
        if sys.platform == 'win32':
            PRINTV("DevPath:", smb.GetString(HID_SMBUS.PATH_STR))
        PRINTV("    S/N:", smb.GetString(HID_SMBUS.SERIAL_STR))
        PRINTV("Product:", smb.GetString(HID_SMBUS.PRODUCT_STR))
        PRINTV("Company:", smb.GetString(HID_SMBUS.MANUFACTURER_STR))
        PRINTV('')
        PRINTV("GetAttributes()  =", smb.GetAttributes())
        PRINTV("GetPartNumber()  =", smb.GetPartNumber())
        PRINTV("GetString()      =", smb.GetString())
        PRINTV("GetTimeouts()    =", smb.GetTimeouts())
        PRINTV("GetSmbusConfig() =", smb.GetSmbusConfig())
        PRINTV("GetGpioConfig()  =", smb.GetGpioConfig())
        PRINTV("ReadLatch()      =", hex(smb.ReadLatch()))
        smb.TransferStatusRequest()
        PRINTV("GetTransferStatusResponse() =", smb.GetTransferStatusResponse())
        rc = 0
    except HidSmbusError as e:
        print("Device Error:", e, "-", hex(e.status))
    finally:
        smb.Close()
        return rc

def TestInvalDevIndex( NumDevices):
    rc = 0
    try:
        smb = HidSmbusDevice()
        smb.Open(NumDevices)
        rc = -1
    except HidSmbusError as e:
        if e.status != HID_SMBUS_DEVICE_NOT_FOUND :
            print("TestInvalDevIndex: Unexpected error:", e, "-", hex(e.status))
            rc = -1
    finally:
        return rc

def TestAll():
    errorlevel = 1
    try:
        NumDevices = GetNumDevices()

        if TestInvalDevIndex( NumDevices) == 0:
            SuccessCnt = 0
            for i in range(0, NumDevices):
                if Test( i) == 0:
                    SuccessCnt = SuccessCnt + 1
            if NumDevices == SuccessCnt:
                errorlevel = 0 # let shell know that test PASSED
    except:
        print("API_Test: Unhandled exception")
    finally:
        if errorlevel:
            print("FAIL\n")
        else:
            print("PASS\n")
        sys.exit(errorlevel)

if __name__ == "__main__":
   TestAll()
