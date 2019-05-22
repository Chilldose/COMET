# This file manages the stripscan measurements and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
sys.path.append('../UniDAQ')
from ..utilities import transformation


class stripscan_class:

    def __init__(self, main_class):
        """
        This class takes only one parameter, the main class, in which all parameters must be prevalent. It further
        starts the actual stripscan measuremnt, no further action need to be taken

        :param main_class:
        """

        self.main = main_class
        self.trans = transformation()
        self.vcw = self.main.framework["VCW"]
        self.switching = self.main.switching
        self.current_voltage = self.main.settings["settings"]["bias_voltage"]
        self.voltage_Start = self.main.job_details["frequencyscan"]["StartVolt"]
        self.voltage_End = self.main.job_details["frequencyscan"]["EndVolt"]
        self.voltage_steps = self.main.job_details["frequencyscan"]["Steps"]
        self.complience = self.main.job_details["frequencyscan"]["Complience"]
        self.bias_SMU = self.main.devices["BiasSMU"]
        self.LCR_meter = self.main.devices["Agilent E4980A"]
        self.SMU2 = self.main.devices["2410 Keithley SMU"]
        self.discharge_SMU = self.main.devices["2410 Keithley SMU"]
        self.discharge_switching = self.main.devices["temphum_controller"]
        self.elmeter = self.main.devices["6517B Keithley Elektrometer"]
        self.current_strip = self.main.main.default_dict["settings"]["current_strip"] # Current pad position of the table
        self.height = self.main.main.default_dict["settings"]["height_movement"]
        self.samples = 3
        self.T = self.main.main.default_dict["settings"]["trans_matrix"]
        self.V0 = self.main.main.default_dict["settings"]["V0"]
        self.job = self.main.job_details
        self.sensor_pad_data = self.main.pad_data[self.job["Project"]][self.job["Sensor"]]
        self.justlength = 2
        self.project = self.main.settings["settings"]["Current_project"] # Warning these values are mutable while runtime!!!
        self.sensor = self.main.settings["settings"]["Current_sensor"] # Use with care!!!
        self.log = logging.getLogger(__name__)

    def run(self):
        self.do_frequencyscan()

    def stop_everything(self):
        """Stops the measurement
        A signal will be genereated and send to the event loops, which sets the statemachine to stop all measurements"""
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)
        self.log.warning("Measurement STOP was called, check logs for more information")

    def do_setup_preparations(self):
        """This function prepares the setup, like ramping the voltage and steady state check
        """
        self.log.info("Stripscan: Preparing everything for frequencyscans")
        # Add the additional params to the header
        params_string = ""
        for key, value in self.sensor_pad_data.get("additional_params", {}).items():
            params_string += "# " + str(key) + ": " + str(value) + "\n"
        params_string += "\n\n"
        self.main.write(self.main.measurement_files["frequencyscan"], params_string)

        # Switch to IV for correct biasing for ramp
        if not self.switching.switch_to_measurement("IV"):
            self.stop_everything()

        # Configure the setup, complience and switch on the smu
        self.main.config_setup(self.bias_SMU, [("set_complience_current", str(self.complience))])
        self.main.change_value(self.bias_SMU, "set_output", "1")

        # Moves to strip
        self.main.table.move_to_strip(self.sensor_pad_data, int(self.job["frequencyscan"]["Strip"]) - 1,
                                      self.trans, self.T, self.V0, self.height)

        # Move the table down while ramp
        self.main.table.move_down(self.height)

        # Ramps the voltage, if ramp voltage returns false something went wrong -> stop
        if not self.main.ramp_voltage(self.bias_SMU, "set_voltage", self.voltage_Start, self.voltage_End,
                                      self.voltage_steps, wait_time=1, complience=self.complience):
            self.current_voltage = self.main.settings["settings"]["bias_voltage"]
            self.stop_everything()

        # If everything works make steady state check
        else:
            if self.main.steady_state_check(self.bias_SMU, max_slope=1e-6, wait=0, samples=3, Rsq=0.5,
                                            complience=self.complience):  # Is a dynamic waiting time for the measuremnts
                self.current_voltage = self.main.settings["settings"]["bias_voltage"]
                if self.main.check_complience(self.bias_SMU,
                                              self.complience):  # if complience is reached stop everything
                    self.stop_everything()
            else:
                self.stop_everything()

        # Move the table up again
        self.main.table.move_up(self.height)

    def do_frequencyscan(self, measurement_obj, samples, startfreq, endfreq, steps, voltage):
        '''This function performes a frequency scan of the lcr meter and at each step it executes a LIST of mesaurement'''

        self.do_setup_preparations()

        if not self.main.main.stop_measurement():
            # Generate frequency list
            freq_list = self.main.ramp_value_log10(startfreq, endfreq, steps)

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
            self.main.change_value(self.LCR_meter, "set_voltage", str(voltage))

            for freq in freq_list: #does the loop over the frequencies
                if not self.main.main.stop_measurement(): #stops the loop if shutdown is necessary
                    self.main.change_value(self.LCR_meter, "set_frequency", str(freq))
                    value = []
                    for i, meas in enumerate(measurement_obj):
                        func_name = str(meas)
                        value.append(getattr(self, "do_" + func_name)(freq, samples=samples, freqscan=True)) #calls the measurement
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