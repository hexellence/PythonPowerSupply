import spidev
import time
import math
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob
from spiDevExp import spiExpanded
from multiprocessing import Process, Queue, Array, Value, Pipe
from mcp4821DAC import mcp4821
from mcp3008ADC import mcp3008
import pushButton
import os.path
from os import system
import csv
import paho.mqtt.client as mqttClient
import paho.mqtt.publish as mqttPublish
import logging

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
PB_WHITE = 22

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
WHITE_PRESET_V = 6
WHITE_PRESET_I = 7
LAST_PRESET = 8


# LCD ON/OFF Pin Value assignments
LCD_ON = False
LCD_OFF = True

# Other assignments
SHUNT_RESISTOR_VALUE = 1.2

SHOW_REAL_VOLTAGE = True

global defaultPresets

client = mqttClient.Client()

# This is needed because I could not find other way to read two GPIOs at the same time. 
# pigpio helps and it's daemon has to be started 
system("sudo pigpiod")

# This is needed to interprocess communication, queue didn't work well shared value is better for this
# This is Voltage and Current settings filled by the knobs and consumed by the SPI loop
knobVoltageSet = Value('i')
knobCurrentSet = Value('i')

# Selected Pipe for the MQTT communication. Queue didn't work because of the type
mqttIn, mqttOut = Pipe()

# These are Presets' Store commands' queues
# Store Queue is filled in by buttons loop i.e. process. True when a long press is performed, False otherwise
# Store Queue is consumed by the SPI loop i.e. process
presetStoreQ = Queue(maxsize=5) 

# These are Presets' Recall commands' queues
# Recall Queue is filled in by buttons loop i.e. process. True when a short release is performed, False otherwise
# Recall Queue is consumed by the knobs loop i.e. process. to push to the knob counters
presetRecallQ = Queue(maxsize=5) 

# MQTT remote setting and reading
remoteSetCurrentQ = Queue(maxsize=5) 
remoteSetVoltageQ = Queue(maxsize=5) 

currentMonQ = Queue(maxsize=5) 
voltageMonQ = Queue(maxsize=5) 

# GPIO Assignments
GPIO.setmode(GPIO.BCM)
# LCD On/Off pin assignment
GPIO.setup(LCD_ON_OFF_PIN, GPIO.OUT)
GPIO.output(LCD_ON_OFF_PIN, LCD_OFF)

