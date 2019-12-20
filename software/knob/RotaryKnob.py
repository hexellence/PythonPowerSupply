import spidev
import time
from RPi import GPIO


   
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