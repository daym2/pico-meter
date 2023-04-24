
# _________________________________________
#/                                         \
#| Nothing much to see here.  This is just |
#| a program that uses the voltage pot to  |
#| read in ADC values, scales them to      |
#| useable values then writes these to the |
#| DAC so that the settings for each       |
#| graticule position can be easily        |
#| obtained.                               |
#\                                         /
# -----------------------------------------
#        \   ^__^
#         \  (oo)\_______
#            (__)\       )\/\
#                ||----w |
#                ||     ||
#


#initialisation
import array
import machine
import utime
from machine import Pin, Timer

# set gpio23 high for continuous PWM SMPS operation.
modeSmps = Pin(23, Pin.OUT)
modeSmps.value(1)

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
pin100m = Pin(10,  Pin.OUT)
pin250m = Pin(11,  Pin.OUT)
pin500m = Pin(12, Pin.OUT)
pin1v   = Pin(13, Pin.OUT)
pin2v5  = Pin(14, Pin.OUT)
pin5v   = Pin(15, Pin.OUT)
pin10v  = Pin(16, Pin.OUT)


pin25v  = Pin(17, Pin.OUT)
pin50v  = Pin(18, Pin.OUT)

# GPIO Pin 21 is used to detect current limit mode.
# Input = 0 when current limit is active. 
pinILim = Pin(21, Pin.IN)
# GPIO Pin 20 drives the red front panel Imode LED to mirror the control board LED.
PinIlimFlag = Pin(20, Pin.OUT)
# GPIO Pin 22 compliments to indicate voltage mode. 
PinVoltsFlag = Pin(22, Pin.OUT)

# GPIO Pin 19 is the power indicator.
PinPwr = Pin(19, Pin.OUT)

# onboard led (channel 25) is used to indicate how much time the processor is
# spending awake.  If it never switches off, slow down the scheduling timer. 
led.value(0)

# timer used to schedule measurements / update
meterUpdateTim = Timer()

### Aliases for the indicator lamps ###
RANGE_INDICATOR_LAMP_100m = 0x001
RANGE_INDICATOR_LAMP_250m = 0x002
RANGE_INDICATOR_LAMP_500m = 0x004
RANGE_INDICATOR_LAMP_1 =    0x008
RANGE_INDICATOR_LAMP_2P5 =  0x010
RANGE_INDICATOR_LAMP_5 =    0x020
RANGE_INDICATOR_LAMP_10 =   0x040
RANGE_INDICATOR_LAMP_25 =   0x080
RANGE_INDICATOR_LAMP_50 =   0x100
RANGE_INDICATOR_LAMPS_ALL = 0x1FF
RANGE_INDICATOR_LAMPS_NONE = 0


### functions ###

############ meter update timer callback #############
#                   _            _    _           _       _    _______ _                  _______ _      _    
#                  | |          | |  | |         | |     | |  |__   __(_)                |__   __(_)    | |   
#    _ __ ___   ___| |_ ___ _ __| |  | |_ __   __| | __ _| |_ ___| |   _ _ __ ___   ___ _ __| |   _  ___| | __
#   | '_ ` _ \ / _ \ __/ _ \ '__| |  | | '_ \ / _` |/ _` | __/ _ \ |  | | '_ ` _ \ / _ \ '__| |  | |/ __| |/ /
#   | | | | | |  __/ ||  __/ |  | |__| | |_) | (_| | (_| | ||  __/ |  | | | | | | |  __/ |  | |  | | (__|   < 
#   |_| |_| |_|\___|\__\___|_|   \____/| .__/ \__,_|\__,_|\__\___|_|  |_|_| |_| |_|\___|_|  |_|  |_|\___|_|\_\
#                                      | |                                                                    
#                                      |_|                                                                    
# 
# Called periodically to monitor things and update indicators / meter position. 
def meterUpdateTick(timer):
    led.high()
    print("start update readings")
    updateRdgs()  # and do everything else...
    print("end update readings")
    led.low()