# Preset switches Assignment
GPIO.setup(PB_YELLOW, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(PB_RED, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(PB_BLUE, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(PB_WHITE, GPIO.IN,pull_up_down=GPIO.PUD_UP)

# Call button management class to work
redButton = pushButton.pushButtonDev(PB_RED)
yellowButton = pushButton.pushButtonDev(PB_YELLOW)
blueButton = pushButton.pushButtonDev(PB_BLUE)
whiteButton = pushButton.pushButtonDev(PB_WHITE)

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
vKnob = RotaryKnob.rotKnob(clkPin = V_KNOB_CLK_PIN, dtPin = V_KNOB_DT_PIN, countMin = 0, countMax = 1200, clickStep = 5, highSpeedThrs = 50, highSpeedStep = 100)
vKnob.open()
iKnob = RotaryKnob.rotKnob(clkPin = I_KNOB_CLK_PIN, dtPin = I_KNOB_DT_PIN, countMin = 0, countMax = 990, clickStep = 10, highSpeedThrs = 50, highSpeedStep = 100)
iKnob.open()

log = logging.getLogger()
console = logging.StreamHandler()
format_str = '%(asctime)s\t%(levelname)s -- %(processName)s %(filename)s:%(lineno)s -- %(message)s'
console.setFormatter(logging.Formatter(format_str))

log.addHandler(console) # writes to console.
log.setLevel(logging.CRITICAL)
#log.setLevel(logging.DEBUG)
log.debug('Log Level: DEBUG!')


def lcdLine(heading, voltage, current):
    tempOutput = heading + " "
    tempOutput += "%.2fV %dmA" % (voltage, current)
    return tempOutput


def on_connect(client, userdata, flags, rc):
    log.debug('Connected with result code %s', str(rc))
    client.subscribe("PythonPowerSupply/vSet")
    client.subscribe("PythonPowerSupply/iSet")
    client.subscribe("PythonPowerSupply/preset")
    

def on_message(client, userdata, msg):
    
    if(msg.topic == "PythonPowerSupply/preset"):
        if(msg.payload == "Red"):
            log.debug('Remote command preset Red')
            presetRecallQ.put(1)
        if(msg.payload == "Yellow"):
            log.debug('Remote command preset Yellow')
            presetRecallQ.put(2)
        if(msg.payload == "Blue"):
            log.debug('Remote command preset Blue')
            presetRecallQ.put(3)
        if(msg.payload == "White"):
            log.debug('Remote command preset White')
            presetRecallQ.put(4)    
    
    if(msg.topic == "PythonPowerSupply/iSet"):
        log.debug('%s %s', msg.topic, str(msg.payload))
        remoteSetCurrentQ.put(msg.payload)
        
    if(msg.topic == "PythonPowerSupply/vSet"):
        log.debug('%s %s', msg.topic, str(msg.payload))
        remoteSetVoltageQ.put(msg.payload)

def mqttPub(topic, payload):
    #log.debug("Sending %s from mqtt pipe value is %s", topic, str(payload))
    mqttIn.send([topic, str(payload)])   
   
# def mqttPublish

def loop_knob(defaultPresets, viPresets):
    
    mqttPub("presetReturn", "Select")
    
    while 1:
        # Check if a preset is requested first if yes let the knobs know the current counter
        # initialiseCounter() is needed so that the knobs know where they should start when they are turned
        # Check if a remote command is received
        # Knob is a fast device and thus this process should not be crowded
        
        if(remoteSetVoltageQ.empty() != True):
            mqttPub("presetReturn", "Select")
            remoteSetVoltage = remoteSetVoltageQ.get()
            remoteSetVoltage = float(remoteSetVoltage)*100.0
            vKnob.InitialiseCounter(int(remoteSetVoltage))
        
        if(remoteSetCurrentQ.empty() != True):
            mqttPub("presetReturn", "Select")
            remoteSetCurrent = remoteSetCurrentQ.get()
            iKnob.InitialiseCounter(int(remoteSetCurrent))
        
        # Check if a a preset is recalled
        if(presetRecallQ.empty() != True):
            log.debug('Recall Q not empty')
            presetNo = presetRecallQ.get()
            if(presetNo == 1):
                vKnob.InitialiseCounter(viPresets[RED_PRESET_V])
                iKnob.InitialiseCounter(viPresets[RED_PRESET_I])
                mqttPub("presetReturn", "Red")
            if(presetNo == 2):
                vKnob.InitialiseCounter(viPresets[YELLOW_PRESET_V])
                iKnob.InitialiseCounter(viPresets[YELLOW_PRESET_I])
                mqttPub("presetReturn", "Yellow")
            if(presetNo == 3):
                vKnob.InitialiseCounter(viPresets[BLUE_PRESET_V])
                iKnob.InitialiseCounter(viPresets[BLUE_PRESET_I])
                mqttPub("presetReturn", "Blue")
            if(presetNo == 4):
                vKnob.InitialiseCounter(viPresets[WHITE_PRESET_V])
                iKnob.InitialiseCounter(viPresets[WHITE_PRESET_I])
                mqttPub("presetReturn", "White")
        
        #get the voltage and current settings from the knobs
        knobCurrentSet.value = iKnob.updateKnob()
        knobVoltageSet.value = vKnob.updateKnob()
        
#def loop_knob


def loop_spi(defaultPresets, viPresets):    
    
    #This is the main loop, it is critical and needs better tuning for user interface
    
    newVoltage = 0
    newCurrent = 0
    limVoltage = 0
    limCurrent = 0
    ActVoltageList = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
    ActCurrentList = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
    lastTimeSet = 0
    lastTimeSetPreset = 0
    currentLimOn = False
    presetStoreStat = 0
    presetChanged = False

    # Read the presets that is read from a file on before powerup and store them in a sharable Array. 
    # This is needed for different processes know about the same preset list
    # defaultPresets is a global but it cannot be shared among proceses
    for i, val in enumerate(defaultPresets): 
        viPresets[i] = int(val)  

    #Turn On LCD
    GPIO.output(LCD_ON_OFF_PIN, LCD_ON)
    time.sleep(0.5)
    actLimCurrent = 0
    prevVoltage = -1
    prevCurrent = -1
    actVoltage = 0.0
    accuActVoltage = 0.0
    meanActVoltage = 0.0
    indexVoltageSample = 0
    updateImmediate = False    
    
    while 1:        
        #update data so that we can command the devices
         
        currentTime = time.time()        
        # The interval selected here is kind of tuned so that the display and knob turning makes better sense to the user.
        # But unfortunately I am not totally satisfied. The knobs miss some steps and think the knobs are turning to the other direction. 
        # There are lots of components here including the caps and voltage dividers used with the knobs.
        
        if(currentTime - lastTimeSet > 0.01):
            
            actVoltage = adc.read_adcMilliVolts(ADC_CH_VSENS)/100.0
            actCurrent = int(adc.read_adcMilliVolts(ADC_CH_IMON)/SHUNT_RESISTOR_VALUE)
            
            #get shared values. Queue didn't work so well
            newVoltage = knobVoltageSet.value/100.0
            newCurrent = knobCurrentSet.value
            
            
            #in order not to block the process check the queue if there is a request
            if(presetStoreQ.empty() != True):
                log.debug('Store Q not empty')
                presetStoreStat = presetStoreQ.get()
            else:
                presetStoreStat = 0
            
            # checking if the voltage is changed and commanding the DAC if there is a change keep the bus free 
            if(newVoltage != prevVoltage):
                vDAC.setVoltage(int(newVoltage*100.0))
                lcd.lcdWriteLoc(lcdLine("SET", newVoltage, newCurrent), 0, 0, 16)                
                mqttPub("vSetReturn", newVoltage)
                prevVoltage = newVoltage
                updateImmediate = True  
                
            if(newCurrent != prevCurrent):                
                iDAC.setVoltage(newCurrent)
                lcd.lcdWriteLoc(lcdLine("SET", newVoltage, newCurrent), 0, 0, 16)
                mqttPub("iSetReturn", newCurrent)
                prevCurrent = newCurrent
            
            # Calculate the mean value of the output measurements.
            # Depends on how frequent this loop is running. it may not be always 10 if you change the rate
            if(indexVoltageSample == 10):
                mqttPub("iMon", actCurrent)
                mqttPub("vMon", meanActVoltage)
                indexVoltageSample = 0
            else:
                ActVoltageList[indexVoltageSample] = actVoltage
                ActCurrentList[indexVoltageSample] = actCurrent
                indexVoltageSample += 1
            
            if(updateImmediate == True):
                for i in range(10):
                    ActVoltageList[i] = newVoltage  
                updateImmediate = False
                    
                
            accuActVoltage = 0
            accuActCurrent = 0
            for i in range(10):
                accuActVoltage += ActVoltageList[i]   
                accuActCurrent += ActCurrentList[i]  
            
            

            meanActVoltage = accuActVoltage / 10.0  
            meanActCurrent = accuActCurrent / 10.0 
            # Mean value calc finish always use the last 10 samples
            
            #Reset limiting conditions, either the knobs are turned or the currentConsumption falls less than the limit            
            if(((limVoltage != newVoltage) or (limCurrent != newCurrent) or (actLimCurrent - actCurrent > 10)) and (currentLimOn == True)):                
                log.debug('limVoltage=%d, newVoltage=%d, limCurrent=%d, newCurrent=%d, actCurrent=%d, currentLimOn=%d',limVoltage, newVoltage,limCurrent,newCurrent, actCurrent,currentLimOn) 
                currentLimOn = False
                mqttPub("clim", "CLIM_OFF")
                log.debug('Limit condition Reset')
            
            #We want the current limiting latched so the the user will see it until the user does something 
            if((GPIO.input(CLIM_PIN) == 0) and (currentLimOn == False)):
                limVoltage = newVoltage
                limCurrent = newCurrent
                actLimCurrent = actCurrent
                currentLimOn = True
                mqttPub("clim", "CLIM_ON")
                log.debug('Limit condition Latched at current %d', actLimCurrent)
            
            #Preset Store
            if(presetStoreStat == 1):
                viPresets[RED_PRESET_V] = newVoltage
                viPresets[RED_PRESET_I] = newCurrent 
                presetChanged = True
            elif(presetStoreStat == 2):
                viPresets[YELLOW_PRESET_V] = newVoltage
                viPresets[YELLOW_PRESET_I] = newCurrent
                presetChanged = True
            elif(presetStoreStat == 3):    
                viPresets[BLUE_PRESET_V] = newVoltage
                viPresets[BLUE_PRESET_I] = newCurrent
                presetChanged = True
            elif(presetStoreStat == 4):    
                viPresets[WHITE_PRESET_V] = newVoltage
                viPresets[WHITE_PRESET_I] = newCurrent
                presetChanged = True
            else:
                #Normal or ERR or LIM displays
                if(meanActVoltage - newVoltage > 200):
                    # The Normal dipslay shows the set voltage at the out row. This is to improve usability 
                    # To not to mislead the user if the set voltage and actual voltage goes above 200 mV this will be indicated 
                    # Voltage Error Display
                    lcd.lcdWriteLoc(lcdLine("ERR", meanActVoltage, actCurrent), 1, 0, 16)
                else:
                    if(currentLimOn == True):
                        # Current Limit Display
                        lcd.lcdWriteLoc(lcdLine("LIM", meanActVoltage, meanActCurrent), 1, 0, 16)
                    else:
                        # Normal Display
                        if(SHOW_REAL_VOLTAGE == True):
                            #log.debug(lcdLine("OUT", meanActVoltage, actCurrent))
                            lcd.lcdWriteLoc(lcdLine("OUT", meanActVoltage, actCurrent), 1, 0, 16)
                        else:
                            lcd.lcdWriteLoc(lcdLine("OUT", newVoltage, actCurrent), 1, 0, 16)
                lastTimeSet = time.time() 
            
            #If a preset is stored store is in the csv file and show it on screen
            if(presetChanged == True):
                presetsFile = open('PPS_Presets.csv', 'w')
                csvwriter = csv.writer(presetsFile)
                csvwriter.writerow(viPresets) 
                presetsFile.close()
                lcd.lcdWriteLoc("PRESET SAVED", 1, 0, 16)
                presetChanged = False
                time.sleep(2)
            
            #this is needed for the phone app to go back to select mode regardless what is happening
            if(time.time() - lastTimeSetPreset > 1):
                mqttPub("presetReturn", "Select")
                lastTimeSetPreset = time.time()
            
            
               
#def loop_spi()


def loop_Buttons():
    lastTimeSet = 0    

    while(1):
        currentTime = time.time()                
        if(currentTime - lastTimeSet > 0):
            redButtonStatus = redButton.read_pushButton()
            yellowButtonStatus = yellowButton.read_pushButton()
            blueButtonStatus = blueButton.read_pushButton()
            whiteButtonStatus = whiteButton.read_pushButton()
        
            #RED BUTTON
            # Check Button Status and push into the queue the status
            if(redButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                presetRecallQ.put(1)
            if(redButtonStatus == pushButton.PB_LONG_PRESS):            
                presetStoreQ.put(1) 
                    
            #YELLOW BUTTON
            # Check Button Status and push into the queue the status
            if(yellowButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                presetRecallQ.put(2)
            if(yellowButtonStatus == pushButton.PB_LONG_PRESS):            
                presetStoreQ.put(2)  
                            
            #BLUE BUTTON    
            # Check Button Status and push into the queue the status
            if(blueButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                presetRecallQ.put(3)
            if(blueButtonStatus == pushButton.PB_LONG_PRESS):            
                presetStoreQ.put(3)
                
            #WHITE BUTTON    
            # Check Button Status and push into the queue the status
            if(whiteButtonStatus == pushButton.PB_RELEASE_SHORT_PRESS):
                presetRecallQ.put(4)
            if(whiteButtonStatus == pushButton.PB_LONG_PRESS):            
                presetStoreQ.put(4)
            
            lastTimeSet = time.time()
#def loop_Buttons


def loop_Mqtt():
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("test.mosquitto.org", 1883, 60)
    client.loop_forever()

#def loop_MqttReceive


def loop_MqttSend():
    while(1):
        
        tempMqttData = mqttOut.recv()
        #log.debug("Received %s from mqtt pipe value is %s", tempMqttData[0], tempMqttData[1])
        mqttPublish.single("PythonPowerSupply/"+tempMqttData[0], tempMqttData[1], hostname="test.mosquitto.org")

#def loop_MqttReceive


try:
    defaultPresets = [1200,500,500,300,330,200,0,100]
    
   
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
    viPresets = Array('i',LAST_PRESET)    
    
    #Processes
    knobMng = Process(target=loop_knob, args=(defaultPresets, viPresets))
    spiMng = Process(target=loop_spi, args=(defaultPresets, viPresets))
    buttonsMng = Process(target=loop_Buttons)
    mqttMng = Process(target=loop_Mqtt)
    mqttXmitMng = Process(target = loop_MqttSend)
    
    mqttMng.start()
    knobMng.start()
    spiMng.start()
    buttonsMng.start()
    mqttXmitMng.start()
    
    mqttMng.join()
    knobMng.join()
    spiMng.join()
    buttonsMng.join()
    mqttXmitMng.join()
     

    
except KeyboardInterrupt: # Ctrl+C pressed, so
    log.debug('Shutting Down!!!!!!!!!!!')
    vKnob.Close()
    iKnob.Close()
    vDAC.Close() #close the port before exit
    iDAC.Close() #close the port before exit
    lcd.Close()
    GPIO.cleanup()
  
    
#end try





