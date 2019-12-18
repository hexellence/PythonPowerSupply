# Expands SPI Chip Selects to 8 with the use of an external 74139 dual 2to4 decoder
import spidev
import time
from RPi import GPIO


isResourceReady = False
spi0 = None   
spi1 = None
A0_PIN = 6
A1_PIN = 5


class spiExpanded:    
      
    def __init__(self, address, speed = 350000, lsbFirst = False, mode = 3, csActiveHigh = False):
        
        global isResourceReady
        global spi0
        global spi1
        
        assert(address < 8)
        
        if(isResourceReady == False):
            GPIO.setmode(GPIO.BCM)
            
            GPIO.setup(A0_PIN, GPIO.OUT)
            GPIO.setup(A1_PIN, GPIO.OUT)
            GPIO.output(A0_PIN, True)
            GPIO.output(A1_PIN, True)
                        
            spi1 = spidev.SpiDev(0, 1)
            spi0 = spidev.SpiDev(0, 0)
            spi1.open(0, 1) 
            spi0.open(0, 0)
                        
            isResourceReady = True
        
        self.A0 = (address)&1
        self.A1 = (address)&2
        
        if(address > 3):
            self.spi = spi1
        else:
            self.spi = spi0
        
        self.address = address
        self.speed = speed
        self.lsbFirst = lsbFirst
        self.mode = mode
        self.csActiveHigh = csActiveHigh       
        
    #end def    


    def xfer(self, bytes):

        self.spi.max_speed_hz = self.speed
        self.spi.lsbfirst = self.lsbFirst
        self.spi.mode = self.mode
        self.spi.bits_per_word = 8
        self.spi.cshigh = self.csActiveHigh
        
        self.spiAddressOut()
        resp = self.spi.xfer(bytes)
        time.sleep(0.01) # sleep for 0.01 seconds
        return resp
        
    #end def 


    def xfer2(self, bytes):

        self.spi.max_speed_hz = self.speed
        self.spi.lsbfirst = self.lsbFirst
        self.spi.mode = self.mode
        self.spi.bits_per_word = 8
        self.spi.cshigh = self.csActiveHigh
        
        self.spiAddressOut()
        resp = self.spi.xfer2(bytes)
        time.sleep(0.01) # sleep for 0.01 seconds
        return resp
        
    #end def
    
    
    def spiAddressOut(self):

        GPIO.output(A0_PIN, self.A0)
        GPIO.output(A1_PIN, self.A1)
        time.sleep(0.01) # sleep for 0.01 seconds
        
    #end def


    def Close(self):
          
        spi0.close() #close the port before exit
        spi1.close() #close the port before exit
        GPIO.cleanup(A0_PIN)
        GPIO.cleanup(A1_PIN)
        
    #end def

#end class    