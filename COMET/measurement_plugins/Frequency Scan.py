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
        starts the actual stripscan measurement, no further action need to be taken

        :param main_class:
        """
        super(FrequencyScan_class, self).__init__(main_class)
        self.log = logging.getLogger(__name__)
        self.main = main_class
        self.job = self.main.job_details["Frequency Scan"]
        self.job_details = self.main.job_details
        self.general_options = self.job["General"]
        self.measurements = self.job.copy()
        self.measurements.pop("General")

        # Define a few values, so inital ramp up values etc.
        # These varaibles are used for the stripscan preparations!!!
        self.voltage_End = self.general_options["Start Voltage [V]"]
        self.voltage_Start = 0
        self.voltage_steps = 10
        self.compliance = self.general_options["Compliance [uA]"]

        # Voltage step list
        self.voltage_ramp = self.ramp_value(self.general_options["Start Voltage [V]"],
                        self.general_options["End Voltage [V]"],
                        self.general_options["Voltage Step [V]"])

    def run(self):
        """This function conducts the measurements """
        self.do_preparations_for_stripscan(do_cal=False, measurement="Frequency Scan")

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

        self.clean_up[2]
        self.clean_up()

    def do_frequencyscan(self, iteration, voltage):
        '''This function performes a frequency scan of the lcr meter and at each step it executes a LIST of mesaurement'''

        # Loop over all measurements

        for func_name, measurement in self.measurements.items():
            if not self.main.event_loop.stop_all_measurements_query():

                start_freq = measurement["Start Freq [Hz]"]
                end_freq = measurement["End Freq [Hz]"]
                step_freq = measurement["Steps"]
                LCR_volt = measurement["Amplitude [mV]"]*0.001
                strip = measurement.get("Strip [#]", -1)

                # Generate frequency list
                freq_list = list(self.ramp_value_log10(start_freq, end_freq, step_freq))
                # Construct results array
                self.xvalues = np.zeros(len(freq_list))
                self.yvalues = np.zeros(len(freq_list))

                # Set the LCR amplitude voltage for measurement
                self.change_value(self.LCR_meter, "set_voltage", str(LCR_volt))


                for i, freq in enumerate(list(freq_list)): #does the loop over the frequencies
                    if not self.main.event_loop.stop_all_measurements_query(): #stops the loop if shutdown is necessary
                        yvalue = getattr(self, "do_" + func_name)(strip, samples=self.samples,
                                                         freqscan=True, frequency=freq, write_to_main=False)  # calls the measurement
                        self.yvalues[i] = yvalue
                        self.xvalues[i] = float(freq)

                # Append the data to the data array and sends it to the main as frequency scan measurement
                if not self.main.event_loop.stop_all_measurements_query():
                    if self.main.measurement_data[func_name + "_freq"][0][0]:
                        self.main.measurement_data[func_name + "_freq"][0] = np.vstack([self.main.measurement_data[func_name + "_freq"][0], self.xvalues])
                        self.main.measurement_data[func_name + "_freq"][1] = np.vstack([self.main.measurement_data[func_name + "_freq"][1], self.yvalues])
                    else:
                        self.main.measurement_data[func_name + "_freq"][0] = self.xvalues
                        self.main.measurement_data[func_name + "_freq"][1] = self.yvalues

                    self.main.queue_to_main.put({func_name + "_freq": [self.xvalues, self.yvalues]})

