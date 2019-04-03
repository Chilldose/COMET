from threading import Thread, Timer
from time import time
import logging


class Brandbox_temperature_humidity(Thread):
    """This class is reads out continiously the temperature and humidity from the Brandbox
    This class inherits all function from the threading class an therefore can be startet as thread."""

    def __init__(self, main, framework, update_intervall=5000):
        '''This starts the background and continuous tasks like humidity and temperature control'''

        Thread.__init__(self)
        self.main = main
        self.framework = framework
        self.stop_measurement_loop = self.main.stop_measurement_loop
        self.resource = framework["Devices"]["temphum_controller"]
        self.query = self.resource["get_enviroment"]
        self.update_intervall = float(update_intervall)
        self.queue_to_main = framework["Message_from_main"]
        self.vcw = framework["VCW"]
        self.log = logging.getLogger(__name__)

        # First try if visa_resource is valid
        self.success = False
        try:
            first_try = self.vcw.query(self.resource, self.query)
            if first_try and not -1:
                self.success = True

        except Exception as e:
            self.log.error("The temperature and humidity controller seems not to be responding. Error:" + str(e))

    def run(self):
        '''This is the update function for temp hum query'''

        if self.success:
            self.log.info("Humidity and temp control started...")
        else:
            self.log.info("Humidity and temp control NOT started...")

        if not self.stop_measurement_loop and self.success:
            try:
                values = self.vcw.query(self.resource, self.query)
                values = values.split(",")
                self.main.humidity_history.append(float(values[1]))  # todo: memory leak since no values will be deleted
                self.main.temperatur_history.append(float(values[0]))
                # Write the pt100 and light status and environement in the box to the global variables
                self.framework["Configs"]["config"]["settings"]["chuck_temperature"] = float(values[3])
                self.framework["Configs"]["config"]["settings"]["internal_lights"] = True if int(values[2]) == 1 else False
                self.queue_to_main.put({"temperature": [float(time.time()), float(values[0])],
                                   "humidity": [float(time.time()), float(values[1])]})
            except Exception as err:
                self.log.error(
                    "The temperature and humidity controller seems not to be responding. Error: {!s}".format(err))
            Timer(self.update_intervall / 1000.,
                            self.run).start()  # This ensures the function will be called again



