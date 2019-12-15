import time
from RPi import GPIO
from mcp3008ADC import mcp3008
from spiDevExp import spiExpanded

spiMcp3008 = spiExpanded(0, mode = 0)

ADC1 = mcp3008(spiMcp3008, 4096)

data = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

tunca = 0
try:

    while True:
        tunca = tunca+100  
        time.sleep(0.5)   
        data[0] = ADC1.read_adcMilliVolts(0)
        data[1] = ADC1.read_adcMilliVolts(1)
        data[2] = ADC1.read_adcMilliVolts(2)
        data[3] = ADC1.read_adcMilliVolts(3)
        data[4] = ADC1.read_adcMilliVolts(4)
        data[5] = ADC1.read_adcMilliVolts(5)
        data[6] = ADC1.read_adcMilliVolts(6)
        data[7] = ADC1.read_adcMilliVolts(7)
        print(data)
        
except KeyboardInterrupt: # Ctrl+C pressed, so
    spiMcp3008.Close()
#end try