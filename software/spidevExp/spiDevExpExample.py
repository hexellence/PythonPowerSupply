import time
from RPi import GPIO
from spiDevExp import spiExpanded




time.sleep(1)

dev1 = spiExpanded(0)
dev2 = spiExpanded(1,  speed = 1000)
dev3 = spiExpanded(2)
dev4 = spiExpanded(3)
dev5 = spiExpanded(4)
dev6 = spiExpanded(5)
dev7 = spiExpanded(6)
dev8 = spiExpanded(7, mode = 0)

tunca = 0
try:

    while True:
        tunca = tunca+1  
        dev8.xfer2([0x50,tunca])
        time.sleep(0.05)        
        #dev2.xfer(170)
        #dev3.xfer(42)
        #dev4.xfer(42)
        #dev5.xfer(42)
        #dev6.xfer(42)
        #dev7.xfer(42)
        #dev8.xfer(42)
        time.sleep(1)        
        print(tunca)

	
except KeyboardInterrupt: # Ctrl+C pressed, so
    dev1.Close() #close the port before exit
#end try

