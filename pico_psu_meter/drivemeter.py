#to run standalone on the pico, file must be called main.py

#TODO:
# set gpio23 high for continuous PWM SMPS operation. 

# One ADC count represents...
MAX_VOLTS_OUT = 36
FULL_SCALE_COUNT = 4096
VOLTS_PER_INCREMENT = (MAX_VOLTS_OUT / FULL_SCALE_COUNT)
ISENSE_R_VAL_OHMS = 0.3

#initialisation
import array
import machine
import utime
from machine import Pin, Timer

# An 8-bit R2R ladder DAC is used to drive the meter via a
# single transistor V->I converter 
# Range of meter is 0 to 1mA
bit0 = Pin(0, Pin.OUT)
bit1 = Pin(1, Pin.OUT)
bit2 = Pin(2, Pin.OUT)
bit3 = Pin(3, Pin.OUT)
bit4 = Pin(4, Pin.OUT)
bit5 = Pin(5, Pin.OUT)
bit6 = Pin(6, Pin.OUT)
bit7 = Pin(7, Pin.OUT)

led = Pin(25, Pin.OUT)


# ADC Channels
#=============
# direct reading of output voltage
opVoltRdg = machine.ADC(0)
# current is read as a voltage across a 0.3 ohm resistor
opCurrRdg = machine.ADC(1)
# 0v output is measured to offset various physical effects
op0vRdg = machine.ADC(2)

# meter range indication leds
pin100m = Pin(8,  Pin.OUT)
pin250m = Pin(9,  Pin.OUT)
pin500m = Pin(10, Pin.OUT)
pin1v   = Pin(11, Pin.OUT)
pin2v5  = Pin(12, Pin.OUT)
pin5v   = Pin(13, Pin.OUT)
pin10v  = Pin(14, Pin.OUT)
pin25v  = Pin(15, Pin.OUT)
pin50v  = Pin(16, Pin.OUT)

# GPIO Pin 21 is used to detect current limit mode. 
pinILim = Pin(21, Pin.In)

# onboard led (channel 25) is used to indicate how much 
# time the processor is spending awake.  If it lights 
# up very brightly, things are getting bad.
led.value(0)
LED_state = True

# timer used to schedule measurements / update
meterUpdateTim = Timer()

### timer callbacks ###
    
# meter update timer callback
def meterUpdateTick(timer):
    led.high()
    updateRdgs()
    led.low()


### functions ###

#
# showRange
# Light one or more range LEDs according to the bit pattern given. 
#
def showRange(pattern):
    global pin100m 
    global pin250m
    global pin500m
    global pin1v
    global pin2v5
    global pin5v
    global pin10v
    global pin25v
    global pin50v
    
    if (pattern & 0x001 == 0):
        pin100m.low()
    else:
        pin100m.high()
        
    if (pattern & 0x002 == 0):
        pin250m.low()
    else:
        pin250m.high()
        
    if (pattern & 0x004 == 0):
        pin500m.low()
    else:
        pin500m.high()
        
    if (pattern & 0x008 == 0):
        pin1v.low()
    else:
        pin1v.high()
        
    if (pattern & 0x010 == 0):
        pin2v5.low()
    else:
        pin2v5.high()
        
    if (pattern & 0x020 == 0):
        pin5v.low()
    else:
        pin5v.high()
        
    if (pattern & 0x040 == 0):
        pin10v.low()
    else:
        pin10v.high()
        
    if (pattern & 0x080 == 0):
        pin25v.low()
    else:
        pin25v.high()
        
    if (pattern & 0x100 == 0):
        pin50v.low()
    else:
        pin50v.high()

#
# driveMeter
# Send a binary number out to the R-2R DAC which will drive the meter
# pointer to a particular position.  
#
def driveMeter(mask=0):   
    if (mask & 0x01 == 0):
        bit0.low()
    else:
        bit0.high()

    if (mask & 0x02 == 0):
        bit1.low()
    else:
        bit1.high()

    if (mask & 0x04 == 0):
        bit2.low()
    else:
        bit2.high()

    if (mask & 0x08 == 0):
        bit3.low()
    else:
        bit3.high()

    if (mask & 0x10 == 0):
        bit4.low()
    else:
        bit4.high()

    if (mask & 0x20 == 0):
        bit5.low()
    else:
        bit5.high()

    if (mask & 0x40 == 0):
        bit6.low()
    else:
        bit6.high()
                                
    if (mask & 0x80 == 0):
        bit7.low()
    else:
        bit7.high()
                                
