import spidev
import time
import math
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob
from spiDevExp import spiExpanded
from multiprocessing import Process, Queue, Array
from mcp4821DAC import mcp4821
from mcp3008ADC import mcp3008
import pushButton
import os.path
import csv

V_KNOB_CLK_PIN = 24
V_KNOB_DT_PIN = 23
I_KNOB_CLK_PIN = 15
I_KNOB_DT_PIN = 14
LCD_ON_OFF_PIN = 18
LCD_RS_PIN = 25
CLIM_PIN = 4
PB_YELLOW = 6
PB_RED = 13
PB_BLUE = 19

ADC_CH_GND = 0
ADC_CH_5V0 = 1
ADC_CH_3V3 = 2
ADC_CH_IMON = 3
ADC_CH_VSENS = 4
ADC_CH_VTEMP = 5
ADC_CH_ISET = 6
ADC_CH_VSET = 7

RED_PRESET_V = 0
RED_PRESET_I = 1
YELLOW_PRESET_V = 2
YELLOW_PRESET_I = 3
BLUE_PRESET_V = 4
BLUE_PRESET_I = 5


# This is needed because I could not find other way to read two GPIOs at the same time. 
# pigpio helps and it's daemon has to be started 
from os import system
system("sudo pigpiod")

# This is needed to interprocess communication, queue size is not experimented.
voltageQ = Queue(maxsize=20) 
currentQ = Queue(maxsize=20) 

redPresetRecallQ = Queue(maxsize=5) 
redPresetStoreQ = Queue(maxsize=5) 
yellowPresetRecallQ = Queue(maxsize=5) 
yellowPresetStoreQ = Queue(maxsize=5) 
bluePresetRecallQ = Queue(maxsize=5) 
bluePresetStoreQ = Queue(maxsize=5) 


# Turn off the LCD and turn on after it has been initialised
GPIO.setmode(GPIO.BCM)
GPIO.setup(LCD_ON_OFF_PIN, GPIO.OUT)
GPIO.output(LCD_ON_OFF_PIN, True)


