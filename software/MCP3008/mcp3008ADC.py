

class mcp3008(object):

    def __init__(self, spi, vref):
    
        assert(spi != None)
        self.spi = spi
        self.vRef = vref

    #end def

    def read_adcStep(self, ch_number):
        assert 0 <= ch_number <= 7
        cmdByte1 = 0x01
        cmdByte2 = 0x80 | (ch_number << 4)
        cmdByte3 = 0x00
        step = self.spi.xfer2([cmdByte1, cmdByte2, cmdByte3])
        return step
        #end def
        
        
    def read_adcMilliVolts(self, ch_number):
            step = self.read_adcStep(ch_number)
            voltage = (step[1] << 8) + step[2]
            return voltage * self.vRef / 1024
        #end def   