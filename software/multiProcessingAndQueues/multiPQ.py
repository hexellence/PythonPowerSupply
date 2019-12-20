import spidev
import time
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob
from spiDevExp import spiExpanded
from multiprocessing import Process, Queue
from mcp4821DAC import mcp4821


voltageQ = Queue(maxsize=20) 
currentQ = Queue(maxsize=20) 

GPIO.setmode(GPIO.BCM)
GPIO.setup(14, GPIO.OUT)
GPIO.output(14, True)

def loop_knob():
    vKnob = RotaryKnob.rotKnob(20, 21)
    vKnob.open()
    iKnob = RotaryKnob.rotKnob(16, 19)
    iKnob.open()
    while 1:
        vSet = vKnob.updateKnob()
        if(vSet < 0):
            vSet = 0
        voltageQ.put(vSet)
        
        iSet = iKnob.updateKnob()
        if(iSet < 0):
            iSet = 0
        currentQ.put(iSet)



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
        
        print(newVoltage)
        #print(currentTime - lastTime)
        if((newVoltage != lastSavedVoltage) and (currentTime - lastTime > 0.16)):
            lastSavedVoltage = newVoltage
            lastTime = currentTime
            lcd.lcdWriteLoc("%.2fV" % (newVoltage/100.0), 0, 4, 6)
            vDAC.setVoltage(newVoltage)
            
        
        


p1 = Process(target=loop_knob)
p2 = Process(target=loop_spi)


p1.start()
p2.start()


p1.join()
p2.join()



