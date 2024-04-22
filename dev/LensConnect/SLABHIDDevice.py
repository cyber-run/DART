#!/usr/bin/env python2


################################################################################
## Copyright (c) 2015 by Silicon Laboratories Inc.  All rights reserved.
## The program contained in this listing is proprietary to Silicon Laboratories,
## headquartered in Austin, Texas, U.S.A. and is subject to worldwide copyright
## protection, including protection under the United States Copyright Act of 1976
## as an unpublished work, pursuant to Section 104 and Section 408 of Title XVII
## of the United States code.  Unauthorized copying, adaptation, distribution,
## use, or display is prohibited by this law.
################################################################################

# Python 3.4

import ctypes
import sys

#-------------------------------------------------------------------------------
if sys.platform == 'win32':
    g_DLL = ctypes.windll.LoadLibrary("./SLABHIDDevice.dll")
elif sys.platform.startswith('linux'):
    g_DLL = ctypes.cdll.LoadLibrary("./libslabhiddevice.so.1.0")
elif sys.platform == 'darwin':
    g_DLL = ctypes.cdll.LoadLibrary("libSLABHIDDevice.dylib")

fnc = getattr(g_DLL, "HidDevice_GetNumHidDevices")
fnc.restype = ctypes.c_ulong
fnc = getattr(g_DLL, "HidDevice_GetHidString")
fnc.restype = ctypes.c_ubyte
fnc = getattr(g_DLL, "HidDevice_Open")
fnc.restype = ctypes.c_ubyte
fnc = getattr(g_DLL, "HidDevice_Close")
fnc.restype = ctypes.c_ubyte
fnc = getattr(g_DLL, "HidDevice_SetFeatureReport_Control")
fnc.restype = ctypes.c_ubyte
fnc = getattr(g_DLL, "HidDevice_GetFeatureReport_Control")
fnc.restype = ctypes.c_ubyte
fnc = getattr(g_DLL, "HidDevice_GetTimeouts")
fnc.restype = None
fnc = getattr(g_DLL, "HidDevice_SetTimeouts")
fnc.restype = None
fnc = getattr(g_DLL, "HidDevice_GetMaxReportRequest")
fnc.restype = ctypes.c_ulong
fnc = getattr(g_DLL, "HidDevice_GetInputReportBufferLength")
fnc.restype = ctypes.c_ushort
fnc = getattr(g_DLL, "HidDevice_GetOutputReportBufferLength")
fnc.restype = ctypes.c_ushort
fnc = getattr(g_DLL, "HidDevice_GetFeatureReportBufferLength")
fnc.restype = ctypes.c_ushort
fnc = getattr(g_DLL, "HidDevice_GetInputReport_Interrupt")
fnc.restype = ctypes.c_ubyte
fnc = getattr(g_DLL, "HidDevice_SetOutputReport_Interrupt")
fnc.restype = ctypes.c_ubyte
fnc = getattr(g_DLL, "HidDevice_GetInputReport_Control")
fnc.restype = ctypes.c_ubyte
fnc = getattr(g_DLL, "HidDevice_SetOutputReport_Control")
fnc.restype = ctypes.c_ubyte

#-------------------------------------------------------------------------------
# Functions yet to be wrapped

"""
BYTE	HidDevice_GetHidIndexedString(DWORD deviceIndex, WORD vid, WORD pid, DWORD stringIndex, char* deviceString, DWORD deviceStringLength);
BYTE	HidDevice_GetHidAttributes(DWORD deviceIndex, WORD vid, WORD pid, WORD* deviceVid, WORD* devicePid, WORD* deviceReleaseNumber);
void	HidDevice_GetHidGuid(void* hidGuid);
BYTE	HidDevice_GetHidLibraryVersion(BYTE* major, BYTE* minor, BOOL* release);
BOOL	HidDevice_IsOpened(HID_DEVICE device);
HANDLE	HidDevice_GetHandle(HID_DEVICE device);
BYTE	HidDevice_GetString(HID_DEVICE device, BYTE hidStringType, char* deviceString, DWORD deviceStringLength);
BYTE	HidDevice_GetIndexedString(HID_DEVICE device, DWORD stringIndex, char* deviceString, DWORD deviceStringLength);
BYTE	HidDevice_GetAttributes(HID_DEVICE device, WORD* deviceVid, WORD* devicePid, WORD* deviceReleaseNumber);
BOOL	HidDevice_FlushBuffers(HID_DEVICE device);
BOOL	HidDevice_CancelIo(HID_DEVICE device);
"""

#-------------------------------------------------------------------------------
# Constant definitions copied from the public DLL header
MAX_STRING_LENGTH = 260

# String Types
HID_VID_STRING	=				0x01
HID_PID_STRING	=				0x02
HID_PATH_STRING	=				0x03
HID_SERIAL_STRING	=			0x04
HID_MANUFACTURER_STRING		=	0x05
HID_PRODUCT_STRING		=		0x06

# Return Codes
HID_DEVICE_SUCCESS = 0x00

