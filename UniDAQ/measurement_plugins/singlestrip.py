# This file manages the stripscan measurements and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
sys.path.append('../UniDAQ')
from .stripscan import stripscan_class


class singlestrip_class(stripscan_class):
    """Class for singlestrip measurements. It inherits everythin from the stripscan class"""

    def __init__(self, main_class):
        super(singlestrip_class, self).__init__(main_class)
        self.log = logging.getLogger(__name__)

    def run(self):
        """This function conducts the measurements defined for a single strip measurement"""
        self.main.queue_to_main({"INFO": "Started singlestrip measurement..."})
        self.do_preparations_for_stripscan()

        # use the function from the stripscan file
        self.do_one_strip(self.job["Strip"])

        # if not self.main.main.stop_measurement:
        #     measurement_header = "Pad".ljust(self.justlength)  # indicates the measurement
        #     unit_header = "#".ljust(self.justlength)  # indicates the units for the measurement
        #
        #     # Now add the new header to the file
        #     if self.main.save_data:
        #         self.main.write(self.main.measurement_files["stripscan"], measurement_header + "\n" + unit_header + "\n")
        #
        #     # Conduct the actual measurements and send it to the main
        #     for measurement in self.measurement_order:
        #         if measurement in self.job["Measurements"] and not self.main.main.stop_measurement:  # looks if measurement should be done
        #
        #             # Now conduct the measurement
        #             self.main.table.move_to_strip(self.sensor_pad_data, str(self.job["Strip"]), self.trans, self.T, self.V0, self.height)
        #             value = getattr(self, "do_" + measurement)(self.job["Strip"], self.samples, write_to_main = False)
        #
        #             # Write this to the file
        #             if value and self.main.save_data:
        #                 self.main.write(self.main.measurement_files["stripscan"],str(float(value)).ljust(self.justlength))  # Writes the value to the file
        #             else:
        #                 if self.main.save_data:
        #                     self.main.write(self.main.measurement_files["stripscan"],
        #                                     "--".ljust(self.justlength))  # Writes nothing if no value is aquired
        #
        #             # Write the data back to the GUI thread
        #             if value:
        #                 self.main.queue_to_main.put({str(measurement): [int(self.job["Strip"]), float(value)]})
        #
        #     # Write new line
        #     if self.main.save_data:
        #         self.main.write(self.main.measurement_files["stripscan"], "\n")