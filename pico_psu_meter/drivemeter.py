
# _________________________________________
#/ This is a program that manages the      \
#| display front panel of a Power Supply   |
#| Unit from Practical Electronics 1978.   |
#| Design of the PSU was by R. Lawrence    |
#| B.Sc. This program drives a moving coil |
#| meter and lights a few LEDs on the      |
#| front panel to indicate what the range  |
#| of the meter is, whether the PSU is in  |
#| current limit mode etc. The program     |
#| monitors a current-limit indicator      |
#| light on the PSU control board to       |
#| determine whether to show volts or      |
#| amps. It doesn't need to be fast -      |
#| polling is fine. The PSU's overcurrent  |
#| detection is done in hardware. This is  |
#| just monitoring and pretty displaying   |
#| things. It runs on the Raspberry Pi     |
#| pico board but with R7 removed and a    |
#| very highly filtered ADC_VREF supply    |
#| provided externally for the small       |
#\ voltage measurements                    /
# -----------------------------------------
#        \   ^__^
#         \  (oo)\_______
#            (__)\       )\/\
#                ||----w |
#                ||     ||
#

# note: to run standalone on the pico, file must be called main.py

#TODO:
# set gpio23 high for continuous PWM SMPS operation. 

# One ADC count represents...
MAX_VOLTS_OUT = 36
FULL_SCALE_COUNT = 4096
VOLTS_PER_ADC_STEP = (MAX_VOLTS_OUT / FULL_SCALE_COUNT)
ISENSE_R_VAL_OHMS = 0.3

MAX_AMPS_OUT = 6
AMPS_PER_ADC_STEP = (MAX_AMPS_OUT / FULL_SCALE_COUNT)

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
pinILim = Pin(21, Pin.IN)

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
    updateRdgs()  # and do everything else...
    led.low()


#
############ showRange ############
#        _                   _____                        
#       | |                 |  __ \                       
#    ___| |__   _____      _| |__) |__ _ _ __   __ _  ___ 
#   / __| '_ \ / _ \ \ /\ / /  _  // _` | '_ \ / _` |/ _ \
#   \__ \ | | | (_) \ V  V /| | \ \ (_| | | | | (_| |  __/
#   |___/_| |_|\___/ \_/\_/ |_|  \_\__,_|_| |_|\__, |\___|
#                                               __/ |     
#                                              |___/      
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
                                

############# lampTest ############
#    _                    _______        _   
#   | |                  |__   __|      | |  
#   | | __ _ _ __ ___  _ __ | | ___  ___| |_ 
#   | |/ _` | '_ ` _ \| '_ \| |/ _ \/ __| __|
#   | | (_| | | | | | | |_) | |  __/\__ \ |_ 
#   |_|\__,_|_| |_| |_| .__/|_|\___||___/\__|
#                     | |                    
#                     |_|                    
# An impressive display of meter needle movement and LED lighting when the
# program starts running.  Proves that both are working. A half second blanking
# is done to allow the observer to recover. 
# 
def lampTest():
    driveMeterToPercentFS(100)
    showRange(RANGE_INDICATOR_LAMPS_ALL)
    utime.sleep(1)
    driveMeterToPercentFS(0)
    showRange(RANGE_INDICATOR_LAMPS_NONE)
    utime.sleep(0.5)


#
############# driveMeterToPercentFS #############
#        _      _           __  __      _         _______    _____                        _   ______ _____ 
#       | |    (_)         |  \/  |    | |       |__   __|  |  __ \                      | | |  ____/ ____|
#     __| |_ __ ___   _____| \  / | ___| |_ ___ _ __| | ___ | |__) |__ _ __ ___ ___ _ __ | |_| |__ | (___  
#    / _` | '__| \ \ / / _ \ |\/| |/ _ \ __/ _ \ '__| |/ _ \|  ___/ _ \ '__/ __/ _ \ '_ \| __|  __| \___ \ 
#   | (_| | |  | |\ V /  __/ |  | |  __/ ||  __/ |  | | (_) | |  |  __/ | | (_|  __/ | | | |_| |    ____) |
#    \__,_|_|  |_| \_/ \___|_|  |_|\___|\__\___|_|  |_|\___/|_|   \___|_|  \___\___|_| |_|\__|_|   |_____/ 
#                                                                                                          
#                                                                                                          
# Given the percentage of Full Scale Deflection that the needle should indicate,
# calculate the DAC count that the meter should be driven with. 
# 
def driveMeterToPercentFS(pcVal):

    ###########  METER CALIBRATION VALUES ##########
    # The meter has 25 graticules, so each represents 4% of Full Scale
    # Deflection.  Below this comment is a list of DAC counts to drive the
    # indicator to each graticule because the system is not really linear.
    # Calibration used a test program to read an ADC input driven from a
    # potentiometer and print out the ADC count while the needle was moved to
    # each graticule position using the potentiometer.  
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
    
    pcVal = pcVal / 100 # because this evolved using per-unit values. 
    # needle is never driven beyond 4% past the last graticule. 
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
     
    # and finally, send the drive value to the Digital to Analogue Converter...
    driveMeterDAC(drive) 
        
    # print ("%drive: ", drive)
    

