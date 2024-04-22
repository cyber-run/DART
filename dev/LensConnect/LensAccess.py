import LensCtrl
import DefVal as DV

fineNum = 10    #default focus fine tuning number

def MoveLens(motor):
    data = input("\nEnter the adderess you want to go ")
    addrData = int(data)
    if (motor == DV.ZOOM):
        LensCtrl.ZoomMove(addrData)
    elif (motor == DV.FOCUS):
        LensCtrl.FocusMove(addrData)
    elif (motor == DV.IRIS):
        LensCtrl.IrisMove(addrData)
    elif (motor == DV.OPT):
        LensCtrl.OptFilterMove(addrData)
    print("")


def UserIDRead():
    retval, userName = LensCtrl.UserAreaRead()
    print(userName)

def UserIDWrite():
    print("\nPlease fill in  the user area(32byte full)")
    print("12345678901234567890123456789012")
    userName = input("")
    if len(userName) > 32:
        print("Error! Only 32 characters allowed!")
    else:
        LensCtrl.UserAreaWrite(userName)
    print("")

def FineFocusMove():
    print("Fine focus move")
    print("Selection : Near -> n / Far -> f / End -> q, fine step = {} >>".format(fineNum), end="")
    dir = ""
    while True:
        key = input()
        if(key == ("n" or"N")):
            dir = "Near"
            print("Set Near. Press Enter key.", end="")
        elif(key == ("f" or "F")):
            dir = "Far"
            print("Set Far. Press Enter key.", end="")

        elif(key ==""):
            if(dir =="Near"):
                addrData = LensCtrl.focusCurrentAddr + fineNum
                LimFocusMove(addrData)
            elif(dir =="Far"):
                addrData = LensCtrl.focusCurrentAddr - fineNum
                LimFocusMove(addrData)

        elif(key ==("q" or "Q")):
            dir = "Quit"
            break

def LimFocusMove(addrData):

    if ((LensCtrl.focusMaxAddr >= addrData) & (addrData > LensCtrl.focusMinAddr)):
        retval = LensCtrl.FocusMove(addrData)
        if (retval == DV.RET_SUCCESS):
            print("Addr = {} >> ".format(LensCtrl.focusCurrentAddr), end="")
    else:
        print("Limit", end= "")

def FineNumSet():
    global fineNum
    num = input("Current fine number = {} \nFine move step number = ".format(fineNum))
    fineNum = int(num)
