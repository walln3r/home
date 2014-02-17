#!/usr/bin/python


from nanpy import OneWire, Lcd, serial_manager
from time import sleep


class unit(object):

    onewire_pin = None
    onewire_addr = None
    lcd_addr = None

    def __init__(self, device):

        if device == '':

            print 'Need device'

        else:

            try:
                serial_manager.connect(device)
            except:
                print 'Connection failed to %s' % device

    def lcd(self, data):
        lcd = Lcd((self.lcd_addr[0:6]), (self.lcd_addr[6:8]))

        try:
            for index, item in enumerate(data):
                if index < 4:

                    lcd.setCursor(0, index)
                    lcd.printString('%s' % (item))

                else:
                    print 'To many rows to print, max 4'

        except:
            print 'Failed to write %s to addr %s' % data, self.lcd_addr

    def gettemp(self):

        tempC = {}

        try:
            for item in self.onewire_addr:

                data = []

                one = OneWire(self.onewire_pin)
                one.reset()
                one.select(item)
                one.write(0x44, 1)
                sleep(float(750) / 1000)
                one.reset()
                one.select(item)
                one.write(0xBE)

                for i in range(9):
                    val = one.read()
                    data.append(val)

                raw = (data[1] << 8) | data[0]
                """ leftshit data[1], binary OR data[0]
                """
                cfg = (data[4] & 0x60)

                if cfg == 0x00:
                    raw = raw << 3
                elif cfg == 0x20:
                    raw = raw << 2
                elif cfg == 0x40:
                    raw = raw << 1

                tempC[str(item)] = (raw / 16.0)

                one = None
                """ Need this to reset the OneWire instance so a new
                               read can be performed.
                """

        except:
                print 'Could not read sensordata'

        return tempC