GPIO.setup(PB_YELLOW, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(PB_RED, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(PB_BLUE, GPIO.IN,pull_up_down=GPIO.PUD_UP)
redButton = pushButton.pushButtonDev(PB_RED)
yellowButton = pushButton.pushButtonDev(PB_YELLOW)
blueButton = pushButton.pushButtonDev(PB_BLUE)

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

defaultPresets = [500,250,330,200,1200,500]

def loop_knob(defaultPresets, viPresets):
    

    
    while 1:
        redPresetRecallStat = redPresetRecallQ.get()
        yellowPresetRecallStat = yellowPresetRecallQ.get()
        bluePresetRecallStat = bluePresetRecallQ.get()
        
        if(redPresetRecallStat == True):
            vKnob.InitialiseCounter(viPresets[RED_PRESET_V])
            iKnob.InitialiseCounter(viPresets[RED_PRESET_I])

        if(yellowPresetRecallStat == True):
            vKnob.InitialiseCounter(viPresets[YELLOW_PRESET_V])
            iKnob.InitialiseCounter(viPresets[YELLOW_PRESET_I])
            
        if(bluePresetRecallStat == True):
            vKnob.InitialiseCounter(viPresets[BLUE_PRESET_V])
            iKnob.InitialiseCounter(viPresets[BLUE_PRESET_I])
        
        voltageQ.put(vKnob.updateKnob())        
        currentQ.put(iKnob.updateKnob())
#def loop_knob


def loop_spi(defaultPresets, viPresets):    
    
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
    actVoltage = 0
    redPresetStoreStat = False
    yellowPresetStoreStat = False
    bluePresetStoreStat = False
    presetChanged = False

    #read the presets and store them   
    for i, val in enumerate(defaultPresets): 
        viPresets[i] = int(val)  

    while 1:        
        newVoltage = voltageQ.get()
        newCurrent = currentQ.get()
        redPresetStoreStat = redPresetStoreQ.get()
        yellowPresetStoreStat = yellowPresetStoreQ.get()
        bluePresetStoreStat = bluePresetStoreQ.get()
        currentTime = time.time()        
        
        if(currentTime - lastTimeSet > 0.2):
            lcd.lcdWriteLoc("%.2fV %dmA" % (newVoltage/100.0, newCurrent), 0, 4, 12)
                        
            vDAC.setVoltage(newVoltage)
            iDAC.setVoltage(newCurrent)
            
            actVoltage = adc.read_adcMilliVolts(ADC_CH_VSENS)
        
            iMonVoltage = adc.read_adcMilliVolts(ADC_CH_IMON)/1.2
            iMonVoltage = int(math.ceil(iMonVoltage / 5.0)) * 5
            
            #Reset limiting conditions, either the knobs are turned or the currentConsumption falls less then 10mA less than the limit
            
            if(((limVoltage != newVoltage) or (limCurrent != newCurrent) or (iMonVoltage - limCurrent < 5)) and (currentLimOn == True)):                
                currentLimOn = False
                #print("Reset")
            
            #Save Limiting settings
            if((GPIO.input(CLIM_PIN) == 0) and (currentLimOn == False)):
                limVoltage = newVoltage
                limCurrent = newCurrent
                currentLimOn = True
                #print("Latch")
            
            #Preset Save or show regular display
            if(redPresetStoreStat == True):
                viPresets[RED_PRESET_V] = newVoltage
                viPresets[RED_PRESET_I] = newCurrent 
                presetChanged = True
            elif(yellowPresetStoreStat == True):
                viPresets[YELLOW_PRESET_V] = newVoltage
                viPresets[YELLOW_PRESET_I] = newCurrent
                presetChanged = True
            elif(yellowPresetStoreStat == True):    
                viPresets[BLUE_PRESET_V] = newVoltage
                viPresets[BLUE_PRESET_I] = newCurrent
                presetChanged = True
            else:
                if(actVoltage - newVoltage > 200):
                    #print("VOLTAGE ERROR")
                    lcd.lcdWriteLoc("ERR %.2fV %dmA" % ((actVoltage)/100.0, iMonVoltage), 1, 0, 16)
                else:
                    if(currentLimOn == True):
                        lcd.lcdWriteLoc("LIM %.2fV %dmA" % ((actVoltage)/100.0, iMonVoltage), 1, 0, 16)
                    else:
                        lcd.lcdWriteLoc("OUT %.2fV %dmA" % ((newVoltage)/100.0, iMonVoltage), 1, 0, 16)
                lastTimeSet = time.time() 
            
            if(presetChanged == True):
                presetsFile = open('PPS_Presets.csv', 'w')
                csvwriter = csv.writer(presetsFile)
                csvwriter.writerow(viPresets) 
                presetsFile.close()
                lcd.lcdWriteLoc("PRESET SAVED", 1, 0, 16)
                presetChanged = False
#def loop_spi()


def loop_Buttons():
    lastTimeSet = 0    
    
    while(1):
        currentTime = time.time()                
        if(currentTime - lastTimeSet > 0):
            redButtonStatus = redButton.read_pushButton()
            yellowButtonStatus = yellowButton.read_pushButton()
            blueButtonStatus = blueButton.read_pushButton()
        
            #RED BUTTON
            if(redButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                redPresetRecallQ.put(True)
            else:
                redPresetRecallQ.put(False)            
        
            if(redButtonStatus == pushButton.PB_LONG_PRESS):            
                redPresetStoreQ.put(True)            
            else:
                redPresetStoreQ.put(False)
        
            #YELLOW BUTTON
            if(yellowButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                yellowPresetRecallQ.put(True)
            else:
                yellowPresetRecallQ.put(False)            
            
            if(yellowButtonStatus == pushButton.PB_LONG_PRESS):            
                yellowPresetStoreQ.put(True)            
            else:            
                yellowPresetStoreQ.put(False)
                            
            #BLUE BUTTON    
            if(blueButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                bluePresetRecallQ.put(True)
            else:   
                bluePresetRecallQ.put(False)
            
            if(blueButtonStatus == pushButton.PB_LONG_PRESS):            
                bluePresetStoreQ.put(True)            
            else:
                bluePresetStoreQ.put(False)
            lastTimeSet = time.time()
#def loop_Buttons

try:
    global defaultPresets
    isPresetFilePresent = os.path.isfile('PPS_Presets.csv')
    if(isPresetFilePresent == False):  
        with open('PPS_Presets.csv', 'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(defaultPresets)    
    
    #read file and copy to internal list on powerup
    with open('PPS_Presets.csv', 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            for row in csvreader:
                for i, val in enumerate(row): 
                    defaultPresets[i] = val
    
    viPresets = Array('i',6)
    
    
    p1 = Process(target=loop_knob, args=(defaultPresets, viPresets))
    p2 = Process(target=loop_spi, args=(defaultPresets, viPresets))
    p3 = Process(target=loop_Buttons)

    p1.start()
    p2.start()
    p3.start()

    p1.join()
    p2.join()
    p3.join()
    
except KeyboardInterrupt: # Ctrl+C pressed, so
    print("Shutting Down!!!!!!!!!!!")
    vKnob.Close()
    iKnob.Close()
    vDAC.Close() #close the port before exit
    iDAC.Close() #close the port before exit
    lcd.Close()
    GPIO.cleanup()
    
    
    
#end try






