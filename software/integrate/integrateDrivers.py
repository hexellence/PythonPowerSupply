from spiDevExp import spiExpanded
import time
from RPi import GPIO
import MIDAS_LCD
import RotaryKnob
from mcp4821DAC import mcp4821

from mcp3008ADC import mcp3008

spiAdc = spiExpanded(0, mode = 0)
spiVDac = spiExpanded(1, mode = 0)
spiIDac = spiExpanded(2, mode = 0)
spiLcd = spiExpanded(3, mode = 0)

adcOutV = 0
adc5V = 1
adc3V3 = 2



ADC1 = mcp3008(spiAdc, 4096)
vDAC = mcp4821(spiVDac)
iDAC = mcp4821(spiIDac)
lcd = MIDAS_LCD.MidasLcd(spiLcd, 4)

vKnob = RotaryKnob.rotKnob(20, 21)
vKnob.open()

iKnob = RotaryKnob.rotKnob(19, 16)
iKnob.open()

lcd.lcdWriteLoc('0', 0, 0, 0)
tunca = 0
try:

    while True:
        lcd.lcdWriteLoc("SET", 0, 0)  
        lcd.lcdWriteLoc(str(vKnob.updateKnob()), 0, 4, 4, "V")  
        lcd.lcdWriteLoc(str(iKnob.updateKnob()), 0, 11, 4, "A")  
        
        lcd.lcdWriteLoc("OUT", 1, 0)  
        lcd.lcdWriteLoc(str(ADC1.read_adcMilliVolts(adc3V3)), 1, 4, 4, "V")  
        lcd.lcdWriteLoc(str(ADC1.read_adcMilliVolts(adc5V)), 1, 11, 4, "A")  
        
        vDAC.setVoltage(vKnob.updateKnob())
        iDAC.setVoltage(iKnob.updateKnob())
        
        time.sleep(1)

	
except KeyboardInterrupt: # Ctrl+C pressed, so
    lcd.Close() #close the port before exit
    GPIO.cleanup()
#end try

