import spidev
import time
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob
from spiDevExp import spiExpanded
from multiprocessing import Process, Queue
 


counterQ = Queue(maxsize=20) 



def loop_knob():
    vKnob = RotaryKnob.rotKnob(20, 21)
    vKnob.open()
    while 1:
        counterQ.put(vKnob.updateKnob())



def loop_lcd():
    spiLcd = spiExpanded(3, mode = 0)
    lcd = MIDAS_LCD.MidasLcd(spiLcd, 4)
    
    counter = 0
    lastSavedCounter = 1
    
    while 1:    
        counter = counterQ.get()
        if(counter != lastSavedCounter):
            lastSavedCounter = counter
            print(counter)
            #lcd.lcdWriteLoc(str(counter), 0, 0, 4)



p1 = Process(target=loop_knob)
p2 = Process(target=loop_lcd)

p1.start()
p2.start()

p1.join()
p2.join()


