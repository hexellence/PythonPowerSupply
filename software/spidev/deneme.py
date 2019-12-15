import spidev
import time
from RPi import GPIO


REGISTER_SELECT_PIN = 21 
MAX_LCD_LINE_SIZE = 16
MAX_LCD_LINE_COUNT = 2
LINE_2_ADDRESS_START = 0x40
DDRAM_ADDRESS_REGISTER_MASK = 0x80

clk = 17
dt = 18

def lcdCommand(byte):
	GPIO.output(REGISTER_SELECT_PIN, False)
	resp = spi.xfer([byte])
	time.sleep(0.01) # sleep for 0.1 seconds
#end def

def lcdWriteByte(byte):
	GPIO.output(REGISTER_SELECT_PIN, True)
	resp = spi.xfer(byte)
	time.sleep(0.01) # sleep for 0.1 seconds
#end def

def lcdWriteList(list):
	GPIO.output(REGISTER_SELECT_PIN, True)
	resp = spi.xfer(bytearray(list))
	time.sleep(0.01) # sleep for 0.1 seconds
#end def

def lcdWriteLoc(list, line, loc):
    assert loc < MAX_LCD_LINE_SIZE and line < MAX_LCD_LINE_COUNT and loc+len(list) <= MAX_LCD_LINE_SIZE
    if line != 0 : loc = LINE_2_ADDRESS_START + loc
    lcdCommand(loc | DDRAM_ADDRESS_REGISTER_MASK)
    lcdWriteList(list)

    
	
#end def

GPIO.setmode(GPIO.BCM)
GPIO.setup(clk, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(dt, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

counter = 0
clkLastState = GPIO.input(clk)

GPIO.setmode(GPIO.BCM)
GPIO.setup(REGISTER_SELECT_PIN, GPIO.OUT)


spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 540000
spi.lsbfirst = False
spi.mode = 3
spi.bits_per_word = 8

time.sleep(1)

#Function set
lcdCommand(0x38)
#display on/off
lcdCommand(0x0C)
#display clear
lcdCommand(0x01)
#display mode
lcdCommand(0x02)
lcdWriteLoc('0', 0, 0)


while True:
    clkState = GPIO.input(clk)
    dtState = GPIO.input(dt)
    if clkState != clkLastState:
        if dtState != clkState:
            counter += 1
        else:
            counter -= 1
        lcdWriteLoc(str(counter), 0, 0)        
        clkLastState = clkState
    time.sleep(0.01)

	
#end try



