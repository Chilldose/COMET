# This file manages the stripscan measurements and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
sys.path.append('../COMET')
try:
    from .Stripscan import Stripscan_class
except:
    from .stripscan import Stripscan_class



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
        self.numVSteps = len(self.voltage_ramp)
        self.numMSteps = len(self.measurements)
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
            self.do_frequencyscan(iter+1, volt)

        for i, func_name in enumerate(self.measurements.keys()):
            self.write_to_file(self.main.measurement_files["Frequency Scan"], self.voltage_ramp, self.main.measurement_data[func_name + "_freq"][0],
                           self.main.measurement_data[func_name + "_freq"][1])
            if i > 0:
                self.log.critical("ASCII output cannot cope with multiple data structures, output may be compromised.")

        self.write_to_json()

        self.clean_up()

    def write_to_json(self):
        """Writes the individual data arrays to stand alone json files for easy plotting"""
        for i, func_name in enumerate(self.measurements.keys()): # Measuremnts
            data_to_dump = {}
            for j, data in enumerate(zip(self.main.measurement_data[func_name + "_freq"][0], self.main.measurement_data[func_name + "_freq"][1])): # Voltage steps
                data_to_dump["{}V".format(self.voltage_ramp[j])] = [data[0], data[1]]
            new_name = {"Filename": self.job_details["Filename"]+"_{}".format(func_name)}
            details = self.job_details.copy()
            details.update(new_name)
            self.main.save_data_as("json", details, data=data_to_dump, xunits=("frequency", "Hz"), yunits=("capacitance", "F"))


    def do_frequencyscan(self, iteration, voltage):
        '''This function performes a frequency scan of the lcr meter and at each step it executes a LIST of mesaurement'''

        # Loop over all measurements
        step = 0
        for func_name, measurement in self.measurements.items():
            if not self.main.event_loop.stop_all_measurements_query():
                step+=1
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

                # Move to strip if necessary
                if strip > 0 and self.main.framework['Configs']['config']['settings']["Alignment"]:
                    if not self.main.table.move_to_strip(self.sensor_pad_data,
                                                     strip,
                                                     self.trans, self.T, self.V0, self.height):
                        self.log.error("Could not move to strip {}".format(strip))
                        break
                elif not self.main.framework['Configs']['config']['settings']["Alignment"]:
                    self.log.critical("No alignment done, conducting frequency scan without moving table!")


                for i, freq in enumerate(list(freq_list)): #does the loop over the frequencies
                    if not self.main.event_loop.stop_all_measurements_query(): #stops the loop if shutdown is necessary
                        self.main.framework['Configs']['config']['settings']['progress'] = (i+1)/len(freq_list)
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

    def write_to_file(self, file, voltages, xvalues, yvalues):
        """
        Writes data to the ascii file
        """
        # Check if length of voltages matches the length of data array
        if len(xvalues) == len(yvalues):
            data = np.array([xvalues, yvalues])
            # data = np.transpose(data)
            # Write voltage header for each measurement first the voltages
            self.main.write(file,
                            '' + ''.join([format(el, '<{}'.format(self.justlength * 2)) for el in voltages]) + "\n")
            # Then the Units
            self.main.write(file, ''.join([format("frequency[Hz]{}capacitance[F]".format(" " * (self.justlength - 7)),
                                                  '<{}'.format(self.justlength * 2)) for x in
                                           range(len(voltages))]) + "\n")

            for i in range(len(data[0, 0, :])):
                freq = [format(time, '<{}'.format(self.justlength)) for time in data[:, :, i][0]]
                cap = [format(curr, '<{}'.format(self.justlength)) for curr in data[:, :, i][1]]
                final = "".join([t + c for t, c in zip(freq, cap)])
                self.main.write(file, final + "\n")
        else:
            self.log.error("Length of results array are non matching, abort storing data to file")

