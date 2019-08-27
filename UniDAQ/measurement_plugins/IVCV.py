# This file manages the IV and CV measurement and it is intended to be used as a plugin for the QTC software

import logging
import sys
from time import sleep
import numpy as np
sys.path.append('../UniDAQ')
from ..utilities import timeit
from .forge_tools import tools



class IVCV_class(tools):

    def __init__(self, main_class):
        self.main = main_class
        super(IVCV_class, self).__init__(self.main.framework, self.main)
        self.log = logging.getLogger(__name__)
        self.switching = self.main.switching
        self.justlength = 24
        self.vcw = self.main.framework["VCW"]
        self.user_configs = self.main.settings["settings"].get("Measurement_configs",{}).get("IVCV", {}) # Loads the configs for IVCV measurements
        self.IVCV_configs = {
                # Devices Configs
                "BiasSMU": "BiasSMU",
                "LCRMeter": "Agilent E4980A",
                "DischargeSMU": "2410 Keithley SMU",
                "Switching": "temphum_controller",

                # Commands Configs
                "Discharge" : ("set_terminal", "FRONT"),
                "OutputON": ("set_output", "1"),
                "OutputOFF": ("set_output", "0"),
                "GetReadSMU": "get_read", # This read can be a single current read or current, voltage pair
                "GetReadLCR": "get_read",

                # General Configs for the measurements
                "Meas_order": "sequential", # Or: interlaced
                "BaseConfig": [],
                "IVConfig": [],
                "CVConfig": [],

            }
        # Important commands which has to be available: set_compliance_current
        #                                               set_voltage

        # Just update the new configs with the standard config
        self.IVCV_configs.update(self.user_configs)
        self.log.debug("Configs used for IVCV are: {}".format(self.IVCV_configs))

    def run(self):
        """Runs the IVCV measurement"""
        time = self.do_IVCV()
        self.main.settings["settings"]["IVCV_time"] = str(time[1])
        return None

    def stop_everything(self):
        """Stops the measurement"""
        self.log.critical("IVCV measurement called immediate stop of execution")
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)

    @timeit
    def do_IVCV(self):
        '''This function conducts IVCV measurements.'''
        job_list = []
        voltage_End = []
        voltage_Start = []
        voltage_steps = []
        self.log.info("Acquiring devices for IVCV measurements...")
        discharge_SMU = None
        bias_SMU = None
        LCR_meter = None
        discharge_switching = None
        try:
            bias_SMU = self.main.devices[self.IVCV_configs["BiasSMU"]]
            LCR_meter = self.main.devices[self.IVCV_configs["LCRMeter"]]
            discharge_SMU = self.main.devices[self.IVCV_configs["DischargeSMU"]]
            discharge_switching = self.main.devices[self.IVCV_configs["Switching"]]
        except KeyError as valErr:
            self.log.critical("One or more devices could not be found for the IVCV measurements. Error: {}".format(valErr))

        # First perform a discharge of the decouple box capacitor and stop if there is a problem
        if discharge_SMU:
            if not self.main.capacitor_discharge(discharge_SMU, discharge_switching, *self.IVCV_configs["Discharge"]):
                return # Exits the Measurement if need be
        else:
            self.log.critical("No discharge SMU specified. Therefore, no discharge of capacitors done!")

        if "IV" in self.main.job_details["IVCV"]: # Creates the actual measurement plan
            job_list.append(self.do_IV)
            voltage_End.append(self.main.job_details["IVCV"]["IV"].get("EndVolt", 0))
            voltage_Start.append(self.main.job_details["IVCV"]["IV"].get("StartVolt", 0))
            voltage_steps.append(self.main.job_details["IVCV"]["IV"].get("Steps", 0))
            #job_header += "voltage [V] \t current [A] \t"

        if "CV" in self.main.job_details["IVCV"]:
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

        voltage_step_list = self.ramp_value(voltage_Start, voltage_End, voltage_steps)
        if self.main.job_details["IVCV"].get("IVCV_refinement", False):
            voltage_step_list = self.refine_ramp(voltage_step_list,
                                                  self.main.job_details["IVCV"]["IVCV_refinement"]["Min"],
                                                  self.main.job_details["IVCV"]["IVCV_refinement"]["Max"],
                                                  self.main.job_details["IVCV"]["IVCV_refinement"]["Step"])

        # Config the setup for IV
        compliance = str(self.main.job_details["IVCV"].get("IV",self.main.job_details["IVCV"].get("CV", None))["Complience"])

        self.config_setup(bias_SMU, self.IVCV_configs["BaseConfig"])
        self.change_value(bias_SMU, "set_compliance_current", compliance)
        self.change_value(bias_SMU, *self.IVCV_configs["OutputON"])

        # So biasing is correctly applied
        if not self.switching.switch_to_measurement("IV"):
            self.stop_everything()
        #sleep(2.)

        # Seq or interlaced ----------------------------------------------
        if self.IVCV_configs["Meas_order"] == "interlaced":
            i = self.interlaced_order(voltage_step_list, bias_SMU, LCR_meter, compliance)
        elif self.IVCV_configs["Meas_order"] == "sequential":
            i = self.sequential_order(voltage_step_list, bias_SMU, LCR_meter, compliance)
        else:
            self.log.error("Measurement order: {} was recognised, either sequential or interlaced are possible".format(self.IVCV_configs["Meas_order"]))

        #if self.main.save_data: # Closes the file after completion of measurement or abortion
        #    close_file(self.main.measurement_files["IVCV"])

        self.ramp_voltage(bias_SMU, "set_voltage", str(voltage_step_list[i-1]), 0, 20, 0.01)
        self.change_value(bias_SMU, *self.IVCV_configs["OutputOFF"])
        sleep(2.)
        self.main.settings["settings"]["bias_voltage"] = 0
        if self.check_complience(bias_SMU, 100e-6):
            sleep(1.)
            if self.check_complience(bias_SMU, 100e-6):
                self.log.error("Output voltage was set to 0 and still the device is in complience. Please check the setup."
                               "This should not happen!!!")

        self.change_value(bias_SMU, *self.IVCV_configs["OutputOFF"])
        if discharge_SMU:
            self.capacitor_discharge(discharge_SMU, discharge_switching, *self.IVCV_configs["Discharge"], do_anyway=True)
        return None

    def sequential_order(self, voltage_step_list, bias_SMU, LCR_meter, compliance):
        """Routine for the sequential IVCV measurement
           The function returns the iterator, where it was with the voltage!"""
        iter = 0
        voltage = 0
        for meas, device in zip(["IV", "CV"], [bias_SMU, LCR_meter]):
            if meas in self.main.job_details["IVCV"] and not self.main.event_loop.stop_all_measurements_query():
                for i, voltage in enumerate(voltage_step_list):
                    if abs(voltage) <= abs(self.main.job_details["IVCV"][meas].get("EndVolt", 0)):
                        iter = i
                        if not self.main.event_loop.stop_all_measurements_query(): # To shut down if necessary
                            self.change_value(bias_SMU, "set_voltage", str(voltage))
                            if not self.steady_state_check(bias_SMU, self.IVCV_configs["GetReadSMU"], max_slope = 1e-6, wait = 0, samples = 5, Rsq = 0.5, complience=compliance): # Is a dynamic waiting time for the measuremnts
                                self.stop_everything()

                            if self.check_complience(bias_SMU, float(compliance)):
                                self.stop_everything() # stops the measurement if complience is reached

                            getattr(self, "do_{}".format(meas))(voltage, device, samples=3)

                        elif self.main.event_loop.stop_all_measurements_query():  # Stops the measurement if necessary
                            break

            if not self.main.event_loop.stop_all_measurements_query():
                self.ramp_voltage(bias_SMU, "set_voltage", voltage, 0, 10, 0.3, float(compliance))


        # Todo: write good readout to file
        #IV_zip = zip(self.main.measurement_data["IV"][0], self.main.measurement_data["IV"][1])
        #CV_zip = zip(self.main.measurement_data["CV"][0], self.main.measurement_data["CV"][1])
        #"".join(["{}".format(x).ljust(5) for x in a])

        return iter

    def interlaced_order(self, voltage_step_list, bias_SMU, LCR_meter, compliance):
        """Routine for the interlace IVCV measurement
        The function returns the iterator, where it was with the voltage!"""
        for i, voltage in enumerate(voltage_step_list):
            if not self.main.event_loop.stop_all_measurements_query(): # To shut down if necessary
                self.change_value(bias_SMU, "set_voltage", str(voltage))
                #self.main.settings["settings"]["bias_voltage"] = voltage
                if not self.steady_state_check(bias_SMU, self.IVCV_configs["GetReadSMU"], max_slope = 1e-6, wait = 0, samples = 5, Rsq = 0.5, complience=compliance): # Is a dynamic waiting time for the measuremnts
                    self.stop_everything()

                if self.check_complience(bias_SMU, float(compliance)):
                    self.stop_everything() # stops the measurement if complience is reached

                string_to_write = ""
                if "IV" in self.main.job_details["IVCV"] and abs(voltage) <= abs(self.main.job_details["IVCV"]["IV"].get("EndVolt", 0)):
                    self.do_IV(voltage, bias_SMU, samples = 3)
                    if self.main.save_data:
                        string_to_write += str(self.main.measurement_data["IV"][0][-1]).ljust(self.justlength) + str(self.main.measurement_data["IV"][1][-1]).ljust(self.justlength)

                if "CV" in self.main.job_details["IVCV"] and abs(voltage) <= abs(self.main.job_details["IVCV"]["CV"].get("EndVolt", 0)):
                    self.do_CV(voltage, LCR_meter, samples = 3)
                    if self.main.save_data:
                        string_to_write += str(self.main.measurement_data["CV"][0][-1]).ljust(self.justlength) + str(self.main.measurement_data["CV"][1][-1]).ljust(self.justlength)

                # environment values
                if self.main.job_details.get("enviroment", False):
                    if "CV" in self.main.job_details["IVCV"] and abs(voltage) > abs(self.main.job_details["IVCV"]["CV"].get("EndVolt", 0)):
                        string_to_write += "--".ljust(self.justlength)+"--".ljust(self.justlength) # Writes nothing if no value is aquired
                    if self.main.event_loop.temphum_plugin:
                        string_to_write += str(self.main.event_loop.temperatur_history[-1]).ljust(self.justlength) + str(self.main.event_loop.humidity_history[-1]).ljust(self.justlength)
                    else:
                        string_to_write = ""
                self.main.write(self.main.measurement_files["IVCV"], string_to_write + "\n")  # writes correctly the units into the fileself.main.IVCV_file, string_to_write)

            elif self.main.event_loop.stop_all_measurements_query(): # Stops the measurement if necessary
                break
        return i

    #@timeit
    def do_IV(self, voltage, device_dict, samples = 5):
        '''This function simply sends a request for reading a current value and process the data'''
        if not self.main.event_loop.stop_all_measurements_query():
            self.log.debug("IV measurement started...")
            if not self.switching.switch_to_measurement("IV"):
                self.stop_everything()
                return

            # Reconfig setup if need be for the IV measurement
            self.config_setup(device_dict, self.IVCV_configs["IVConfig"])

            if not self.steady_state_check(device_dict, self.IVCV_configs["GetReadSMU"], max_slope=1e-6, wait=0, samples=4,Rsq=0.5, complience=self.main.job_details["IVCV"]["IV"]["Complience"]):  # Is a dynamic waiting time for the measuremnt
                self.stop_everything()
                self.log.warning("Steady state could not be reached, shutdown of measurement")
                return
            values = []
            for i in range(samples):
                #command = self.main.build_command(device_dict, "get_read_iv") # returns 2 values!!!
                #values.append(float(str(vcw.query(device_dict, command)).split(",")[0])) 237SMU
                values.append(str(self.vcw.query(device_dict, device_dict[self.IVCV_configs["GetReadSMU"]])).split("\t")) # 2657SMU

            current = sum([float(x[0]) for x in values])/len(values) # Makes a mean out of it
            if len(values[0]) >1:
                voltage = sum([float(x[1]) for x in values]) / len(values)  # Makes a mean out of it
            else:
                voltage = voltage

            self.main.settings["settings"]["bias_voltage"] = voltage  # changes the bias voltage

            self.main.measurement_data["IV"][0] = np.append(self.main.measurement_data["IV"][0], [float(voltage)])
            self.main.measurement_data["IV"][1] = np.append(self.main.measurement_data["IV"][1],[float(current)])
            self.main.queue_to_main.put({"IV": [float(voltage), float(current)]})


    #@timeit
    def do_CV(self, voltage, device_dict, samples = 5):
        '''This function simply sends a request for reading a capacity value (or more precicely the amplitude and the phase shift) and process the data'''
        if not self.main.event_loop.stop_all_measurements_query():
            self.log.debug("CV measurement started...")
            if not self.switching.switch_to_measurement("CV"):
                self.stop_everything()
                return

            # Reconfig setup if need be for the CV measurement
            self.config_setup(device_dict, self.IVCV_configs["CVConfig"])

            if not self.steady_state_check(device_dict, self.IVCV_configs["GetReadLCR"], max_slope=1e-6, wait=0.05, samples=3, Rsq=0.5, complience=None):  # Is a dynamic waiting time for the measuremnts
                self.stop_everything()
                self.log.warning("Steady state could not be reached, shutdown of measurement")
                return
            values = []
            for i in range(samples):
                values.append(float(str(self.vcw.query(device_dict, device_dict[self.IVCV_configs["GetReadLCR"]])).split(",")[0]))
            value = sum(values) / len(values)
            self.main.measurement_data["CV"][0] = np.append(self.main.measurement_data["CV"][0], [float(voltage)])
            self.main.measurement_data["CV"][1] = np.append(self.main.measurement_data["CV"][1], [float(value)])
            self.main.queue_to_main.put({"CV": [float(voltage), float(value)]})
