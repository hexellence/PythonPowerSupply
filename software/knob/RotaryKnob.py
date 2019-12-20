import spidev
import time
import math
from RPi import GPIO

COUNT_MIN = 0
COUNT_MAX = 2400
POS_HIGH_SPEED_THRESHOLD = 110 # Clicks per second
NEG_HIGH_SPEED_THRESHOLD = -110 # Clicks per second
   
class rotKnob:
    
    def __init__(self, clk, dt):
    
        self.clk = clk
        self.dt = dt
        self.counter = 0
        self.lastCounter = 0
        self.speed = 0
        self.lastTime = 0
        
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
        currentTime = time.time()
        
        if self.clkState != self.clkLastState:
            if(self.dtState != self.clkState):
                self.counter += 1
                if(self.counter > COUNT_MAX):
                    self.counter = COUNT_MAX
            else:
                self.counter -= 1
                if(self.counter < COUNT_MIN):
                    self.counter = COUNT_MIN
                    
            self.clkLastState = self.clkState
            
            self.speed = (self.counter - self.lastCounter) / (currentTime - self.lastTime)

            if(self.speed > POS_HIGH_SPEED_THRESHOLD):
                self.counter = self.counter + 50
                if(self.counter > COUNT_MAX):
                    self.counter = COUNT_MAX
            elif(self.speed < NEG_HIGH_SPEED_THRESHOLD):
                self.counter = self.counter - 50
                if(self.counter < COUNT_MIN):
                    self.counter = COUNT_MIN
            
            self.lastCounter = self.counter
            self.lastTime = currentTime
        return self.counter
        
    #end def