#!/usr/bin/python


from nanpy import Arduino, OneWire, Lcd, serial_manager
from datetime import datetime, timedelta
from time import sleep
import dbcon
import sys


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
    autosave = False
    backlight = False
    temp_timer = 0
    lcd_update_timer = 0
    lcd_pir = None
    pwm_pin_state = {}
    tempC = {}
    _oldlcddata = None
    _conn = None

    def __init__(self):

            try:
                pass

            except:
                print 'Connection failed to ', self.device

    def lcdscreen(self, data):

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

        step = 25

        if state < self.pwm_pin_state[val]['state']:
            step = -step

        else:

            pass

        while self.pwm_pin_state[val]['state'] != state:

            self.pwm_pin_state[val]['state'] += step

            Arduino.analogWrite(self.pwm_pin_state[val]['pin'],
                                self.pwm_pin_state[val]['state'])

    def dRead(self, pin):

        Arduino.pinMode(pin, Arduino.INPUT)

        return Arduino.digitalRead(pin)

    def updatelcd(self):

        lcddata = self.getlcddata()

        if lcddata != self._oldlcddata:

            if (
                (self.lcd_pir is None) and
                any(self.pwm_pin_state) and
                (not self.backlight)
            ):

                self.pwm('lcd', 250)

                self.backlight = True

            self.lcdscreen(lcddata)

            self._oldlcddata = lcddata

        elif (self.lcd_pir is None) & (self.backlight):

            self.pwm('lcd', 0)

            self.backlight = False

    def pirbacklight(self):

        pir_state = self.dRead(self.lcd_pir)

        if (pir_state == 1) and (not self.backlight):

            self.pwm('lcd', 250)

            self.backlight = True

        elif (pir_state == 0 and self.backlight):

            self.pwm('lcd', 0)

            self.backlight = False

    @classmethod
    def device(cls, device):

        obj = cls()

        obj.device = device

        db = dbcon.connect()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM units WHERE device =%s",
                       (device,))

        arduino = cursor.fetchone()
        obj.aid = arduino[0]
        obj.autosave = arduino[3]
        obj.temp_timer = timedelta(seconds=arduino[4])
        obj.lcd_update_timer = timedelta(seconds=arduino[5])

        cursor.execute("SELECT addr, pin, location FROM equipment WHERE"
                       " id=%s and type=%s", (obj.aid, 'OneWire'))

        for record in cursor:
            print 'Onewire: ', record
            obj.onewire.append(record)

        try:

            cursor.execute("SELECT addr FROM equipment WHERE"
                           " id=%s and type=%s", (obj.aid, 'Lcd'))

            obj.Lcd = cursor.fetchone()[0]
            print 'Lcd: ', obj.Lcd

            if len(obj.Lcd) == 9:

                cls.pwm_pin_state['lcd'] = {
                    'pin': obj.Lcd[0],
                    'state': 0
                }

            cursor.execute("SELECT pin FROM equipment WHERE"
                           " id=%s and type=%s and addr=%s",
                           (obj.aid, 'Pir', ['Lcd']))
            obj.lcd_pir = cursor.fetchone()[0]

        except:
            pass

        cursor.close()
        db.close()
        obj._conn = serial_manager.connect(obj.device)
        return obj


def main():

    device = sys.argv[1]
    a1 = unit.device(device)

    owtimer = datetime.now() + a1.temp_timer

    nextlcdupdate = datetime.now() + a1.lcd_update_timer

    while True:

        print datetime.now()
        print 'OneWire timer: ', owtimer
        print 'Next lcd update :', nextlcdupdate

        if owtimer <= datetime.now():

            print 'Get temp'

            a1.gettemp()

            a1.wrlcddata()

            owtimer = datetime.now() + a1.temp_timer

        if nextlcdupdate <= datetime.now():

            a1.updatelcd()

            nextlcdupdate = datetime.now() + a1.lcd_update_timer

        if a1.lcd_pir:

            a1.pirbacklight()

        sleep(1)


if __name__ == '__main__':
    main()
