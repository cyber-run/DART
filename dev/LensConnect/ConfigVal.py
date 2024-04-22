# LensConnect Parameters

# for USB
VID = 0x10C4   # USB VID
PID = 0x8D08   # USB PID
I2CSLAVEADDR = 0x20 # I2C SlaveAddress (7bitAddress)

# for LensConnect RegisterBit
INIT_RUN_BIT    = 0x0001
NEED_INIT_BIT   = 0x0001
ZOOM_MASK       = 0x0002
FOCUS_MASK      = 0x0004
IRIS_MASK       = 0x0008
OPT_FILTER_MASK = 0x0010

# for waitCalc
OPT_FILTER_SPEED    = 1

# for Usb Add Error
#LOWHI_ERROR     = 0x50    # Status Bit 0 -> 1 Error
#HILOW_ERROR     = 0x51    # Status Bit 1 -> 0 Error
LOWHI_ERROR     = "Status bit hi error."    # Status Bit 0 -> 1 Error
HILOW_ERROR     = "Status bit low error."    # Status Bit 1 -> 0 Error

# for USB Read Length
LENSMODEL_LENGTH    = 24    # Lens model name length
USERAREA_LENGTH     = 32    # User area length
LENSADDRESS_LENGTH  = 4     # Lens address length
LENSCOUNT_LENGTH    = 4     # Lens device (Z/F/I) count length
SEGMENTOFFSET_LENGTH= 2     # Segment offset length
DATA_LENGTH         = 2     # Data length

# for USB Read
RETRYNUM = 10               # USB read retry Count

# Status wait Time
LOW_HIGH_WAIT   = 10        # Status1 busy bit 0->1 wait
WAIT_MAG        = 1000		# [ms] =1[s]=1000[ms]* 1.1times : Status wait magnification
MINIMUM_WAIT    = 500      # WaitTime minmun wait

# for HidSmbus_SetTimeouts
RESPONSETIMEOUT = 500         # 0 is Clock stretching

# for  HidSmbus_SetSmbusConfig
BITRATE         = 100000    # Default value 100KHz
AUTOREADRESPOND = 0         # 0 is false.
WRITETIMEOUT    = 500      # [ms]   
READTIMEOUT     = 500      # [ms]
SCLLOWTIMEOUT   = 0	        # [ms]
TRANSFARRETRIES = 0	        # [ms]

# for HidSmbus_SetGpioConfig
DIRECTION   = 0xFF          # HID_SMBUS_GPIO All Output(1) set
MODE        = 0x00          # HID_SMBUS_MODE All OpenDrain(0) set 
SPECIAL     = 0x00          # GPIO7 Spceial function OFF(0) 
CLKDIV      = 0xFF          # Not Use <if GPIO7 is ClkOut, 48MHz/(2*255)>