#
############ driveMeterDAC ############
#        _      _           __  __      _            _____          _____ 
#       | |    (_)         |  \/  |    | |          |  __ \   /\   / ____|
#     __| |_ __ ___   _____| \  / | ___| |_ ___ _ __| |  | | /  \ | |     
#    / _` | '__| \ \ / / _ \ |\/| |/ _ \ __/ _ \ '__| |  | |/ /\ \| |     
#   | (_| | |  | |\ V /  __/ |  | |  __/ ||  __/ |  | |__| / ____ \ |____ 
#    \__,_|_|  |_| \_/ \___|_|  |_|\___|\__\___|_|  |_____/_/    \_\_____|
#                                                                         
#                                                                         
# Send a binary number out to the R-2R Digital to Analogue Converter which will
# drive the meter pointer to the required position. The value is masked to write
# out the drive value bit by bit. 
# 
def driveMeterDAC(dacValue=0):   
    if (dacValue & 0x01 == 0):
        bit0.low()
    else:
        bit0.high()

    if (dacValue & 0x02 == 0):
        bit1.low()
    else:
        bit1.high()

    if (dacValue & 0x04 == 0):
        bit2.low()
    else:
        bit2.high()

    if (dacValue & 0x08 == 0):
        bit3.low()
    else:
        bit3.high()

    if (dacValue & 0x10 == 0):
        bit4.low()
    else:
        bit4.high()

    if (dacValue & 0x20 == 0):
        bit5.low()
    else:
        bit5.high()

    if (dacValue & 0x40 == 0):
        bit6.low()
    else:
        bit6.high()
                                
    if (dacValue & 0x80 == 0):
        bit7.low()
    else:
        bit7.high()
                                

        


############# updateRdgs ##############
#                  _       _       _____     _           
#                 | |     | |     |  __ \   | |          
#  _   _ _ __   __| | __ _| |_ ___| |__) |__| | __ _ ___ 
# | | | | '_ \ / _` |/ _` | __/ _ \  _  // _` |/ _` / __|
# | |_| | |_) | (_| | (_| | ||  __/ | \ \ (_| | (_| \__ \
#  \__,_| .__/ \__,_|\__,_|\__\___|_|  \_\__,_|\__, |___/
#       | |                                     __/ |    
#       |_|                                    |___/     
# Read and average the readings for output voltage, output current and 
# the zero point from which both of those are referenced. 
# Readings are held as integer values. 
#
def updateRdgs():
    global opVarr
    global opIarr
    global op0varr
    
    # Read all three ADCs and shift to give range 0 - 4096.
    # All arrays are the same length so just using size of first array
    for i in range(len(opVarr)):
        opVarr[i] = opVoltRdg.read_u16()>>4
#        print("rdg ", i, " Val: ", opVarr[i])
        op0varr[i] = op0vRdg.read_u16()>>4
    
    # get averaged raw adc counts
    voltsVal = 0
    volt0Val = 0
    for i in range(len(opVarr)):
        voltsVal = voltsVal + opVarr[i]
        volt0Val = volt0Val + op0varr[i]

    # averaged raw output voltage adc count    
    voltsVal = voltsVal / len(opVarr)
    voltsVal = int(voltsVal)
    
    # averaged raw 0V voltage adc count
    volt0Val = volt0Val / len(op0varr)
    volt0Val = int(volt0Val)

    # subtract 0v from output volts reading
    if voltsVal > volt0Val:
        voltsVal -= volt0Val
    else:
        print("op volt error")  
        
    # divide by 10 because it's a big number, then write to the DAC.
    voltsVal = int(voltsVal / 10)
    if voltsVal < 220:
        driveMeterDAC(voltsVal) 

    print("voltsVal: ", voltsVal)
    print("0vVal: ",volt0Val)
#    print("voltsOut: ", voltsOut)
#    print("meterVal: ", meterVal)
    
    print(bit7.value(),bit6.value(), bit5.value(), bit4.value(), bit3.value(), bit2.value(), bit1.value(), bit0.value())
    
#    print(" ")



############ main program ###########
#                    _                                                   
#                   (_)                                                  
#    _ __ ___   __ _ _ _ __    _ __  _ __ ___   __ _ _ __ __ _ _ __ ___  
#   | '_ ` _ \ / _` | | '_ \  | '_ \| '__/ _ \ / _` | '__/ _` | '_ ` _ \ 
#   | | | | | | (_| | | | | | | |_) | | | (_) | (_| | | | (_| | | | | | |
#   |_| |_| |_|\__,_|_|_| |_| | .__/|_|  \___/ \__, |_|  \__,_|_| |_| |_|
#                             | |               __/ |                    
#                             |_|              |___/                     
#
opVoltRdg = machine.ADC(2)
opVarr = [0, 0, 0, 0, 0, 0, 0, 0]
op0vRdg = machine.ADC(0)
op0varr = [0, 0, 0, 0, 0, 0, 0, 0]
PinPwr.value(1) #power indicator

# The meter update timer schedules running of the meter update code. 
# get it to run as fast as possible.  
# Will likely need to slow it down if using print statements for testing. 
#meterUpdateTim.init(freq=10, mode=Timer.PERIODIC, callback=meterUpdateTick)
meterUpdateTim.init(freq=5, mode=Timer.PERIODIC, callback=meterUpdateTick)


