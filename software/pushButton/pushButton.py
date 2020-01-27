import time
from RPi import GPIO

PB_RELEASE_LONG_PRESS = 4
PB_LONG_PRESS = 3
PB_PRESS = 1
PB_RELEASE_SHORT_PRESS = 2
PB_IDLE = 0

LONG_PRESS_THRESHOLD = 2


class pushButtonDev(object):



    def __init__(self, gpio):
        self.pin = gpio
        self.prevState = 0
        self.currState = 0
        self.pressTimeTag = 0
        self.isFingerOn = False
        self.output = PB_IDLE
    #end def

    def read_pushButton(self):
        currentTime = time.time()
        #button is active 0
        self.currState = GPIO.input(self.pin) 
        
        if((self.currState == 1) and (self.prevState == 1)):
            self.output = PB_IDLE
        
        #establish press
        if((self.currState == 0) and (self.prevState == 1)):
            #print("Press Detect")
            #DEBOUNCE
            time.sleep(0.020)
            self.currState = GPIO.input(self.pin)             
            if(self.currState == 0):            
                #print("Press Established at %f" % currentTime)
                self.isFingerOn = True
                self.pressDuration = 0
                self.output = PB_PRESS
                self.pressTimeTag = currentTime
                
                
        #establish press and hold condition
        if((self.currState == 0) and (self.output == PB_PRESS)):
            if(self.isFingerOn == True):            
                self.pressDuration = currentTime - self.pressTimeTag        
                if(self.pressDuration > LONG_PRESS_THRESHOLD) and (self.output == PB_PRESS):
                    #establish long press condition
                    self.output = PB_LONG_PRESS
                    #print("Long Press Established at %f" % currentTime)


        #establish release condition
        if((self.currState == 1) and (self.prevState == 0)):
            #Check press established
            if((self.currState == 1) and (self.isFingerOn == True)):            
                #print("Release Established at %f" % currentTime)
                self.isFingerOn = False
                self.pressDuration = 0
                self.pressTimeTag = 0
                
                if(self.output == PB_LONG_PRESS):
                    self.output = PB_RELEASE_LONG_PRESS
                else:
                    self.output = PB_RELEASE_SHORT_PRESS    
                

        self.prevState = self.currState
        #print(self.output)
        return self.output
    #end def