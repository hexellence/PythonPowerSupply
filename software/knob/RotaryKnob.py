import spidev
import time
import math
from RPi import GPIO
import pigpio
SPEED_MEASUREMENT_WINDOW = 0.5
   
class rotKnob:
    
    def __init__(self, clkPin, dtPin, countMin = -10000, countMax = 10000, highSpeedThrs = -1, clickStep = 1, highSpeedStep = 100):
        
        # the pins must be in the same bank because we need to read them simultaneously
        assert ((clkPin < 32) and (dtPin < 32) and (clkPin >= 0) and (dtPin >= 0))
        # Definitions and Initialisaton 
        self.clkPin = clkPin
        self.dtPin = dtPin
        self.counter = 0
        self.prevCounter = 0
        self.firstCount = 0
        self.highSpeedThrs = highSpeedThrs
        self.clickStep = clickStep
        self.highSpeedStep = highSpeedStep
        self.firstTime = 0
        self.clkState = 0
        self.dtState = 0
        self.clkPinMask = 1 << self.clkPin
        self.dtPinMask = 1 << self.dtPin
        self.countMin = countMin
        self.countMax = countMax
        # Next will help to read pins at the same time. note that the pins should be in the same bank
        self.pi = pigpio.pi()
        
    #end def
    
    
    def open(self):
    
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.clkPin, GPIO.IN)
        GPIO.setup(self.dtPin, GPIO.IN) 
        self.clkLastState = GPIO.input(self.clkPin)
    
    #end def

    def Close(self):
    
        GPIO.cleanup(self.clkPin)
        GPIO.cleanup(self.dtPin)        
    
    #end def

    def updateKnob(self):
        
        gpioBank = self.pi.read_bank_1()    #read bank as a whole and decide pin values, this is needed because the pins should be read simultaneously
        self.clkState = (gpioBank & self.clkPinMask) == self.clkPinMask 
        self.dtState = (gpioBank & self.dtPinMask) == self.dtPinMask
        # time is needed to calculate click speed
        currentTime = time.time()
        clickSpeed = 0
          
        # protect agains divide by zero and start if there is a change in one of the pins
        if(self.clkState != self.clkLastState):
            if(self.firstCount == 0):
                self.firstCount = self.counter
                self.firstTime = currentTime
            
            if(self.dtState != self.clkState):
                # When clk state have an edge and if dt is following; this is the incerement direction
                currentStep = self.clickStep              
            else:
                # When clk state have an edge and if dt is leading; this is the decrement direction
                currentStep = -1*self.clickStep
            self.clkLastState = self.clkState
            
            # define a window for speed calculation
            if(currentTime > self.firstTime + SPEED_MEASUREMENT_WINDOW):
                clickSpeed = (self.counter - self.firstCount) / (currentTime - self.firstTime) / self.clickStep    
                self.firstCount = 0
                self.firstTime = 0.0      
                #print int(clickSpeed)                
                        
            # speed multiplier
            if(abs(clickSpeed) > self.highSpeedThrs) and (self.highSpeedThrs > 0):
                currentStep = currentStep * self.highSpeedStep
                #print("high speed")
            
            #contribute to counter
            self.counter += currentStep
            
            # limiter
            if(self.counter > self.countMax):
                    self.counter = self.countMax
            if(self.counter < self.countMin):
                    self.counter = self.countMin
            
        return self.counter
        
    #end def
    
    def InitialiseCounter(self, initialValue):
    
        self.counter = initialValue
        self.prevCounter = initialValue
    #end def
    
    def isKnobMove(self):
        tempOut = False
        if(self.counter != self.prevCounter):
            tempOut = True
            self.prevCounter = self.counter
        return tempOut
    