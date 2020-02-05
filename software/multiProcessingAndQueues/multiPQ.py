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
from os import system
import csv
import paho.mqtt.client as mqttClient
import paho.mqtt.publish as mqttPublish

# Used Pins
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

# ADC channels assignments
ADC_CH_GND = 0
ADC_CH_5V0 = 1
ADC_CH_3V3 = 2
ADC_CH_IMON = 3
ADC_CH_VSENS = 4
ADC_CH_VTEMP = 5
ADC_CH_ISET = 6
ADC_CH_VSET = 7

# Preset array indexes
RED_PRESET_V = 0
RED_PRESET_I = 1
YELLOW_PRESET_V = 2
YELLOW_PRESET_I = 3
BLUE_PRESET_V = 4
BLUE_PRESET_I = 5

# LCD ON/OFF Pin Value assignments
LCD_ON = False
LCD_OFF = True

# Other assignments
SHUNT_RESISTOR_VALUE = 1.2

global defaultPresets

client = mqttClient.Client()

# This is needed because I could not find other way to read two GPIOs at the same time. 
# pigpio helps and it's daemon has to be started 
system("sudo pigpiod")

# This is needed to interprocess communication, queue size is not experimented.
# This is Voltage and Current settings filled by the knobs and consumed by the SPI loop
voltageQ = Queue(maxsize=20) 
currentQ = Queue(maxsize=20) 

# These are Presets' Store commands' queues
# Store Queue is filled in by buttons loop i.e. process. True when a long press is performed, False otherwise
# Store Queue is consumed by the SPI loop i.e. process
redPresetStoreQ = Queue(maxsize=5) 
yellowPresetStoreQ = Queue(maxsize=5) 
bluePresetStoreQ = Queue(maxsize=5) 

# These are Presets' Recall commands' queues
# Recall Queue is filled in by buttons loop i.e. process. True when a short release is performed, False otherwise
# Recall Queue is consumed by the knobs loop i.e. process. to push to the knob counters
redPresetRecallQ = Queue(maxsize=5) 
yellowPresetRecallQ = Queue(maxsize=5) 
bluePresetRecallQ = Queue(maxsize=5) 

# MQTT remote setting and reading
remoteSetCurrentQ = Queue(maxsize=5) 
remoteSetVoltageQ = Queue(maxsize=5) 

currentMonQ = Queue(maxsize=5) 

# GPIO Assignments
GPIO.setmode(GPIO.BCM)
# LCD On/Off pin assignment
GPIO.setup(LCD_ON_OFF_PIN, GPIO.OUT)
GPIO.output(LCD_ON_OFF_PIN, LCD_OFF)

