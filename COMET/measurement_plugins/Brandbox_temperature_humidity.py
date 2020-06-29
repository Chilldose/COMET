from threading import Thread, Timer
from time import time
import logging
import random
import numpy as np


class Brandbox_temperature_humidity(Thread):
    """This class is reads out continiously the temperature and humidity from the Brandbox
    This class inherits all function from the threading class an therefore can be startet as thread."""

    def __init__(self, main, framework, update_interval=5000):
        """This starts the background and continuous tasks like humidity and temperature control"""

        Thread.__init__(self)
        self.main = main
        self.framework = framework
        self.stop_measurement_loop = self.main.stop_measurement_loop
        self.resource = framework["Devices"]["temphum_controller"]
        self.update_interval = float(update_interval)
        self.queue_to_main = framework["Message_to_main"]
        self.vcw = framework["VCW"]
        self.log = logging.getLogger(__name__)
        self.testmode = False
        self.running = False
        self.readqueue = False

        # First try if visa_resource is valid
        self.success = False
        try:
            first_try = self.vcw.query(self.resource, self.resource["get_environment"])
            self.framework["Configs"]["config"]["settings"]["light"] = True  # Dummy
            if first_try:
                self.success = True

        except Exception as e:
            self.log.error(
                "The temperature and humidity controller seems not to be responding. Error:"
                + str(e)
            )

    def run(self):
        """This is the update function for temp hum query"""

        if self.success and not self.running:
            self.log.info("Humidity and temp control started...")
            self.running = True
        elif self.testmode and not self.running:
            self.log.critical("Humidity and temp TEST MODE started!!!")
            self.running = True
        elif not self.running:
            self.log.info("Humidity and temp control NOT started...")
            return

        if not self.stop_measurement_loop and self.success:
            try:
                # Query the environemnt etc from Brandbox
                envvalues = self.vcw.query(
                    self.resource, self.resource["get_environment"]
                )
                envvalues = envvalues.split(",")

                # Get dewpoint
                boxvalues = self.vcw.query(
                    self.resource, self.resource["get_box_environment"]
                )
                boxvalues = boxvalues.split(",")

                vacuumvalues = self.vcw.query(
                    self.resource, self.resource["get_vacuum"]
                )

                # get light
                luxvalues = self.vcw.query(self.resource, self.resource["get_lux"])
                luxvalues = luxvalues.split(",")[0]

                # if an error happen, as so often with the brandbox read the queue
                if self.readqueue:
                    try:
                        ans = self.vcw.read(self.resource)
                        self.log.critical("Brandbox had an non empty queue: {}".format(ans))
                    except:
                        self.log.info("Brandbox indicated an non empty queue, reading queue yielded no queue...", exc_info=True)


                try:
                    if float(luxvalues) >= 0.5:
                        self.framework["Configs"]["config"]["settings"]["lights"] = True
                    else:
                        self.framework["Configs"]["config"]["settings"]["lights"] = False

                    # get door
                    # doorvalues = self.vcw.query(self.resource, self.resource["get_door"])
                    # doorvalues = doorvalues.split(",")[0]
                    # if doorvalues == "1":
                    #    self.framework["Configs"]["config"]["settings"]["door"] = False
                    # else:
                    #    self.framework["Configs"]["config"]["settings"]["door"] = True

                    # get light
                    vacuumvalues = vacuumvalues.split(",")[0]
                    if vacuumvalues == "1":
                        self.framework["Configs"]["config"]["settings"]["vacuum"] = True
                    else:
                        self.framework["Configs"]["config"]["settings"]["vacuum"] = False

                    # Here a list
                    self.main.humidity_history = np.append(
                        self.main.humidity_history, float(envvalues[1])
                    )  # todo: memory leak since no values will be deleted
                    self.main.temperatur_history = np.append(
                        self.main.humidity_history, float(envvalues[3])
                    )

                    # Write the pt100 and light status and environement in the box to the global variables
                    self.framework["Configs"]["config"]["settings"][
                        "chuck_temperature"
                    ] = float(envvalues[3])
                    self.framework["Configs"]["config"]["settings"][
                        "air_temperature"
                    ] = float(envvalues[0])
                    self.framework["Configs"]["config"]["settings"]["dew_point"] = float(
                        boxvalues[2]
                    )

                    # Send data to main
                    self.queue_to_main.put(
                        {
                            "temperature_air": [float(time()), float(envvalues[0])],
                            "temperature_chuck": [float(time()), float(envvalues[3])],
                            "dew_point": [float(time()), float(boxvalues[2])],
                            "humidity": [float(time()), float(envvalues[1])],
                        }
                    )
                except:
                    self.readqueue = True

            except Exception as err:
                self.log.error(
                    "The temperature and humidity controller seems not to be responding. Error: {!s}".format(
                        err
                    ),
                    exc_info=True,
                )

        elif self.testmode:
            self.log.critical("Testmode sends message to main!")
            self.queue_to_main.put(
                {
                    "temperature": [float(time()), float(random.randint(1, 10))],
                    "humidity": [float(time()), float(random.randint(1, 10))],
                }
            )

        if not self.main.stop_measurement_loop:
            self.start_timer(self.run)
        else:
            self.log.info(
                "Shutting down environment control due to stop of measurement loop"
            )

    def start_timer(self, object):
        Timer(
            self.update_interval / 1000.0, object
        ).start()  # This ensures the function will be called again
