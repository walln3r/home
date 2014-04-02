#!/usr/bin/python


from nanpy import Arduino, OneWire, Lcd, serial_manager
from datetime import datetime
from time import sleep
from psycopg2 import extras
from redis import Redis
from rrdtool import update as rrd_update
import dbcon


class aio(object):

    unit = {}
    lcddata = []
    old_lcddata = []
    _con = None
    _queue = None

    def __init__(self):

            pass

    def serialconnection(self):

        self._con = serial_manager.connect(self.unit['device'])

    def wr(self):

        for key in self.unit['onewire']:

            ds_name = (self.unit['location'] +
                       self.unit['onewire'][key]['location'].replace(' ', ''))

            temp = round(self.unit['onewire'][key]['temp'], 2)

            toqueue = (self.unit['onewire'][key]['location'] + ':'
                       ' ' + str(temp))

            self._queue.rpush(self.unit['lcd'][0]['addr'], toqueue)

            r = rrd_update('/home/cubie/python/aio/rrddata/%s.rrd' % (ds_name),
                           'N:%s' % (temp))
            print r
            print 'DSNAME: %s, TEMP: %s' % (ds_name, temp)

    def getlcddata(self):

        while True:

            row = self._queue.lpop(self.unit['lcd'][0]['addr'])
            if row is not None:
                self.lcddata.insert(0, row)

            else:
                try:
                    self.lcddata = self.lcddata[0:4]
                    break
                except:
                    break

    def get_eq_arduino_device(self, aid):

        a = {}

        db = dbcon.connect()
        cursor = db.cursor(cursor_factory=extras.DictCursor)

        cursor.execute("SELECT * FROM units WHERE id =%s",
                       (aid,))

        for record in cursor:

            a = {
                'id': aid,
                'location': record['location'],
                'device': record['device'],
            }

        cursor.close()
        db.close()

        return a

    def get_eq_arduino_id(self, device):

        a = {}

        db = dbcon.connect()
        cursor = db.cursor(cursor_factory=extras.DictCursor)

        cursor.execute("SELECT * FROM units WHERE device =%s",
                       (device,))

        for record in cursor:

            a = {
                'id': record['id'],
                'location': record['location'],
                'device': device,
            }

        cursor.close()
        db.close()

        return a

    def get_eq_onewire(self):

        db = dbcon.connect()
        cursor = db.cursor(cursor_factory=extras.DictCursor)

        onewire = {}

        cursor.execute("SELECT room, location, addr, location, pin, power FROM"
                       " equipment WHERE id=%s and type=%s",
                       (self.unit['id'], 'OneWire'))

        for index, record in enumerate(cursor):

            onewire[index] = {
                'room': record['room'],
                'location': record['location'],
                'addr': record['addr'],
                'pin': record['pin'],
                'power': record['power'],
                'temp': None,
                'lastupdate': None,
            }

        cursor.close()
        db.close()

        return onewire

    def get_eq_lcd(self):

        db = dbcon.connect()
        cursor = db.cursor(cursor_factory=extras.DictCursor)

        lcd = {}

        cursor.execute("SELECT room, location, addr, pin FROM equipment"
                       " WHERE id=%s and type=%s", (self.unit['id'], 'Lcd'))

        for index, record in enumerate(cursor):

            lcd[index] = {
                'room': record['room'],
                'location': record['location'],
                'addr': record['addr'],
                'backlightPin': record['pin'],
                'backlightState': False,
                'pwmState': 0,
            }

        cursor.close()
        db.close()

        return lcd

    def get_eq_pir(self):

        db = dbcon.connect()
        cursor = db.cursor(cursor_factory=extras.DictCursor)

        pir = {}

        cursor.execute("SELECT room, location, addr, pin FROM equipment WHERE"
                       " id=%s and type=%s ", (self.unit['id'], 'Pir', ))

        for index, record in enumerate(cursor):

            pir[index] = {
                'room': record['room'],
                'location': record['location'],
                'addr': record['addr'],
                'pin': record['pin'],
                'state': None
            }

        cursor.close()
        db.close()

        return pir

    def get_eq_servo(self):

        db = dbcon.connect()
        cursor = db.cursor(cursor_factory=extras.DictCursor)

        servo = {}

        cursor.execute("SELECT room, location, pin FROM equipment WHERE"
                       " id=%s and type=%s ", (self.unit['id'], 'Servo', ))

        for index, record in enumerate(cursor):

            servo[index] = {
                'room': record['room'],
                'location': record['location'],
                'pin': record['pin'],
            }

        cursor.close()
        db.close()

        return servo

    def updatelcd(self):

        self.getlcddata()

        if self.lcddata != self.old_lcddata:

            lcd = Lcd((self.unit['lcd'][0]['addr'][0:6]),
                      (self.unit['lcd'][0]['addr'][6:8]))

            for index, item in enumerate(self.lcddata):
                if index < 4:

                    lcd.setCursor(0, index)
                    lcd.printString(item)

                else:
                    print 'To many rows to print, max 4'

            if (
                (not self.unit['pir']) and
                (not self.unit['lcd'][0]['backlightState'])
            ):
                self.pwmLcdBacklight(250)

            self.old_lcddata = self.lcddata

        elif (
            (not self.unit['pir']) and
            (self.unit['lcd'][0]['backlightState'])
        ):
            self.pwmLcdBacklight(0)

    def readonewire(self):

        for key in self.unit['onewire']:

            data = []

            one = OneWire(self.unit['onewire'][key]['pin'])
            one.reset()
            one.select(self.unit['onewire'][key]['addr'])
            one.write(0x44, 1)
            sleep(float(750) / 1000)
            one.reset()
            one.select(self.unit['onewire'][key]['addr'])
            one.write(0xBE)

            for i in range(9):
                val = one.read()
                data.append(val)

            raw = (data[1] << 8) | data[0]

            cfg = (data[4] & 0x60)
            if cfg == 0x00:
                raw = raw << 3
            elif cfg == 0x20:
                raw = raw << 2
            elif cfg == 0x40:
                raw = raw << 1

            if raw < 2048:
                temp = (raw / 16.0)
            else:
                temp = -((~raw & 0xffff) >> 2) / 16.0

            time = datetime.now().strftime('%H:%M:%S')
            self.unit['onewire'][key].update(temp=(temp))
            self.unit['onewire'][key].update(lastupdate=str(time))

            del one

    def pirSense(self):

        for key in self.unit['pir']:

            pin = self.unit['pir'][key]['pin']

            Arduino.pinMode(pin, Arduino.INPUT)
            self.unit['pir'][key].update(state=Arduino.digitalRead(pin))

    def pwmLcdBacklight(self, newState):

        step = 25

        if newState < self.unit['lcd'][0]['pwmState']:
            step = -step

        while self.unit['lcd'][0]['pwmState'] != newState:

            self.unit['lcd'][0]['pwmState'] += step
            Arduino.analogWrite(self.unit['lcd'][0]['backlightPin'],
                                self.unit['lcd'][0]['pwmState'])

        if (self.unit['lcd'][0]['pwmState'] > 128):

            self.unit['lcd'][0]['backlightState'] = True

        else:

            self.unit['lcd'][0]['backlightState'] = False

    def pirBacklight(self):

        pin = self.unit['pir']['0']['pin']
        backlight = self.unit['lcd']['0']['backlightState']
        state = self.pirSense(pin)

        if (state == 1 and not backlight):
            self.pwmLcdBacklight(250)

        if (state == 0 and backlight):
            self.pwmLcdBacklight(0)

    def msgQueue(self):

        var = self._queue.lpop(self.unit['id'])

        if var is not None:

            print 'from in queue: ', var

            if var == 'unit':

                self._queue.rpush('web', str(self.unit))

    @classmethod
    def allid(cls):

        result = []

        db = dbcon.connect()
        cursor = db.cursor()

        cursor.execute("SELECT id FROM units")

        for record in cursor:

            result.append(cls.fromid(record[0]))

        cursor.close()
        db.close()

        return result

    @classmethod
    def fromid(cls, aid, connect=False):

        obj = cls()
        obj.unit = obj.get_eq_arduino_device(aid)

        obj.unit.update(onewire=obj.get_eq_onewire())
        obj.unit.update(lcd=obj.get_eq_lcd())
        obj.unit.update(pir=obj.get_eq_pir())
        obj.unit.update(servo=obj.get_eq_servo())
        obj._queue = Redis()
        if connect:
            obj.serialconnection()

        return obj

    @classmethod
    def fromdevice(cls, device, connect=False):

        obj = cls()
        obj.unit = obj.get_eq_arduino_id(device)

        obj.unit.update(onewire=obj.get_eq_onewire())
        obj.unit.update(lcd=obj.get_eq_lcd())
        obj.unit.update(pir=obj.get_eq_pir())
        obj.unit.update(servo=obj.get_eq_servo())
        obj._queue = Redis()
        if connect:
            obj.serialconnection()

        return obj