# Preset switches Assignment
GPIO.setup(PB_YELLOW, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(PB_RED, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(PB_BLUE, GPIO.IN,pull_up_down=GPIO.PUD_UP)

# Call button management class to work
redButton = pushButton.pushButtonDev(PB_RED)
yellowButton = pushButton.pushButtonDev(PB_YELLOW)
blueButton = pushButton.pushButtonDev(PB_BLUE)

# Current Limit Indicator assignment. This lets us know that the current limit comparator is triggered
GPIO.setup(CLIM_PIN, GPIO.IN)

# Call spi Class and create devices on the SPI bus
spiADC = spiExpanded(0, mode = 0)
adc = mcp3008(spiADC, 4096)
    
spiLcd = spiExpanded(3, mode = 0)
lcd = MIDAS_LCD.MidasLcd(spiLcd, LCD_RS_PIN)
    
spiVDac = spiExpanded(2, mode = 0)
vDAC = mcp4821(spiVDac)
    
spiIDac = spiExpanded(1, mode = 0)
iDAC = mcp4821(spiIDac)

# Call knob Class and create Voltage and Current Knobs
vKnob = RotaryKnob.rotKnob(clkPin = V_KNOB_CLK_PIN, dtPin = V_KNOB_DT_PIN, countMin = 0, countMax = 1200, highSpeedThrs = 15, highSpeedStep = 100)
vKnob.open()
iKnob = RotaryKnob.rotKnob(clkPin = I_KNOB_CLK_PIN, dtPin = I_KNOB_DT_PIN, countMin = 0, countMax = 999, highSpeedThrs = 15, highSpeedStep = 100)
iKnob.open()


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("PythonPowerSupply/vSet")
    client.subscribe("PythonPowerSupply/iSet")
    client.subscribe("PythonPowerSupply/preset")
    
def on_message(client, userdata, msg):
    
    if(msg.topic == "PythonPowerSupply/preset"):
        if(msg.payload == "Red"):
            redPresetRecallQ.put(True)
        if(msg.payload == "Yellow"):
            yellowPresetRecallQ.put(True)  
        if(msg.payload == "Blue"):
            bluePresetRecallQ.put(True)  
    
    if(msg.topic == "PythonPowerSupply/iSet"):
        print(msg.topic+" "+str(msg.payload))
        remoteSetCurrentQ.put(msg.payload)
        
    if(msg.topic == "PythonPowerSupply/vSet"):
        print(msg.topic+" "+str(msg.payload))
        remoteSetVoltageQ.put(msg.payload)


def loop_knob(defaultPresets, viPresets):
    
    while 1:
        # Check if a preset is requested first if yes let the knobs know the current counter
        # This is needed because otherwise the knobs when turned start from where they were left
        redPresetRecallStat = redPresetRecallQ.get()
        yellowPresetRecallStat = yellowPresetRecallQ.get()
        bluePresetRecallStat = bluePresetRecallQ.get()
        
        if(remoteSetVoltageQ.empty() != True):
            remoteSetVoltage = remoteSetVoltageQ.get()
            vKnob.InitialiseCounter(int(remoteSetVoltage))
        
        if(remoteSetCurrentQ.empty() != True):
            remoteSetCurrent = remoteSetCurrentQ.get()
            iKnob.InitialiseCounter(int(remoteSetCurrent))
            
        if(redPresetRecallStat == True):
            vKnob.InitialiseCounter(viPresets[RED_PRESET_V])
            iKnob.InitialiseCounter(viPresets[RED_PRESET_I])

        if(yellowPresetRecallStat == True):
            vKnob.InitialiseCounter(viPresets[YELLOW_PRESET_V])
            iKnob.InitialiseCounter(viPresets[YELLOW_PRESET_I])
            
        if(bluePresetRecallStat == True):
            vKnob.InitialiseCounter(viPresets[BLUE_PRESET_V])
            iKnob.InitialiseCounter(viPresets[BLUE_PRESET_I])
        
        #get the voltage and current settings from the knobs
        voltageQ.put(vKnob.updateKnob())        
        currentQ.put(iKnob.updateKnob())
#def loop_knob


def loop_spi(defaultPresets, viPresets):    
    
    #This is the main loop, it is critical and needs better tuning for user interface
    
    newVoltage = 0
    #lastSavedVoltage = 1
    newCurrent = 0
    limVoltage = 0
    limCurrent = 0
    #lastSavedCurrent = 1
    
    lastTimeSet = 0
    #lastTimeOut = 0
    #numOfSmaples = 0
    currentLimOn = False
    #isVoltageErrorOn = False
    actVoltage = 0
    redPresetStoreStat = False
    yellowPresetStoreStat = False
    bluePresetStoreStat = False
    presetChanged = False

    # Read the presets that is read from a file on before powerup and store them in a sharable Array. 
    # This is needed for different processes know about the same preset list
    # defaultPresets is a global but it cannot be shared among proceses
    for i, val in enumerate(defaultPresets): 
        viPresets[i] = int(val)  

    #Turn On LCD
    GPIO.output(LCD_ON_OFF_PIN, LCD_ON)
    time.sleep(0.5)
    lcd.lcdWriteLoc("SET ", 0, 0)
    while 1:        
        newVoltage = voltageQ.get()
        newCurrent = currentQ.get()
        redPresetStoreStat = redPresetStoreQ.get()
        yellowPresetStoreStat = yellowPresetStoreQ.get()
        bluePresetStoreStat = bluePresetStoreQ.get()
        currentTime = time.time()        
        # The interval selected here is kind of tuned so that the display and knob turning makes better sense to the user.
        # But unfortunately I am not totally satisfied. The knobs miss some steps and think the knobs are turning to the other direction. 
        # There are lots of components here including the caps and voltage dividers used with the knobs.
        if(currentTime - lastTimeSet > 0.2):
            lcd.lcdWriteLoc("%.2fV %dmA" % (newVoltage/100.0, newCurrent), 0, 4, 12)
                        
            vDAC.setVoltage(newVoltage)
            iDAC.setVoltage(newCurrent)
            
            actVoltage = adc.read_adcMilliVolts(ADC_CH_VSENS)
            # The calculation here is because of some current is stolen by the circuit and the bad tolerance of the shunt resistor.
            iMonVoltage = int(adc.read_adcMilliVolts(ADC_CH_IMON)/SHUNT_RESISTOR_VALUE)
            iMonVoltage += actVoltage*6.5/100
            iMonVoltage = int(math.ceil(iMonVoltage / 5.0)) * 5
            currentMonQ.put(iMonVoltage)
            
            #Reset limiting conditions, either the knobs are turned or the currentConsumption falls below the limit            
            if(((limVoltage != newVoltage) or (limCurrent != newCurrent) or (iMonVoltage - limCurrent < 5)) and (currentLimOn == True)):                
                currentLimOn = False
                #print("Reset")
            
            #We want the current limiting latched so the the user will see it until the user does something 
            if((GPIO.input(CLIM_PIN) == 0) and (currentLimOn == False)):
                limVoltage = newVoltage
                limCurrent = newCurrent
                currentLimOn = True
                #print("Latch")
            
            #Preset Store
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
                #Normal or ERR or LIM displays
                if(actVoltage - newVoltage > 200):
                    # The Normal dipslay shows the set voltage at the out row. This is to improve usability 
                    # To not to mislead the user if the set voltage and actual voltage goes above 200 mV this will be indicated 
                    # Voltage Error Display
                    lcd.lcdWriteLoc("ERR %.2fV %dmA" % ((actVoltage)/100.0, iMonVoltage), 1, 0, 16)
                else:
                    if(currentLimOn == True):
                        # Current Limit Display
                        lcd.lcdWriteLoc("LIM %.2fV %dmA" % ((actVoltage)/100.0, iMonVoltage), 1, 0, 16)
                    else:
                        # Normal Display
                        lcd.lcdWriteLoc("OUT %.2fV %dmA" % ((newVoltage)/100.0, iMonVoltage), 1, 0, 16)
                lastTimeSet = time.time() 
            
            #If a preset is stored store is in the csv file and show it on screen
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
            # Check Button Status and push into the queue the status
            if(redButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                redPresetRecallQ.put(True)
            else:
                redPresetRecallQ.put(False)            
        
            if(redButtonStatus == pushButton.PB_LONG_PRESS):            
                redPresetStoreQ.put(True)            
            else:
                redPresetStoreQ.put(False)
        
            #YELLOW BUTTON
            # Check Button Status and push into the queue the status
            if(yellowButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                yellowPresetRecallQ.put(True)
            else:
                yellowPresetRecallQ.put(False)            
            
            if(yellowButtonStatus == pushButton.PB_LONG_PRESS):            
                yellowPresetStoreQ.put(True)            
            else:            
                yellowPresetStoreQ.put(False)
                            
            #BLUE BUTTON    
            # Check Button Status and push into the queue the status
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


def loop_MqttReceive():
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("test.mosquitto.org", 1883, 60)
    client.loop_forever()

#def loop_MqttReceive


def loop_MqttSend():
    while(1):
        mqttPublish.single("PythonPowerSupply/iMon", currentMonQ.get(), hostname="test.mosquitto.org")
        time.sleep(0.05)

#def loop_MqttReceive


try:
    defaultPresets = [500,250,330,200,1200,500]
    
    
    
    #Check presets file and if it does not exist create it with the defaults
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
    
    #Shared Array accross processes
    viPresets = Array('i',6)    
    
    #Processes
    knobMng = Process(target=loop_knob, args=(defaultPresets, viPresets))
    spiMng = Process(target=loop_spi, args=(defaultPresets, viPresets))
    buttonsMng = Process(target=loop_Buttons)
    mqttRcvMng = Process(target=loop_MqttReceive)
    mqttXmitMng = Process(target = loop_MqttSend)
    
    knobMng.start()
    spiMng.start()
    buttonsMng.start()
    mqttRcvMng.start()
    mqttXmitMng.start()
    
    knobMng.join()
    spiMng.join()
    buttonsMng.join()
    mqttRcvMng.join()
    mqttXmitMng.join()
     

    
except KeyboardInterrupt: # Ctrl+C pressed, so
    print("Shutting Down!!!!!!!!!!!")
    vKnob.Close()
    iKnob.Close()
    vDAC.Close() #close the port before exit
    iDAC.Close() #close the port before exit
    lcd.Close()
    GPIO.cleanup()
  
    
#end try




