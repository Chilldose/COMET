# This file manages the IV and CV measurement and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
sys.path.append('../modules')
from ..VisaConnectWizard import *
from ..utilities import *
l = logging.getLogger(__name__)

help = help_functions()
vcw = VisaConnectWizard.VisaConnectWizard()

@help.timeit
class IVCV_class:
    
    def __init__(self, main_class):
        self.main = main_class
        self.switching = self.main.switching
        self.justlength = 24
        self.do_IVCV()


    @help.timeit
    def do_IVCV(self):
        '''This function conducts IVCV measurements.'''
        job_list = []
        job_header = ""
        voltage_End = []
        voltage_Start = []
        voltage_steps = []
        bias_SMU = self.main.devices["IVSMU"]
        LCR_meter = self.main.devices["LCR"]
        discharge_SMU = self.main.devices["2410SMU"]
        discharge_switching = self.main.devices["temphum_controller"]

        # First perform a discharge of the decouple box capacitor and stop if there is a problem
        if not self.main.capacitor_discharge(discharge_SMU, discharge_switching, discharge_SMU["set_terminal"], "FRONT"):
            return

        if "IV" in self.main.job_details["IVCV"]: # Creates the actual measurement plan
            job_list.append(self.do_IV)
            voltage_End.append(self.main.job_details["IVCV"]["IV"].get("EndVolt", 0))
            voltage_Start.append(self.main.job_details["IVCV"]["IV"].get("StartVolt", 0))
            voltage_steps.append(self.main.job_details["IVCV"]["IV"].get("Steps", 0))
            #job_header += "voltage [V] \t current [A] \t"

        elif "CV" in self.main.job_details["IVCV"]:
            job_list.append(self.do_CV)
            voltage_End.append(self.main.job_details["IVCV"]["CV"].get("EndVolt", 0))
            voltage_Start.append(self.main.job_details["IVCV"]["CV"].get("StartVolt", 0))
            voltage_steps.append(self.main.job_details["IVCV"]["CV"].get("Steps", 0))
            #job_header += "voltage [V] \t capacity [F] \t"

        if self.main.save_data:
            self.main.write(self.main.measurement_files["IVCV"], self.main.job_details["IVCV"]["header"] + "\n") # writes correctly the units into the file

        voltage_End = min(voltage_End) # Just of general settings
        voltage_Start = min(voltage_Start)
        voltage_steps = min(voltage_steps)

        voltage_step_list = self.main.ramp_value(voltage_Start, voltage_End, voltage_steps)

        # Config the setup for IV
        complience = str(self.main.job_details["IVCV"].get("IV",self.main.job_details["IVCV"].get("CV", None))["Complience"])
        self.main.config_setup(bias_SMU, [(str(bias_SMU["set_complience"]), complience )])
        self.main.change_value(bias_SMU, bias_SMU["set_output"], "1")

        # So biasing is correctly applied
        switch_success = self.switching.switch_to_measurement("IV")
        if not switch_success:
            order = {"ABORT_MEASUREMENT": True}  # just for now
            self.main.queue_to_main.put(order)
        sleep(2.)

        for i, voltage in enumerate(voltage_step_list):
            if not self.main.stop_measurement(): # To shut down if necessary
                switch_success = self.switching.switch_to_measurement("IV")
                self.main.change_value(bias_SMU, bias_SMU["set_voltage"], str(voltage))
                self.main.settings["Defaults"]["bias_voltage"] = voltage  # changes the bias voltage
                if not self.main.steady_state_check(bias_SMU, max_slope = 1e-6, wait = 0, samples = 5, Rsq = 0.5, complience=complience): # Is a dynamic waiting time for the measuremnts
                    break

                if self.main.check_complience(bias_SMU, float(complience)):
                    break # stops the measurement if complience is reached

                string_to_write = ""
                if "IV" in self.main.job_details["IVCV"] and abs(voltage) <= abs(self.main.job_details["IVCV"]["IV"].get("EndVolt", 0)):
                    self.do_IV(voltage, bias_SMU, samples = 3)
                    if self.main.save_data:
                        string_to_write += str(self.main.measurement_data["IV"][0][-1]).ljust(self.justlength) + str(self.main.measurement_data["IV"][1][-1]).ljust(self.justlength)

                if "CV" in self.main.job_details["IVCV"] and abs(voltage) <= abs(self.main.job_details["IVCV"]["CV"].get("EndVolt", 0)):
                    self.do_CV(voltage, LCR_meter, samples = 3)
                    if self.main.save_data:
                        string_to_write += str(self.main.measurement_data["CV"][0][-1]).ljust(self.justlength) + str(self.main.measurement_data["CV"][1][-1]).ljust(self.justlength)

                # enviroment values
                if self.main.job_details.get("enviroment", False):
                    if "CV" in self.main.job_details["IVCV"] and abs(voltage) > abs(self.main.job_details["IVCV"]["CV"].get("EndVolt", 0)):
                        string_to_write += "--".ljust(self.justlength)+"--".ljust(self.justlength) # Writes nothing if no value is aquired
                    string_to_write += str(self.main.main.temperatur_history[-1]).ljust(self.justlength) + str(self.main.main.humidity_history[-1]).ljust(self.justlength)

                self.main.write(self.main.measurement_files["IVCV"], string_to_write + "\n")  # writes correctly the units into the fileself.main.IVCV_file, string_to_write)

            elif self.main.stop_measurement(): # Stops the measurement if necessary
                break

        if self.main.save_data: # Closes the file after completion of measurement or abortion
            help.close_file(self.main.IVCV_file)

        self.main.ramp_voltage(bias_SMU, bias_SMU["set_voltage"], str(voltage_step_list[i-1]), 0, 20, 0.01)
        self.main.change_value(bias_SMU, bias_SMU["set_voltage"], "0")
        self.main.change_value(bias_SMU, bias_SMU["set_output"], "0")
        self.main.capacitor_discharge(discharge_SMU, discharge_switching, discharge_SMU["set_terminal"], "FRONT", do_anyway=True)

    #@help.timeit
    def do_IV(self, voltage, device_dict, samples = 5):
        '''This function simply sends a request for reading a current value and process the data'''
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("IV"):
                order = {"ABORT_MEASUREMENT": True}  # just for now
                self.main.queue_to_main.put(order)
                return
            if not self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=4,Rsq=0.5, complience=self.main.job_details["IVCV"]["IV"]["Complience"]):  # Is a dynamic waiting time for the measuremnt
                return
            values = []
            for i in range(samples):
                values.append(float(str(vcw.query(device_dict, device_dict["Read"], device_dict.get("execution_terminator", ""))).split(",")[0]))
            value = sum(values)/len(values)
            #print values
            self.main.measurement_data["IV"][0] = np.append(self.main.measurement_data["IV"][0], [float(voltage)])
            self.main.measurement_data["IV"][1] = np.append(self.main.measurement_data["IV"][1],[float(value)])
            self.main.queue_to_main.put({"IV": [float(voltage), float(value)]})


    #@help.timeit
    def do_CV(self, voltage, device_dict, samples = 5):
        '''This function simply sends a request for reading a capacity value (or more precicely the amplitude and the phase shift) and process the data'''
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("CV"):
                order = {"ABORT_MEASUREMENT": True}  # just for now
                self.main.queue_to_main.put(order)
                return
            if not self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0.05, samples=3, Rsq=0.5, complience=None):  # Is a dynamic waiting time for the measuremnts
                return
            values = []
            for i in range(samples):
                values.append(float(str(vcw.query(device_dict, device_dict["Read"],device_dict.get("execution_terminator", ""))).split(",")[0]))
            value = sum(values) / len(values)
            self.main.measurement_data["CV"][0] = np.append(self.main.measurement_data["CV"][0], [float(voltage)])
            self.main.measurement_data["CV"][1] = np.append(self.main.measurement_data["CV"][1], [float(value)])
            self.main.queue_to_main.put({"CV": [float(voltage), float(value)]})
