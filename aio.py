#!/usr/bin/python


from nanpy import OneWire, Lcd, serial_manager
from datetime import datetime
from time import sleep
import dbcon


class setup(object):

    onewire_pin = 0
    lcd = []
    unit = {}
    onewire = []
    device = ''

    def __init__(self, device):

        try:

            self.device = device

            qone = self.axk('Search OneWire sensors? y/n', ('y', 'n'))
            if qone == 'y':
                self.onewire_pin = raw_input('OneWire pin: ')
                self.onewire = self.searchonewire()

            qlcd = self.axk('Add Lcd? y/n', ('y', 'n'))

            if qlcd == 'y':
                self.lcd = raw_input('Lcd pins: ')

        except:
            print 'Nope'

    def searchonewire(self):
        serial_manager.connect(self.device)
        one = OneWire(self.onewire_pin)
        search = ''
        run = 0
        result = {}
        while True:
            search = one.search()
            if search == '1':
                return result
            else:
                result[run] = {
                    'addr': search
                }
                run += 1

    def axk(self, quest, valid):
        val = ''
        while val not in valid:
            print quest
            val = raw_input(quest, ' : ')
        return val


class unit(object):

    onewire = []
    Lcd = None
    device = None
    aid = None
    autosave = True

    def __init__(self):

            try:
                pass

            except:
                print 'Connection failed to %s' % self.device

    def lcdscreen(self, data):
        serial_manager.connect(self.device)
        lcd = Lcd((self.Lcd[0:6]), (self.Lcd[6:8]))

        try:
            for index, item in enumerate(data):
                if index < 4:

                    lcd.setCursor(0, index)
                    lcd.printString('%s' % (item))

                else:
                    print 'To many rows to print, max 4'

        except:
            print 'Failed to write %s to addr %s' % data, self.lcd

    def gettemp(self):
        serial_manager.connect(self.device)
        tempC = {}
        try:
            for item in self.onewire:

                data = []

                one = OneWire(item[1])
                one.reset()
                one.select(item[0])
                one.write(0x44, 1)
                sleep(float(750) / 1000)
                one.reset()
                one.select(item[0])
                one.write(0xBE)

                for i in range(9):
                    val = one.read()
                    data.append(val)

                raw = (data[1] << 8) | data[0]
                """ leftshift data[1], binary OR data[0]
                """
                cfg = (data[4] & 0x60)

                if cfg == 0x00:
                    raw = raw << 3
                elif cfg == 0x20:
                    raw = raw << 2
                elif cfg == 0x40:
                    raw = raw << 1

                tempC[item[2]] = {
                    'addr': item[0],
                    'temp': ((raw / 16.0)),
                    'time': datetime.today()
                }

                one = None
                """ Need this to reset the OneWire instance so a new
                    read can be performed.
                """

        except:
                print 'Could not read sensordata'

        if self.autosave:
            self.wr(tempC)

        else:
            pass

        return tempC

    def wr(self, data):
        try:
            db = dbcon.connect()
            cursor = db.cursor()
            for key in data:
                cursor.execute("INSERT INTO sensordata (addr, data, time)"
                               " VALUES (%s, %s, %s)",
                              (data[key]['addr'], data[key]['temp'],
                               data[key]['time']))

            db.commit()
            cursor.close()
            db.close()
        except:
            print 'Failed to write %s to database', dict(data)

    @classmethod
    def device(cls, device):
        obj = cls()
        obj.device = device

        db = dbcon.connect()
        cursor = db.cursor()

        cursor.execute("SELECT id FROM units WHERE device =%s",
                       (device,))
        obj.aid = cursor.fetchone()[0]

        cursor.execute("SELECT addr, pin, location FROM equipment WHERE"
                       " id=%s and type=%s", (obj.aid, 'OneWire'))
        for record in cursor:
            obj.onewire.append(record)

        cursor.execute("SELECT addr FROM equipment WHERE"
                       " id=%s and type=%s", (obj.aid, 'Lcd'))
        obj.Lcd = cursor.fetchone()[0]

        cursor.close()
        db.close()

        return obj