#-------------------------------------------------------------------------------
# This class trivially wraps SLABHIDDevice.dll. Class methods have same names as DLL functions.
# The parameters are the same unless the DLL declaration is given in a comment above wrapper to show difference.
# Also, the device file handle is stored in the object, so wrappers don't have it as the first parameter.
#
# See Function prototypes in SLABHIDDevice.h and HID_DeviceInterface_Specification.doc for functional description.

class SLABHIDDevice:
    def __init__(self):
        self.hDev = ctypes.c_void_p(0)

    def HidDevice_GetNumHidDevices(self, vid, pid):
        return g_DLL.HidDevice_GetNumHidDevices(vid, pid)

    def HidDevice_GetHidString(self, deviceIndex, vid, pid, hidStringType, deviceString, deviceStringLength):
        err = g_DLL.HidDevice_GetHidString( deviceIndex, vid, pid, hidStringType, deviceString, deviceStringLength)
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_GetHidString type %d err %x" % (hidStringType, err))
        return err

    def HidDevice_Open(self, deviceIndex, vid, pid, numInputBuffers):
        err = g_DLL.HidDevice_Open( ctypes.byref(self.hDev), deviceIndex, vid, pid, numInputBuffers)
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_Open err %x" % err)
        return err

    def HidDevice_Close(self):
        err = g_DLL.HidDevice_Close( self.hDev)
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_Close err %x" % err)
        return err

    def HidDevice_SetFeatureReport_Control(self, buffer, bufferSize):
        err = g_DLL.HidDevice_SetFeatureReport_Control(self.hDev, buffer, bufferSize)
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_SetFeatureReport_Control err %x" % err)
        return err

    def HidDevice_GetFeatureReport_Control(self, buffer, bufferSize):
        err = g_DLL.HidDevice_GetFeatureReport_Control(self.hDev, buffer, bufferSize)
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_GetFeatureReport_Control err %x" % err)
        return err

    def HidDevice_GetTimeouts(self, getReportTimeout, setReportTimeout):
        g_DLL.HidDevice_GetTimeouts(self.hDev, ctypes.byref(getReportTimeout), ctypes.byref(setReportTimeout))

    def HidDevice_SetTimeouts(self, getReportTimeout, setReportTimeout):
        g_DLL.HidDevice_SetTimeouts(self.hDev, getReportTimeout, setReportTimeout)

    def HidDevice_GetMaxReportRequest(self):
        return g_DLL.HidDevice_GetMaxReportRequest(self.hDev)

    def HidDevice_GetInputReportBufferLength(self):
        return g_DLL.HidDevice_GetInputReportBufferLength(self.hDev)

    def HidDevice_GetOutputReportBufferLength(self):
        return g_DLL.HidDevice_GetOutputReportBufferLength(self.hDev)

    def HidDevice_GetFeatureReportBufferLength(self):
        return g_DLL.HidDevice_GetFeatureReportBufferLength(self.hDev)

    def HidDevice_GetInputReport_Interrupt(self, buffer, bufferSize, numReports, bytesReturned):
        err = g_DLL.HidDevice_GetInputReport_Interrupt(self.hDev, buffer, bufferSize, numReports, ctypes.byref(bytesReturned))
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_GetInputReport_Interrupt err %x" % err)
        return err

    def HidDevice_SetOutputReport_Interrupt(self, buffer, bufferSize):
        err = g_DLL.HidDevice_SetOutputReport_Interrupt(self.hDev, buffer, bufferSize)
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_SetOutputReport_Interrupt err %x" % err)
        return err

    def HidDevice_SetOutputReport_Control(self, buffer, bufferSize):
        err = g_DLL.HidDevice_SetOutputReport_Control(self.hDev, buffer, bufferSize)
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_SetOutputReport_Control err %x" % err)
        return err

    def HidDevice_GetInputReport_Control(self, buffer, bufferSize):
        err = g_DLL.HidDevice_GetInputReport_Control(self.hDev, buffer, bufferSize)
        if err != HID_DEVICE_SUCCESS :
            print("HidDevice_GetInputReport_Control err %x" % err)
        return err

def StrToUshort(s):
    retval = int(s, 16) # this too can raise ValueError
    if retval > 0xffff:
        raise ValueError
    if retval < 0:
        raise ValueError
    return retval

