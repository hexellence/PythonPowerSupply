import spidev
import time
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob
from spiDevExp import spiExpanded
from multiprocessing import Process, Queue
from mcp4821DAC import mcp4821

# This is needed because I could not find other way to read two GPIOs at the same time. 
# pigpio helps and it's daemon has to be started 
from os import system
system("sudo pigpiod")

# This is needed to interprocess communication, queue size is not experimented.
voltageQ = Queue(maxsize=20) 
currentQ = Queue(maxsize=20) 

# Turn off the LCD and turn on after it has been initialised
GPIO.setmode(GPIO.BCM)
GPIO.setup(14, GPIO.OUT)
GPIO.output(14, True)

def loop_knob():
    vKnob = RotaryKnob.rotKnob(clkPin = 20, dtPin = 21, countMin = 0, countMax = 2400, highSpeedThrs = 150, highSpeedStep = 50)
    vKnob.open()
    iKnob = RotaryKnob.rotKnob(clkPin = 16, dtPin = 19, countMin = 0, countMax = 1000, highSpeedThrs = 200, highSpeedStep = 10)
    iKnob.open()
    while 1:
        voltageQ.put(vKnob.updateKnob())        
        currentQ.put(iKnob.updateKnob())
#def loop_knob


def loop_spi():
    spiLcd = spiExpanded(3, mode = 0)
    lcd = MIDAS_LCD.MidasLcd(spiLcd, 4)
    
    spiVDac = spiExpanded(1, mode = 0)
    vDAC = mcp4821(spiVDac)
    
    spiIDac = spiExpanded(2, mode = 0)
    iDAC = mcp4821(spiIDac)
    
    #Turn On LCD
    GPIO.output(14, False)
    
    newVoltage = 0
    lastSavedVoltage = 1
    newCurrent = 0
    lastSavedCurrent = 1
    lcd.lcdWriteLoc("SET ", 0, 0)
    lastTime = 0
    while 1: 
        newVoltage = voltageQ.get()
        newCurrent = currentQ.get()
        currentTime = time.time()
        
        #print(newVoltage)
        #print(currentTime - lastTime)
        if((newVoltage != lastSavedVoltage) and (currentTime - lastTime > 0.16)):
            lastSavedVoltage = newVoltage
            lastTime = currentTime
            lcd.lcdWriteLoc("%.2fV" % (newVoltage/100.0), 0, 4, 6)
            vDAC.setVoltage(newVoltage)
#def loop_spi()
        
        


p1 = Process(target=loop_knob)
p2 = Process(target=loop_spi)


p1.start()
p2.start()


p1.join()
p2.join()



