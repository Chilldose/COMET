from threading import Thread, Timer
from time import time
import logging
try:
    import Adafruit_DHT
except:
    pass




class OneWireEnv(Thread):
    """This class is for reading out one wire sensors with the rpi"""

    def __init__(self, main, framework, update_interval=5000):
        '''This starts the background and continuous tasks like humidity and temperature control'''

        Thread.__init__(self)
        self.main = main
        self.framework = framework
        self.stop_measurement_loop = self.main.stop_measurement_loop
        self.update_interval = float(update_interval)
        self.queue_to_main = framework["Message_to_main"]
        self.settings = framework["Configs"]["config"]["settings"]
        self.sensors = self.settings["Sensors"]
        self.log = logging.getLogger(__name__)
        self.running = False

        # First try if DHT resource is valid and accessible
        self.success_DHT = False
        try:
            import Adafruit_DHT
            for name, sensor in self.sensors.items():
                sensortype = getattr(Adafruit_DHT, sensor["type"])
                humidity, temperature = Adafruit_DHT.read(sensortype, sensor["pin"])
                if not humidity and not temperature:
                    self.log.critical("Sensor {} at pin {} for room {} did not answer.".format(sensortype, sensor["pin"], name))
            self.success_DHT = True
        except Exception as e:

            self.log.error("The temperature and humidity controller seems not to be responding. Error:" + str(e))

        # Try to query the 

    def run(self):
        '''This is the update function for temp hum query'''

        if self.success_DHT and not self.running:
            self.log.info("Humidity and temp control started...")
            self.running = True
        elif not self.running:
            self.log.info("Humidity and temp control NOT started...")
            return

        if not self.stop_measurement_loop and self.success:
            try:
                for name, sensor in self.sensors.items():
                    sensortype = getattr(Adafruit_DHT, sensor["type"])
                    humidity, temperature = Adafruit_DHT.read_retry(sensortype, sensor["pin"])
                    self.queue_to_main.put({"Temp_"+name: [float(time()), float(temperature)],
                                            "Hum_"+name: [float(time()), float(humidity)]})
            except Exception as err:
                self.log.error(
                    "The temperature and humidity controller seems not to be responding. Error: {!s}".format(err))

        if not self.main.stop_measurement_loop:
            self.start_timer(self.run)
        else:
            self.log.info("Shutting down environment control due to stop of measurement loop")


    def start_timer(self, object):
        Timer(self.update_interval / 1000.,object).start()  # This ensures the function will be called again



