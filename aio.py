#!/usr/bin/python


from nanpy import Arduino, OneWire, Lcd, serial_manager
from datetime import datetime
from time import sleep
import dbcon


class setup(object):

    """
    This class is not in use or ready to be used
    """

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
    pwm_pin_state = {}
    tempC = {}

    def __init__(self):

            try:
#                serial_manager.connect(self.device)
                pass

            except:
                print 'Connection failed to %s' % self.device

    def lcdscreen(self, data):
        serial_manager.connect(self.device)
        lcd = Lcd((self.Lcd[1:7]), (self.Lcd[7:9]))

        try:
            for index, item in enumerate(data):
                if index < 4:

                    lcd.setCursor(0, index)
                    lcd.printString('%s' % (item))

                else:
                    print 'To many rows to print, max 4'

        except:
            print 'Failed to write %s to addr %s' % data, self.lcd

    def wrlcddata(self):

        db = dbcon.connect()
        cursor = db.cursor()

        for key in self.tempC:

            string = str(key) + ': ' + str(self.tempC[key]['temp'])

            cursor.execute("INSERT INTO lcdata (aid, data) VALUES"
                           "(%s, %s)", (self.aid, string))
            db.commit()

        cursor.close()
        db.close

    def getlcddata(self):

        db = dbcon.connect()
        cursor = db.cursor()

        result = []

        cursor.execute("SELECT data FROM lcdata WHERE aid=%s", (str(self.aid)))

        for row in cursor.fetchall():

            result.append(row[0])

        result.reverse()

        cursor.close()
        db.close()

        return result[0:4]

    def gettemp(self):
        serial_manager.connect(self.device)
        self.tempC = {}

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

                self.tempC[item[2]] = {
                    'addr': item[0],
                    'temp': ((raw / 16.0)),
                    'time': datetime.today()

                }

                one = None
                """ Need this to reset the OneWire instance so a new
                    read can be performed. There's probably another way
                    to do this, but i dont feel like exploring that now.
                """

        except:

                print 'Could not read sensordata'

        if self.autosave:

            self.wr(self.tempC)

        else:

            pass

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

    def pwm(self, val, state):

        serial_manager.connect(self.device)

        step = 5

        if state < self.pwm_pin_state[val]['state']:
            step = -step

        else:

            pass

        while self.pwm_pin_state[val]['state'] != state:

            self.pwm_pin_state[val]['state'] += step

            Arduino.analogWrite(self.pwm_pin_state[val]['pin'],
                                self.pwm_pin_state[val]['state'])

#           sleep(0.0001)

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

        try:

            cursor.execute("SELECT addr FROM equipment WHERE"
                           " id=%s and type=%s", (obj.aid, 'Lcd'))

            obj.Lcd = cursor.fetchone()[0]

            cls.pwm_pin_state[0] = {
                'pin': obj.Lcd[0],
                'state': 0
            }

        except:
            pass

        cursor.close()
        db.close()

        return obj


def main():

    device = ('/dev/ttyACM0')
    a1 = unit.device(device)
    run = 0
    oldlcdata = ''

    while True:

        if run == 0:

            a1.gettemp()

            a1.wrlcddata()

        lcdata = a1.getlcddata()
        print 'GET lcdata: ', lcdata

        if lcdata != oldlcdata:

            print 'Updating LCD'

            a1.pwm(0, 255)

            a1.lcdscreen(lcdata)

            oldlcdata = lcdata

        sleep(5)

        a1.pwm(0, 0)

        if run < 60:

            print 'Run: ', run
            run += 1

        else:

            run = 0
            print 'Resetting run to: ', run

if __name__ == '__main__':
    main()