############# calcModeAndRange ############
#            _      __  __           _                         _ _____                        
#           | |    |  \/  |         | |        /\             | |  __ \                       
#   ___ __ _| | ___| \  / | ___   __| | ___   /  \   _ __   __| | |__) |__ _ _ __   __ _  ___ 
#  / __/ _` | |/ __| |\/| |/ _ \ / _` |/ _ \ / /\ \ | '_ \ / _` |  _  // _` | '_ \ / _` |/ _ \
# | (_| (_| | | (__| |  | | (_) | (_| |  __// ____ \| | | | (_| | | \ \ (_| | | | | (_| |  __/
#  \___\__,_|_|\___|_|  |_|\___/ \__,_|\___/_/    \_\_| |_|\__,_|_|  \_\__,_|_| |_|\__, |\___|
#                                                                                   __/ |     
#                                                                                  |___/      
# Determine whether we should be displaying Voltage or current and calculate a
# suitable display range for the value being measured. 
# 
# Hysteresis is applied when changing down through ranges via the limit definitions. 
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

    # Defines limits of voltage and current for each range. 
    RANGE_50_LOW_LIM = 20.0
    RANGE_25_HIGH_LIM = 25.0
    RANGE_25_LOW_LIM = 8.0
    RANGE_10_HIGH_LIM = 10.0
    RANGE_10_LOW_LIM = 4.0
    RANGE_5_HIGH_LIM = 5.0
    RANGE_5_LOW_LIM = 2.0
    RANGE_2P5_HIGH_LIM = 2.5
    RANGE_2P5_LOW_LIM = 0.8
    RANGE_1_HIGH_LIM = 1.0
    RANGE_1_LOW_LIM = 0.4
    RANGE_500m_HIGH_LIM = 0.5
    RANGE_500m_LOW_LIM = 0.2
    RANGE_250m_HIGH_LIM = 0.25
    RANGE_250m_LOW_LIM = 0.08
    RANGE_100m_HIGH_LIM = 0.1

    # Read pinILim to determine whether displaying volts or amps
    vMode = pinILim.value()
    #print ("vMode: ", vMode)
    # TODO: drive the mode indicator relay lamp here. 

    if vMode == True:
        # voltage scales
        if rangeVolts == RANGE_50:
            # there is no higher voltage range. 
            if Volts < RANGE_50_LOW_LIM:
                rangeVolts = RANGE_25
                showRange(RANGE_INDICATOR_LAMP_25)
        elif rangeVolts == RANGE_25:
            if Volts > RANGE_25_HIGH_LIM:
                rangeVolts = RANGE_50
                showRange(RANGE_INDICATOR_LAMP_50)
            elif Volts < RANGE_25_LOW_LIM:
                rangeVolts = RANGE_10
                showRange(RANGE_INDICATOR_LAMP_10)
        elif rangeVolts == RANGE_10:
            if Volts > RANGE_10_HIGH_LIM:
                rangeVolts = RANGE_25
                showRange(RANGE_INDICATOR_LAMP_25)
            elif Volts < RANGE_10_LOW_LIM:
                rangeVolts = RANGE_5
                showRange(RANGE_INDICATOR_LAMP_5)
        elif rangeVolts == RANGE_5:
            if Volts > RANGE_5_HIGH_LIM:
                rangeVolts = RANGE_10
                showRange(RANGE_INDICATOR_LAMP_10)
            elif Volts < RANGE_5_LOW_LIM:
                rangeVolts = RANGE_2P5
                showRange(RANGE_INDICATOR_LAMP_2P5)
        elif rangeVolts == RANGE_2P5:
            if Volts > RANGE_2P5_HIGH_LIM:
                rangeVolts = RANGE_5
                showRange(RANGE_INDICATOR_LAMP_5)
            elif Volts < RANGE_2P5_LOW_LIM:
                rangeVolts = RANGE_1
                showRange(RANGE_INDICATOR_LAMP_1)
        elif rangeVolts == RANGE_1:
            if Volts > RANGE_1_HIGH_LIM:
                rangeVolts = RANGE_2P5
                showRange(RANGE_INDICATOR_LAMP_2P5)
            elif Volts < RANGE_1_LOW_LIM:
                rangeVolts = RANGE_500m
                showRange(RANGE_INDICATOR_LAMP_500m)
        elif rangeVolts == RANGE_500m:
            if Volts > RANGE_500m_HIGH_LIM:
                rangeVolts = RANGE_1
                showRange(RANGE_INDICATOR_LAMP_1)
            elif Volts < RANGE_500m_LOW_LIM:
                rangeVolts = RANGE_250m
                showRange(RANGE_INDICATOR_LAMP_250m)
        elif rangeVolts == RANGE_250m:
            if Volts > RANGE_250m_HIGH_LIM:
                rangeVolts = RANGE_500m
                showRange(RANGE_INDICATOR_LAMP_500m)
            elif Volts < RANGE_250m_LOW_LIM:
                rangeVolts = RANGE_100m
                showRange(RANGE_INDICATOR_LAMP_100m)
        else: # rangeVolts is 100m or invalid. 
            if Volts > RANGE_100m_HIGH_LIM:
                rangeVolts = RANGE_250m
                showRange(RANGE_INDICATOR_LAMP_250m)
            else:
                rangeVolts = RANGE_100m
                showRange(RANGE_INDICATOR_LAMP_100m)
            # there are no lower voltage ranges
        # Now calculate the percentage of full scale for volts...
        perCentDrive = rangeVolts / Volts
        perCentDrive = perCentDrive * 100
        driveMeterToPercentFS(perCentDrive) 
        # here endeth the voltage meter driving. 

    else:
        # PSU is in current limit mode.  Display Current. 
        if rangeAmps == RANGE_10:
            # No point changing to higher ranges. The output transistor will
            # melt if current gets any higher. 
            if Curr < RANGE_10_LOW_LIM:
                rangeAmps = RANGE_5
                showRange(RANGE_INDICATOR_LAMP_5)
        elif rangeAmps == RANGE_5:
            if Curr > RANGE_5_HIGH_LIM:
                rangeAmps = RANGE_10
                showRange(RANGE_INDICATOR_LAMP_10)
            elif Curr < RANGE_5_LOW_LIM:
                rangeAmps = RANGE_2P5
                showRange(RANGE_INDICATOR_LAMP_2P5)
        elif rangeAmps == RANGE_2P5:
            if Curr > RANGE_2P5_HIGH_LIM:
                rangeAmps = RANGE_5
                showRange(RANGE_INDICATOR_LAMP_5)
            elif Curr < RANGE_2P5_LOW_LIM:
                rangeAmps = RANGE_1
                showRange(RANGE_INDICATOR_LAMP_1)
        elif rangeAmps == RANGE_1:
            if Curr > RANGE_1_HIGH_LIM:
                rangeAmps = RANGE_2P5
                showRange(RANGE_INDICATOR_LAMP_2P5)
            elif Curr < RANGE_1_LOW_LIM:
                rangeAmps = RANGE_500m
                showRange(RANGE_INDICATOR_LAMP_500m)
        elif rangeAmps == RANGE_500m:
            if Curr > RANGE_500m_HIGH_LIM:
                rangeAmps = RANGE_1
                showRange(RANGE_INDICATOR_LAMP_1)
            elif Curr < RANGE_500m_LOW_LIM:
                rangeAmps = RANGE_250m
                showRange(RANGE_INDICATOR_LAMP_250m)
        elif rangeAmps == RANGE_250m:
            if Curr > RANGE_250m_HIGH_LIM:
                rangeAmps = RANGE_500m
                showRange(RANGE_INDICATOR_LAMP_500m)
            elif Curr < RANGE_250m_LOW_LIM:
                rangeAmps = RANGE_100m
                showRange(RANGE_INDICATOR_LAMP_100m)
        else: # rangeAmps is 100m or invalid. 
            if Curr > RANGE_100m_HIGH_LIM:
                rangeAmps = RANGE_250m
                showRange(RANGE_INDICATOR_LAMP_250m)
            else:
                rangeAmps = RANGE_100m
                showRange(RANGE_INDICATOR_LAMP_100m)
            # there are no lower current ranges
        # Now calculate the percentage of full scale for current...
        perCentDrive = rangeAmps / Curr
        perCentDrive = perCentDrive * 100
        driveMeterToPercentFS(perCentDrive)
    # end of changing and scaling current ranges. 



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
    voltsOut = voltsVal* VOLTS_PER_ADC_STEP
        
    if iVal > volt0Val:
        iVal = iVal-volt0Val
    else:
        # negative current!  Maybe light the amber measurement warning lamp?  
        iVal = 0
        print ("op I error")

    iOut = iVal * AMPS_PER_ADC_STEP

    calcModeAndRange(voltsOut, iOut)
    
# remnants of the test program to display the DAC bits...    
#    print("voltsVal: ", voltsVal)
#    print("0vVal: ",volt0Val)
#    print("iVal: ", iVal)
#    print("voltsOut: ", voltsOut)
#    print("iOut: ", iOut)
#    print("meterVal: ", meterVal)
    
#    print(bit7.value(),bit6.value(), bit5.value(), bit4.value(), bit3.value(), bit2.value(), bit1.value(), bit0.value())
    
#    print("Iactive: ")
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
opVoltRdg = machine.ADC(0)
opVarr = [0, 0, 0, 0, 0, 0, 0, 0]
opCurrRdg = machine.ADC(1)
opIarr = [0, 0, 0, 0, 0, 0, 0, 0]
op0vRdg = machine.ADC(1) #TODO: use the correct pins. 
op0varr = [0, 0, 0, 0, 0, 0, 0, 0]
lampTest()
currentRange = 0

# The meter update timer schedules running of the meter update code. 
# get it to run as fast as possible.  
# Will likely need to slow it down if using print statements for testing. 
meterUpdateTim.init(freq=10, mode=Timer.PERIODIC, callback=meterUpdateTick)


