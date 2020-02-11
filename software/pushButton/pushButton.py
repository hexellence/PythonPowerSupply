import time
from RPi import GPIO

PB_RELEASE_LONG_PRESS = 4
PB_LONG_PRESS = 3
PB_LOCKED = 5
PB_PRESS = 1
PB_RELEASE_SHORT_PRESS = 2
PB_IDLE = 0

PB_DEBOUNCE_TIME = 0.10 # 100ms

LONG_PRESS_THRESHOLD = 2    # 2 seconds

# For pulled up sense pins
PB_PRESS_PULL_UP_PIN = 0
PB_RELAX_PULL_UP_PIN = 1

PB_PRESS_PULL_DN_PIN = 1
PB_RELAX_PULL_DN_PIN = 0

class pushButtonDev(object):

    def __init__(self, gpio, isPulledUp):
        self.pin = gpio        
        self.prevState = 0
        self.currState = 0
        self.pressTimeTag = 0
        self.isFingerOn = False
        self.output = PB_IDLE
        if(isPulledUp == True):
            self.BUTTON_RELAXED = PB_RELAX_PULL_UP_PIN
            self.BUTTON_PRESSED = PB_PRESS_PULL_UP_PIN
        else:
            self.BUTTON_RELAXED = PB_RELAX_PULL_DN_PIN
            self.BUTTON_PRESSED = PB_PRESS_PULL_DN_PIN
            
    #end def

    def read_pushButton(self):
        currentTime = time.time()
        #button is active 0
        self.currState = GPIO.input(self.pin) 
        
        if((self.currState == self.BUTTON_RELAXED) and (self.prevState == self.BUTTON_RELAXED)):
            self.output = PB_IDLE
        
        #establish press
        if((self.currState == self.BUTTON_PRESSED) and (self.prevState == self.BUTTON_RELAXED)):
            #print("Press Detect")
            #DEBOUNCE
            time.sleep(PB_DEBOUNCE_TIME)
            self.currState = GPIO.input(self.pin)             
            if(self.currState == self.BUTTON_PRESSED):            
                #print("Press Established at %f" % currentTime)
                self.isFingerOn = True
                self.pressDuration = 0
                self.output = PB_PRESS
                self.pressTimeTag = currentTime
                
                
        #establish press and hold condition
        if(self.currState == self.BUTTON_PRESSED):
            if(self.output == PB_PRESS):
                if(self.isFingerOn == True):            
                    self.pressDuration = currentTime - self.pressTimeTag        
                    if(self.pressDuration > LONG_PRESS_THRESHOLD) and (self.output == PB_PRESS):
                        #establish long press condition
                        self.output = PB_LONG_PRESS
                        #print("Long Press Established at %f" % currentTime)
            elif(self.output == PB_LONG_PRESS):
                self.output = PB_LOCKED

        #establish release condition
        if((self.currState == self.BUTTON_RELAXED) and (self.prevState == self.BUTTON_PRESSED)):
            #Check press established
            #print("Release Detect")
            #DEBOUNCE
            time.sleep(PB_DEBOUNCE_TIME)
            if((self.currState == self.BUTTON_RELAXED) and (self.isFingerOn == True)):            
                #print("Release Established at %f" % currentTime)
                self.isFingerOn = False
                self.pressDuration = 0
                self.pressTimeTag = 0
                
                if((self.output == PB_LONG_PRESS) or (self.output == PB_LOCKED)):
                    self.output = PB_RELEASE_LONG_PRESS
                else:
                    self.output = PB_RELEASE_SHORT_PRESS    
                

        self.prevState = self.currState
        #print(self.output)
        return self.output
    #end def