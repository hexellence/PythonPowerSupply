import time
from RPi import GPIO
from mcp4821DAC import mcp4821
from spiDevExp import spiExpanded

spiMcp4821 = spiExpanded(1, mode = 0)

DAC1 = mcp4821(spiMcp4821)

tunca = 0
try:

    while True:
          
        DAC1.setVoltage(tunca)
        tunca = tunca+100
        time.sleep(3)   
        print(tunca)
        

	
except KeyboardInterrupt: # Ctrl+C pressed, so
    DAC1.Close() #close the port before exit
    spiMcp4821.Close()
#end try

