from spiDevExp import spiExpanded
import time
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob
from mcp4821DAC import mcp4821

from mcp3008ADC import mcp3008


spiLcd = spiExpanded(3, mode = 0)
lcd = MIDAS_LCD.MidasLcd(spiLcd, 4)
spiVDac = spiExpanded(1, mode = 0)

spiAdc = spiExpanded(0, mode = 0)
ADC1 = mcp3008(spiAdc, 4096)
vDAC = mcp4821(spiVDac)


vKnob = RotaryKnob.rotKnob(20, 21)
vKnob.open()

lcd.lcdWriteLoc('0', 0, 0)
tunca = 0
try:

    while True:
        vDAC.setVoltage(tunca)
        counter = vKnob.updateKnob()
        lcd.lcdWriteLoc(str(ADC1.read_adcMilliVolts(2)), 0, 0)  
        time.sleep(1)
        lcd.lcdWriteLoc(str(ADC1.read_adcMilliVolts(1)), 0, 0)  
        time.sleep(1)
        lcd.lcdWriteLoc(str(ADC1.read_adcMilliVolts(7)), 1, 0)  
        tunca = tunca+100
        if(tunca > 3300):
            tunca = 0

	
except KeyboardInterrupt: # Ctrl+C pressed, so
    lcd.Close() #close the port before exit
    GPIO.cleanup()
#end try

