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


def loop_knob():
    vKnob = RotaryKnob.rotKnob(20, 21)
    vKnob.open()
    iKnob = RotaryKnob.rotKnob(16, 19)
    iKnob.open()
    while 1:
        voltageQ.put(vKnob.updateKnob())
        currentQ.put(iKnob.updateKnob())



def loop_lcd():
    spiLcd = spiExpanded(3, mode = 0)
    lcd = MIDAS_LCD.MidasLcd(spiLcd, 4)
    
    spiVDac = spiExpanded(1, mode = 0)
    vDAC = mcp4821(spiVDac)
    
    spiIDac = spiExpanded(2, mode = 0)
    iDAC = mcp4821(spiIDac)
    
    newVoltage = 0
    lastSavedVoltage = 1
    newCurrent = 0
    lastSavedCurrent = 1
    lcd.lcdWriteLoc("SET ", 0, 0)
    while 1:    
        newVoltage = voltageQ.get()
        newCurrent = currentQ.get()
        if(newVoltage != lastSavedVoltage):
            lastSavedVoltage = newVoltage
            lcd.lcdWriteLoc("%.2fV" % (newVoltage/100.0), 0, 4, 5)
            vDAC.setVoltage(newVoltage)
        if(newCurrent != lastSavedCurrent):
            lastSavedCurrent = newCurrent
            lcd.lcdWriteLoc("%.2fA" % (newCurrent/100.0), 0, 10, 5)
            iDAC.setVoltage(newCurrent)
            
        


p1 = Process(target=loop_knob)
p2 = Process(target=loop_lcd)


p1.start()
p2.start()


p1.join()
p2.join()



