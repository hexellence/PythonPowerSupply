# MCP4821 SPI DAC Driver
import spidev
import time
from RPi import GPIO

from spiDevExp import spiExpanded

MCP2841_SHUTDOWN = 0x0000

class mcp4821:    
      
    def __init__(self, spi):
           
        assert(spi != None)
        self.spi = spi
        
    #end def    

    def writeDac(self, value):

        retVal = self.spi.xfer2([(value&0xFF00)>>8,value&0x00FF])
        
    #end def 

     
    def setVoltage(self, millivolts):
        
        #Voltage will be +/-10mV precision
        #Limit range
        vAdj = millivolts   
        if(millivolts > 4095):
            vAdj = 4095
        if(millivolts < 0):
            vAdj = 0
        
        # set gain and value for request        
        if(vAdj > 2047):
            vAdj = vAdj
            gain = 0x5000
        else:
            vAdj = vAdj * 2
            gain = 0x7000
        
        dacValue = vAdj | gain
        retVal = self.writeDac(dacValue)    
        
    #end def 
    
    
    def Close(self):
        
        self.writeDac(MCP2841_SHUTDOWN)
        
    #end def 

#end class    