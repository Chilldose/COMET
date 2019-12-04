# This file manages the stripscan measurements and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
sys.path.append('../COMET')
from .Stripscan import Stripscan_class


class FrequencyScan_class(Stripscan_class):

    def __init__(self, main_class):
        """
        This class takes only one parameter, the main class, in which all parameters must be prevalent. It further
        starts the actual stripscan measuremnt, no further action need to be taken

        :param main_class:
        """
        super(FrequencyScan_class, self).__init__(main_class)
        self.log = logging.getLogger(__name__)
        self.general_options = self.job["General"]
        self.measurements = self.job.copy()
        self.measurements.pop("General")

        # Define a few values, so inital ramp up values etc.
        self.voltage_End = self.measurements["Start Voltage [V]"]
        self.voltage_Start = 0
        self.voltage_steps = 10
        self.compliance = self.measurements["Compliance [uA]"]

        # Voltage step list
        self.voltage_ramp = self.ramp_value(self.measurements["Start Voltage [V]"],
                        self.measurements["End Voltage [V]"],
                        self.measurements["Voltage Step [V]"])

    def run(self):
        """This function conducts the measurements """
        self.main.queue_to_main({"INFO": "Started frequency scan measurement..."})
        self.do_preparations_for_stripscan()

        # Do the voltage ramp
        for iter, volt in enumerate(self.voltage_ramp):
            self.change_value(self.bias_SMU, "set_voltage", str(volt))
            self.main.framework['Configs']['config']['settings']["bias_voltage"] = volt
            if self.steady_state_check(self.bias_SMU, command="get_read_current", max_slope=1e-8, wait=0.05, samples=7,
                                       Rsq=0.8,
                                       compliance=self.compliance):  # Is a dynamic waiting time for the measuremnts
                self.current_voltage = self.main.framework['Configs']['config']['settings']["bias_voltage"]
                if self.check_compliance(self.bias_SMU, self.compliance):  # if compliance is reached stop everything
                    self.stop_everything()
            else:
                self.stop_everything()
            self.do_frequencyscan(iter, volt)

    def do_frequencyscan(self, iteration, voltage):
        '''This function performes a frequency scan of the lcr meter and at each step it executes a LIST of mesaurement'''

        # Loop over all measurements
        for func_name, measurement in self.measurements.items():
            if not self.main.event_loop.stop_all_measurements_query():

                start_freq = measurement["Start Freq [Hz]"]
                end_freq = measurement["End Freq [Hz]"]
                step_freq = measurement["Steps per decade"]
                LCR_volt = measurement["Amplitude [mV]"]

                # Generate frequency list
                freq_list = self.ramp_value_log10(start_freq, end_freq, step_freq)

                # Set the LCR amplitude voltage for measurement
                self.change_value(self.LCR_meter, "set_voltage", str(LCR_volt))

                for freq in freq_list: #does the loop over the frequencies
                    if not self.main.event_loop.stop_all_measurements_query(): #stops the loop if shutdown is necessary
                        value = []
                        value.append(getattr(self, "do_" + func_name)(freq, samples=self.samples, freqscan=True)) #calls the measurement
                        # Append the data to the data array and sends it to the main as frequency scan measurement
                        if not self.main.event_loop.stop_all_measurements_query():
                            self.main.measurement_data[func_name + "_freq"][0] = np.append(self.main.measurement_data[func_name + "_freq"][0],[float(freq)])
                            self.main.measurement_data[func_name + "_freq"][1] = np.append(self.main.measurement_data[func_name + "_freq"][1], [float(value[i])])
                            self.main.queue_to_main.put({func_name + "_freq": [float(freq), float(value[i])]})

                        #if self.main.save_data:
                        #    string_to_write = ""
                        #    for val in value:
                        #        string_to_write += str(freq).ljust(self.justlength) + str(val).ljust(self.justlength)
                        #    self.main.write(self.main.measurement_files["frequencyscan"], string_to_write + "\n")
                        #else:
                        #    break
        # Create single json output file for this measuremenet run
        # Todo: