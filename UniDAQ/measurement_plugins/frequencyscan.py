# This file manages the stripscan measurements and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
sys.path.append('../UniDAQ')
from .stripscan import stripscan_class


class frequencyscan_class(stripscan_class):

    def __init__(self, main_class):
        """
        This class takes only one parameter, the main class, in which all parameters must be prevalent. It further
        starts the actual stripscan measuremnt, no further action need to be taken

        :param main_class:
        """
        super(frequencyscan_class, self).__init__(main_class)
        self.log = logging.getLogger(__name__)
        self.start_freq = self.job["startfreq"]
        self.end_freq = self.job["endfreq"]
        self.step_freq = self.job["step"]
        self.LCR_volt = self.job["voltage"]
        self.measurements = self.job["measuremnts"]

    def run(self):
        """This function conducts the measurements """
        self.main.queue_to_main({"INFO": "Started frequencyscan measurement..."})
        self.do_preparations_for_stripscan()
        self.do_frequencyscan()

    def do_frequencyscan(self):
        '''This function performes a frequency scan of the lcr meter and at each step it executes a LIST of mesaurement'''

        if not self.main.main.stop_measurement():
            # Generate frequency list
            freq_list = self.main.ramp_value_log10(self.start_freq, self.end_freq, self.step_freq)

            # Create a measurement file for the frequency scan, (per strip)
            #if self.main.save_data:
            #    filepath = self.main.job_details["Filepath"]
            #    filename = "fre_strip_" + str(int(strip)) + "_" + self.main.job_details["Filename"]

            #    header = self.main.job_details["Header"]
            #    header += " #AC Voltage: " + str(voltage) + "\n"
            #    header += " #Measured strip: " + str(int(strip)) + "\n\n"
            #    for meas in measurement_obj:
            #        func_name = str(meas)
            #        header += str(func_name) + "\t\t\t\t"
            #    header += "\n"

            #    for meas in measurement_obj: # adds the units header
            #        header += "frequency [Hz]".ljust(self.justlength) +  "capacitance [F]".ljust(self.justlength)
            #    header += "\n"

            #    file = self.main.create_data_file(header, filepath, filename)

            # Set the LCR amplitude voltage for measurement
            self.main.change_value(self.LCR_meter, "set_voltage", str(self.LCR_volt))

            for freq in freq_list: #does the loop over the frequencies
                if not self.main.main.stop_measurement(): #stops the loop if shutdown is necessary
                    self.main.change_value(self.LCR_meter, "set_frequency", str(freq))
                    value = []
                    for i, meas in enumerate(self.measurements):
                        func_name = str(meas)
                        value.append(getattr(self, "do_" + func_name)(freq, samples=self.samples, freqscan=True)) #calls the measurement
                        # Append the data to the data array and sends it to the main as frequency scan measurement
                        if not self.main.main.stop_measurement():
                            self.main.measurement_data[func_name + "_scan"][0] = np.append(self.main.measurement_data[func_name + "_scan"][0],[float(freq)])
                            self.main.measurement_data[func_name + "_scan"][1] = np.append(self.main.measurement_data[func_name + "_scan"][1], [float(value[i])])
                            self.main.queue_to_main.put({func_name + "_scan": [float(freq), float(value[i])]})

                    if self.main.save_data:
                        string_to_write = ""
                        for val in value:
                            string_to_write += str(freq).ljust(self.justlength) + str(val).ljust(self.justlength)
                        self.main.write(self.main.measurement_files["frequencyscan"], string_to_write + "\n")
                    else:
                        break