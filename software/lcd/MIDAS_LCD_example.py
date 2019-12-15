from spiDevExp import spiExpanded
import time
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob



spi = spiExpanded(3, mode = 0)
time.sleep(1)
lcd = MIDAS_LCD.MidasLcd(spi, 4)


vKnob = RotaryKnob.rotKnob(20, 21)
vKnob.open()

lcd.lcdWriteLoc('0', 0, 0)

try:

    while True:
        counter = vKnob.updateKnob()
        lcd.lcdWriteLoc(str(counter), 0, 0)        
        

	
except KeyboardInterrupt: # Ctrl+C pressed, so
    lcd.Close() #close the port before exit
    GPIO.cleanup()
#end try

