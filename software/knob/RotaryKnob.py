import spidev
import time
from RPi import GPIO

#user config
REGISTER_SELECT_PIN = 21 

#device dependent values
MAX_LCD_LINE_SIZE = 16
MAX_LCD_LINE_COUNT = 2
LINE_2_ADDRESS_START = 0x40
DDRAM_ADDRESS_REGISTER_MASK = 0x80

GPIO.setmode(GPIO.BCM)
GPIO.setup(REGISTER_SELECT_PIN, GPIO.OUT)
  
    
class rotKnob:
    
    def __init__(self, clk, dt):
    
        self.clk = clk
        self.dt = dt
        self.counter = 0
        
    #end def
    
    def open(self):
    
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.clk, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.dt, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
        self.clkLastState = GPIO.input(self.clk)        
    
    #end def

    def updateKnob(self):
    
        self.clkState = GPIO.input(self.clk)
        self.dtState = GPIO.input(self.dt)
        if self.clkState != self.clkLastState:
            if self.dtState != self.clkState:
                self.counter += 1
            else:
                self.counter -= 1
            self.clkLastState = self.clkState
            
        return self.counter
        
    #end def