#------------------------------------------------------
# Open device #DevIndex and dump info about it
def TestHID( device, vid, pid, DevIndex):
    buf = ctypes.create_string_buffer(MAX_STRING_LENGTH)

    if device.HidDevice_GetHidString(DevIndex, vid, pid, HID_VID_STRING, buf, MAX_STRING_LENGTH) != HID_DEVICE_SUCCESS:
        return -1
    print("HID_VID_STRING: %s" % buf.value.decode())
    if device.HidDevice_GetHidString(DevIndex, vid, pid, HID_PID_STRING, buf, MAX_STRING_LENGTH) != HID_DEVICE_SUCCESS:
        return -1
    print("HID_PID_STRING: %s" % buf.value.decode())
    if sys.platform == 'win32':
        if device.HidDevice_GetHidString(DevIndex, vid, pid, HID_PATH_STRING, buf, MAX_STRING_LENGTH) != HID_DEVICE_SUCCESS:
            return -1
        print("HID_PATH_STRING: %s" % buf.value.decode())
    if device.HidDevice_GetHidString(DevIndex, vid, pid, HID_SERIAL_STRING, buf, MAX_STRING_LENGTH) != HID_DEVICE_SUCCESS:
        return -1
    print("HID_SERIAL_STRING: %s" % buf.value.decode())
    if device.HidDevice_GetHidString(DevIndex, vid, pid, HID_MANUFACTURER_STRING, buf, MAX_STRING_LENGTH) != HID_DEVICE_SUCCESS:
        return -1
    print("HID_MANUFACTURER_STRING: %s" % buf.value.decode())
    if device.HidDevice_GetHidString(DevIndex, vid, pid, HID_PRODUCT_STRING, buf, MAX_STRING_LENGTH) != HID_DEVICE_SUCCESS:
        return -1
    print("HID_PRODUCT_STRING: %s" % buf.value.decode())
    
    if device.HidDevice_Open(DevIndex, vid, pid, 16) != HID_DEVICE_SUCCESS:
        return -1

    MaxReportRequest = device.HidDevice_GetMaxReportRequest()
    print("MaxReportRequest: %d" % MaxReportRequest)
    InputReportBufferLength = device.HidDevice_GetInputReportBufferLength()
    print("InputReportBufferLength: %d" % InputReportBufferLength)
    OutputReportBufferLength = device.HidDevice_GetOutputReportBufferLength()
    print("OutputReportBufferLength: %d" % OutputReportBufferLength)
    FeatureReportBufferLength = device.HidDevice_GetFeatureReportBufferLength()
    print("FeatureReportBufferLength: %d" % FeatureReportBufferLength)

    getReportTimeout  = ctypes.c_ulong(0)
    setReportTimeout  = ctypes.c_ulong(0)
    device.HidDevice_GetTimeouts(getReportTimeout, setReportTimeout)
    print("getReportTimeout: %d setReportTimeout: %d" % (getReportTimeout.value, setReportTimeout.value))

    if device.HidDevice_Close() != HID_DEVICE_SUCCESS:
        return -1

    return 0

API_Test_StatusNoDevFound = -2

def Test(vid, pid):
    rc = -1

    lib = SLABHIDDevice()
    try:
        SuccessCnt = 0
        NumDevices = lib.HidDevice_GetNumHidDevices(vid, pid)
        for i in range(0, NumDevices):
            if TestHID( lib, vid, pid, i) == 0:
                SuccessCnt = SuccessCnt + 1
        if NumDevices == 0:
            print("SLABHIDDevice:  no devices found vid %04x pid %04x" % (vid, pid))
            rc = API_Test_StatusNoDevFound
        elif NumDevices == SuccessCnt:
            rc = 0
    except:
        print("SLABHIDDevice: Unhandled exception")
    finally:
        return rc

#------------------------------------------------------
# Does no harm, just gets/dumps info about all devices
# Its purpose is to call all non-destructive wrappers as unit-testing.
#
def TestAll():
    import sys
    errorlevel = 1

    if len(sys.argv) != 1 :
        # Read 16-bit hex VID and PID from command line if specified, then test that device only
        if len(sys.argv) != 3 :
            print("error: invalid command line arguments: %s" % str(sys.argv))
            sys.exit(1)

        vid = 0
        pid = 0
        try:
            vid = StrToUshort(sys.argv[1])
            pid = StrToUshort(sys.argv[2])
        except ValueError:
            print("error: invalid command line arguments: %s" % str(sys.argv))
            sys.exit(1)

        rc = Test(vid, pid)
        if rc == 0:
            errorlevel = 0
    else:
        # Test all CP2110, CP2112 and CP2114 found
        NotFoundCnt = 0
        rc = Test(0x10c4, 0xea80) # CP2110
        if rc == API_Test_StatusNoDevFound:
            NotFoundCnt = NotFoundCnt + 1
            rc = 0
        if rc == 0:
            rc = Test(0x10c4, 0xea90) # CP2112
            if rc == API_Test_StatusNoDevFound:
                NotFoundCnt = NotFoundCnt + 1
                rc = 0
            if rc == 0:
                rc = Test(0x10c4, 0xeab0) # CP2114
                if rc == API_Test_StatusNoDevFound:
                    NotFoundCnt = NotFoundCnt + 1
                    rc = 0
            if rc == 0:
                errorlevel = 0

    if 0 != errorlevel: print("FAIL\n")
    sys.exit(errorlevel)


#------------------------------------------------------
# This main does no harm, just gets/dumps info about all devicea
# Its purpose is to call all non-destructive wrappers as unit-testing.
#
if __name__ == "__main__":
   TestAll()