#
# lampTest
# Show a startup pattern to indicate that all lamps / meter work. 
#
def lampTest():
    driveMeter(200) # full scale deflection. 
    showRange(0x1FF) # all range indicators on. 
    utime.sleep(1)
    driveMeter(0)
    showRange(0) # all range indicators off
    utime.sleep(0.5)


#
# given a value that would drive FSD in the current range and the 
# current value, determine the percentage of FSD that the meter 
# should be driven to.  Absolute values are given for each graticule 
# position.  The function interpolates for values between graticule 
# positions. 
# Meter calibration is done here. 
#TODO: This is ugly.  A table based solution would be t
def scaleMeterReading(fsd_val, val_now):
    global meterDriveIdx
    global meterDriveFilt
    # list DAC counts to drive indicator to each graticule. 
    pc0 = 31
    pc4 = 49
    pc8 = 57
    pc12 = 61
    pc16 = 70
    pc20 = 77
    pc24 = 86
    pc28 = 91
    pc32 = 98
    pc36 = 104
    pc40 = 110
    pc44 = 117
    pc48 = 122
    pc52 = 132
    pc56 = 137
    pc60 = 143
    pc64 = 150
    pc68 = 155
    pc72 = 159
    pc76 = 165
    pc80 = 171
    pc84 = 176
    pc88 = 181
    pc92 = 185
    pc96 = 193
    pc100 = 200
    pc104 = 205
    
    pcVal = val_now / fsd_val
    if pcVal > 1.04:
        pcVal = 1.04
        drive = pc104
    elif pcVal >= 1.0:
        pr = (pcVal - 1.0) / (1.04-1.0)
        drive = pc100 + int(pr*(pc104-pc100))
    elif pcVal >= 0.96:
        pr = (pcVal - 0.96) / (1.0 - 0.96)
        drive = pc96 + int(pr*(pc100-pc96))
    elif pcVal >= 0.92:
        pr = (pcVal - 0.92) / (0.96 - 0.92)
        drive = pc92 + int(pr*(pc96-pc92))
    elif pcVal >= 0.88:
        pr = (pcVal - 0.88) / (0.92 - 0.88)
        drive = pc88 + int(pr*(pc92-pc88))
    elif pcVal >= 0.84:
        pr = (pcVal - 0.84) / (0.88 - 0.84)
        drive = pc84 + int(pr*(pc88-pc84))
    elif pcVal >= 0.80:
        pr = (pcVal - 0.80) / (0.84 - 0.80)
        drive = pc80 + int(pr*(pc84-pc80))
    elif pcVal >= 0.76:
        pr = (pcVal - 0.76) / (0.80 - 0.76)
        drive = pc76 + int(pr*(pc80-pc76))
    elif pcVal >= 0.72:
        pr = (pcVal - 0.72) / (0.80 - 0.76)
        drive = pc72 + int(pr*(pc76-pc72))
    elif pcVal >= 0.68:
        pr = (pcVal - 0.68) / (0.72 - 0.68)
        drive = pc68 + int(pr*(pc72-pc68))
    elif pcVal >= 0.64:
        pr = (pcVal - 0.64) / (0.68 - 0.64)
        drive = pc64 + int(pr*(pc68-pc64))
    elif pcVal >= 0.60:
        pr = (pcVal - 0.60) / (0.64 - 0.60)
        drive = pc60 + int(pr*(pc64-pc60))
    elif pcVal >= 0.56:
        pr = (pcVal - 0.56) / (0.60 - 0.56)
        drive = pc56 + int(pr*(pc60-pc56))
    elif pcVal >= 0.52:
        pr = (pcVal - 0.52) / (0.56 - 0.52)
        drive = pc52 + int(pr*(pc56-pc52))
    elif pcVal >= 0.48:
        pr = (pcVal - 0.48) / (0.52 - 0.48)
        drive = pc48 + int(pr*(pc52-pc48))
    elif pcVal >= 0.44:
        pr = (pcVal - 0.44) / (0.48 - 0.44)
        drive = pc44 + int(pr*(pc48-pc44))
    elif pcVal >= 0.40:
        pr = (pcVal - 0.40) / (0.44 - 0.40)
        drive = pc40 + int(pr*(pc44-pc40))
    elif pcVal >= 0.36:
        pr = (pcVal - 0.36) / (0.40 - 0.36)
        drive = pc36 + int(pr*(pc40-pc36))
    elif pcVal >= 0.32:
        pr = (pcVal - 0.32) / (0.36 - 0.32)
        drive = pc32 + int(pr*(pc36-pc32))
    elif pcVal >= 0.28:
        pr = (pcVal - 0.28) / (0.32 - 0.28)
        drive = pc28 + int(pr*(pc32-pc28))
    elif pcVal >= 0.24:
        pr = (pcVal - 0.24) / (0.28 - 0.24)
        drive = pc24 + int(pr*(pc28-pc24))
    elif pcVal >= 0.20:
        pr = (pcVal - 0.20) / (0.24 - 0.20)
        drive = pc20 + int(pr*(pc24-pc20))
    elif pcVal >= 0.16:
        pr = (pcVal - 0.16) / (0.20 - 0.16)
        drive = pc16 + int(pr*(pc20-pc16))
    elif pcVal >= 0.12:
        pr = (pcVal - 0.12) / (0.16 - 0.12)
        drive = pc12 + int(pr*(pc16-pc12))
    elif pcVal >= 0.08:
        pr = (pcVal - 0.08) / (0.12 - 0.08)
        drive = pc8 + int(pr*(pc12-pc8))
    elif pcVal >= 0.04:
        pr = (pcVal - 0.04) / (0.08 - 0.04)
        drive = pc4 + int(pr*(pc8-pc4))
    else : # between 0.00 and 0.04
        pr = pcVal / 0.04
        drive = pc0 + int(pr*(pc4-pc0))
     
    # and finally, drive the meter...
        
    print ("%drive: ", drive)
    
    driveMeter(drive)

