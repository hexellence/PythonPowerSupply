import spidev
import time
from RPi import GPIO

#device dependent values
MAX_LCD_LINE_SIZE = 16
MAX_LCD_LINE_COUNT = 2
LINE_2_ADDRESS_START = 0x40
DDRAM_ADDRESS_REGISTER_MASK = 0x80

 
    
class MidasLcd:
    
    def __init__(self, spi, rsPin):
    
        self.spi = spi
        self.rsPin = rsPin        
    
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.rsPin, GPIO.OUT)

        #registers init
        #Function set
        self.lcdCommand(0x38)
        #display on/off
        self.lcdCommand(0x0C)
        #display clear
        self.lcdCommand(0x01)
        #display mode
        self.lcdCommand(0x02)
        
    #end def

    def lcdCommand(self, byte):
    
        GPIO.output(self.rsPin, False)
        resp = self.spi.xfer([byte])
        
    #end def        

    def lcdWriteByte(self, bytes):
    
        GPIO.output(self.rsPin, True)
        resp = self.spi.xfer([bytes])
        time.sleep(0.01) # sleep for 0.01 seconds
        
    #end def

    def lcdWriteList(self, list):
    
        GPIO.output(self.rsPin, True)
        resp = self.spi.xfer(bytearray(list))
        
    #end def

    def lcdWriteLoc(self, list, line, loc, space = 0, addText = None):
    
        assert loc < MAX_LCD_LINE_SIZE and line < MAX_LCD_LINE_COUNT and loc+len(list) <= MAX_LCD_LINE_SIZE
        
        newList = list
            
        if(addText != None):
            for c in addText:
                newList += c
        if(space > 0):
            for i in range(space - len(newList)):
                newList += ' '
        
        if line != 0 : loc = LINE_2_ADDRESS_START + loc
        self.lcdCommand(loc | DDRAM_ADDRESS_REGISTER_MASK)
        self.lcdWriteList(newList)
    #end def
    
    def Close(self):
    
        #display clear
        self.lcdCommand(0x01)
        GPIO.cleanup(self.rsPin)
        self.spi.Close() #close the port before exit
        
    #end def
    










