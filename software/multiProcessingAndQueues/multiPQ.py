import spidev
import time
import math
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob
from spiDevExp import spiExpanded
from multiprocessing import Process, Queue
from mcp4821DAC import mcp4821
from mcp3008ADC import mcp3008

V_KNOB_CLK_PIN = 24
V_KNOB_DT_PIN = 23
I_KNOB_CLK_PIN = 15
I_KNOB_DT_PIN = 14
LCD_ON_OFF_PIN = 18
LCD_RS_PIN = 25
CLIM_PIN = 4

ADC_CH_GND = 0
ADC_CH_5V0 = 1
ADC_CH_3V3 = 2
ADC_CH_IMON = 3
ADC_CH_VSENS = 4
ADC_CH_VTEMP = 5
ADC_CH_ISET = 6
ADC_CH_VSET = 7

HYST_LOW = 50
HYST_HIGH = 100

# This is needed because I could not find other way to read two GPIOs at the same time. 
# pigpio helps and it's daemon has to be started 
from os import system
system("sudo pigpiod")

# This is needed to interprocess communication, queue size is not experimented.
voltageQ = Queue(maxsize=20) 
currentQ = Queue(maxsize=20) 

# Turn off the LCD and turn on after it has been initialised
GPIO.setmode(GPIO.BCM)
GPIO.setup(LCD_ON_OFF_PIN, GPIO.OUT)
GPIO.output(LCD_ON_OFF_PIN, True)

GPIO.setup(4, GPIO.IN)

spiADC = spiExpanded(0, mode = 0)
adc = mcp3008(spiADC, 4096)
    
spiLcd = spiExpanded(3, mode = 0)
lcd = MIDAS_LCD.MidasLcd(spiLcd, LCD_RS_PIN)
    
spiVDac = spiExpanded(2, mode = 0)
vDAC = mcp4821(spiVDac)
    
spiIDac = spiExpanded(1, mode = 0)
iDAC = mcp4821(spiIDac)

vValues = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
remIndexMin = [0, 0, 0, 0, 0, 0, 0, 0]
remIndexMax = []

vKnob = RotaryKnob.rotKnob(clkPin = V_KNOB_CLK_PIN, dtPin = V_KNOB_DT_PIN, countMin = 0, countMax = 1200, highSpeedThrs = 15, highSpeedStep = 100)
vKnob.open()
iKnob = RotaryKnob.rotKnob(clkPin = I_KNOB_CLK_PIN, dtPin = I_KNOB_DT_PIN, countMin = 0, countMax = 999, highSpeedThrs = 15, highSpeedStep = 100)
iKnob.open()

iKnob.InitialiseCounter(500)
#vKnob.InitialiseCounter(250)


def loop_knob():
    while 1:
        voltageQ.put(vKnob.updateKnob())        
        currentQ.put(iKnob.updateKnob())
#def loop_knob


def loop_spi():    
    
    #Turn On LCD
    GPIO.output(LCD_ON_OFF_PIN, False)   
    newVoltage = 0
    lastSavedVoltage = 1
    newCurrent = 0
    limVoltage = 0
    limCurrent = 0
    lastSavedCurrent = 1
    lcd.lcdWriteLoc("SET ", 0, 0)
    lastTimeSet = 0
    lastTimeOut = 0
    numOfSmaples = 0
    currentLimOn = False
    isVoltageErrorOn = False
    actVoltageNow = 0
    
    while 1: 
        
        newVoltage = voltageQ.get()
        newCurrent = currentQ.get()
        currentTime = time.time()        

        if(currentTime - lastTimeSet > 0.35):
            lcd.lcdWriteLoc("%.2fV %dmA" % (newVoltage/100.0, newCurrent), 0, 4, 12)
            vDAC.setVoltage(newVoltage)
            iDAC.setVoltage(newCurrent)
            
            actVoltageNow = adc.read_adcMilliVolts(ADC_CH_VSENS)
            if(numOfSmaples < len(vValues)):
                vValues[numOfSmaples] = actVoltageNow
                numOfSmaples += 1
            else:
                vValues[0] = actVoltageNow
                numOfSmaples = 1
            lastTimeSet = currentTime
            
            actVoltageMedian = 0
            
            for r in range(len(remIndexMin)):
                min_value = min(vValues)
                min_index = vValues.index(min_value)   
                remIndexMin[r] = min_index 
                vValues[min_index] = 99999
                
            for r in range(len(remIndexMax)):
                max_value = max(vValues)
                max_index = vValues.index(max_value)
                remIndexMax[r] = max_index 
                vValues[max_index] = -1
    
            for r in range(len(remIndexMin)):
                vValues[remIndexMin[r]] = 0
                
            for r in range(len(remIndexMax)):
                vValues[remIndexMax[r]] = 0

            n = 0
            for x in vValues:
                if x != 0:
                    n += 1
                    actVoltageMedian += x 

            if(n == 0):
                n = 1
            actVoltageMedian = actVoltageMedian / n

            iMonVoltage = adc.read_adcMilliVolts(ADC_CH_IMON)
            iMonVoltage = int(math.ceil(iMonVoltage / 5.0)) * 5
            
            #Reset limiting conditions, either the knobs are turned or the currentConsumption falls less then 10mA less than the limit
            if(((limVoltage != newVoltage) or (limCurrent != newCurrent) or (iMonVoltage < 10)) and (currentLimOn == True)):
                currentLimOn = False
                #print("Reset")
            
            #Save Limiting settings
            if((GPIO.input(CLIM_PIN) == 0) and (currentLimOn == False)):
                limVoltage = newVoltage
                limCurrent = newCurrent
                currentLimOn = True
                #print("Latch")
            
            
               
            if(actVoltageNow - newVoltage > 200):
                #print("VOLTAGE ERROR")
                lcd.lcdWriteLoc("ERR %.2fV %dmA" % ((actVoltageMedian)/100.0, iMonVoltage), 1, 0, 16)
            else:
                if(currentLimOn == True):
                    lcd.lcdWriteLoc("LIM %.2fV %dmA" % ((actVoltageMedian)/100.0, iMonVoltage), 1, 0, 16)
                else:
                    lcd.lcdWriteLoc("OUT %.2fV %dmA" % ((newVoltage)/100.0, iMonVoltage), 1, 0, 16)
#def loop_spi()


    
try:
    
    p1 = Process(target=loop_knob)
    p2 = Process(target=loop_spi)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
    
except KeyboardInterrupt: # Ctrl+C pressed, so
    print("kapatiyoz!!!!!!!!!!!")
    vKnob.Close()
    iKnob.Close()
    vDAC.Close() #close the port before exit
    iDAC.Close() #close the port before exit
    lcd.Close()
    GPIO.cleanup()
    
    
    
#end try