#
# Determine whether in Voltage or current mode
# and calculate range to use for driving meter.
# Uses a filter to prevent rapid range switching. TODO: remove the filter and change range selection method. 
#
#TODO: add hysteresis for range changes 
def calcModeAndRange(Volts, Curr):
    RANGE_50   = 0x100
    RANGE_25   = 0x080
    RANGE_10   = 0x040
    RANGE_5    = 0x020
    RANGE_2P5  = 0x010
    RANGE_1    = 0x008
    RANGE_500m = 0x004
    RANGE_250m = 0x002
    RANGE_100m = 0x001
    RANGE_CHANGE_FILTER_COUNT = 3
    global changeFilt
    global currentRange
    
    #TODO: read input pin from current mode detect
    vMode = True
    #for now
    if vMode == True:
        # voltage scales
        if Volts > 25:
            nextRange = RANGE_50
            fsVal = 50
        elif Volts > 10:
            nextRange = RANGE_25
            fsVal = 25
        elif Volts > 5:
            nextRange = RANGE_10
            fsVal = 10
        elif Volts > 2.5:
            nextRange = RANGE_5
            fsVal = 5
        elif Volts > 1:
            nextRange = RANGE_2P5
            fsVal = 2.5
        elif Volts > 0.5:
            nextRange = RANGE_1
            fsVal = 1
        elif Volts > 0.25:
            nextRange = RANGE_500m
            fsVal = 0.5
        elif Volts > 0.1:
            nextRange = RANGE_250m
            fsVal = 0.25
        else:
            nextRange = RANGE_100m
            fsVal = 0.1
    else:
        # current scales
        if Curr > 2.5:
            nextRange = RANGE_5
            fsVal = 5
        elif Curr > 1:
            nextRange = RANGE_2P5
            fsVal = 2.5
        elif Curr > 0.5:
            nextRange = RANGE_1
            fsVal = 1
        elif Curr > 0.25:
            nextRange = RANGE_500m
            fsVal = 0.5
        elif Curr > 0.1:
            nextRange = RANGE_250m
            fsVal = 0.25
        else:
            nextRange = RANGE_100m
            fsVal = 0.1
            
#    if changeFilt < RANGE_CHANGE_FILTER_COUNT:
#TODO: remove range change filtering.  Use hysteresis instead. 
    if changeFilt < 4:
        changeFilt += 1
    else:
        currentRange = nextRange
        showRange(currentRange)
        changeFilt = 0
        #scale meter position to range depending on v / i value. 
        if vMode == True:
            scaleMeterReading(fsVal, Volts)    
        else:
            scaleMeterReading(fsVal, Curr)    
 
#
# updateRdgs
# Read and average the readings for output voltage, output current and 
# the zero point to offset both of those from. 
# Readings are held as an integer value. 
#
def updateRdgs():
    global opVarr
    global opIarr
    global op0varr
    
    print ("arr len: ", len(opVarr))
    # Read all three ADCs and shift to give range 0 - 4096.
    # All arrays are the same length so just using size of first array
    for i in range(len(opVarr)):
        opVarr[i] = opVoltRdg.read_u16()>>4
        opIarr[i] = opCurrRdg.read_u16()>>4
        op0varr[i] = op0vRdg.read_u16()>>4
    
    # get averaged raw adc counts
    voltsVal = 0
    iVal = 0
    volt0Val = 0
    for i in range(len(opVarr)):
        voltsVal = voltsVal + opVarr[i]
        iVal = iVal + opIarr[i]
        volt0Val = volt0Val + op0varr[i]

    # averaged raw output voltage adc count    
    voltsVal = voltsVal / len(opVarr)
    voltsVal = int(voltsVal)
    
    # averaged raw output current adc count
    iVal = iVal / len(opIarr)
    iVal = int(iVal)
    
    # averaged raw 0V voltage adc count
    volt0Val = volt0Val / len(op0varr)
    volt0Val = int(volt0Val)

    # subtract 0v from output volts reading
    if voltsVal > volt0Val:
        voltsVal -= volt0Val
    else:
        # negative voltage!
        voltsVal = 0
        print("op volt error")  
    #scale to real voltage
    voltsOut = voltsVal* VOLTS_PER_INCREMENT
        
    if iVal > volt0Val:
        iVal = iVal-volt0Val
    else:
        # negative current!
        iVal = 0
        print ("op I error")

    iOut = iVal * VOLTS_PER_INCREMENT
    iOut /= ISENSE_R_VAL_OHMS

    calcModeAndRange(voltsOut, iOut)
    
    #divide by 16 to get 0 -256 range for driving meter
#    meterVal = voltsVal >> 4
#    driveMeter(meterVal)
    
    print("voltsVal: ", voltsVal)
    print("0vVal: ",volt0Val)
    print("iVal: ", iVal)
    print("voltsOut: ", voltsOut)
    print("iOut: ", iOut)
#    print("meterVal: ", meterVal)
    
    print(bit7.value(),bit6.value(), bit5.value(), bit4.value(), bit3.value(), bit2.value(), bit1.value(), bit0.value())
    
    print("Iactive: ")
    print(" ")

#
# main program.  
#
opVoltRdg = machine.ADC(0)
opVarr = [0, 0, 0, 0, 0, 0, 0, 0]
opCurrRdg = machine.ADC(1)
opIarr = [0, 0, 0, 0, 0, 0, 0, 0]
op0vRdg = machine.ADC(1)
op0varr = [0, 0, 0, 0, 0, 0, 0, 0]
lampTest()
changeFilt = 0
currentRange = 0
meterDriveFilt = [0, 0, 0, 0]
meterDriveIdx = 0

# The meter update timer schedules running of the meter update code
meterUpdateTim.init(freq=10, mode=Timer.PERIODIC, callback=meterUpdateTick)


