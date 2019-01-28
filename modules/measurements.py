# Here the measurement procedures are defined
import logging
import numpy as np
from VisaConnectWizard import *
import os
import time
import datetime, math
from scipy import stats
import importlib
from utilities import *

l = logging.getLogger(__name__)

help = help_functions()
vcw = VisaConnectWizard.VisaConnectWizard()



class measurement_class:
    def __init__(self, meas_loop, main_defaults, pad_data, devices, queue_to_main, queue_to_event_loop, job_details, queue_to_GUI, table, switching, stop_measurement):
        self.queue_to_main = queue_to_main
        self.main = meas_loop
        self.stop_measurement = stop_measurement # this is a function and need to be called via brackets to work correctly!!!
        self.queue_to_event_loop = queue_to_event_loop
        self.queue_to_GUI = queue_to_GUI
        self.setup_not_ready = True
        self.job_details = job_details
        self.IVCV_job = []
        self.strip_scan_job = []
        self.measured_data = {}
        self.settings = main_defaults
        self.pad_data = pad_data
        self.table = table
        self.switching = switching
        self.devices = devices
        self.IVCV_file = ""
        self.strip_file = ""
        self.IV_longterm_file = ""
        self.list_strip_measurements = ["Rint", "Istrip", "Idiel", "Rpoly", "Cac", "Istrip_overhang", "Cint", "Idark", "Cback"]
        self.IV_data = np.array([])
        self.CV_data = np.array([])
        self.IV_longterm_data = np.array([])
        self.time_const = 1 # sec
        self.current_sensor = self.settings["Defaults"]["Current_sensor"]
        self.all_plugins = {}
        self.total_strips = None
        self.measurement_files = {}
        self.measurement_data = {}
        self.write = None
        self.save_data = False
        self.env_waiting_time = 60*5 # Five minutes
        self.build_command = help.build_command # think of it like a link
        self.badstrip_dict = {}
        self.skip_tests = True # This must always be False!!! only for debugging !!!

        # Make preps
        self.settings["Defaults"]["Start_time"] = str(datetime.datetime.now())
        self.load_plugins()
        self.find_stripnumber()
        self.estimate_duration(datetime.datetime.now())
        self.write_data()

        # Build all data arrays
        for data_files in self.settings["Defaults"]["measurement_types"]:
            self.measurement_data.update({data_files: [[np.zeros(0)], [np.zeros(0)]]})

        #self.make_measurement_plan()

        # Perfom the setup check and start the measurement
        # -------------------------------------------------------------------------------
        if not self.check_setup(): # Checks if measuremnts can be conducted or not if True: an critical error occured
            # Start the light that the measurement is running
            self.external_light(self.devices["lights_controller"], True)
            self.make_measurement_plan()
            sleep(0.1)
            self.external_light(self.devices["lights_controller"], False)
            self.close_measurement_files()

        elif self.skip_tests: # This is just for debugging and can lead to unwanted behavior
            self.make_measurement_plan()
            self.close_measurement_files()



        else:
            l.info("Measurement was not conducted, due to failure in setup check!")
        # Perfom the setup check and start the measurement
        # -------------------------------------------------------------------------------

        self.queue_to_event_loop.put({"Status":{"MEASUREMENT_FINISHED": True}}) # States that the measurement is finished

    def close_measurement_files(self):
        """
        This function closes all measurement files which have been opend during a measurement run
        """
        for file in self.measurement_files.values():
            os.close(file)

    def external_light(self, device_dict, bool):
        '''Turns the light on when measurements are running'''
        if bool:
            self.change_value(device_dict, "set_external_light", "ON")
            self.settings["Defaults"]["external_lights"] = True
        else:
            self.change_value(device_dict, "set_external_light", "OFF")
            self.settings["Defaults"]["external_lights"] = False

    def write_data(self):
        # Save data
        # -----------------------------------------------------------------------------
        if "Save_data" in self.job_details:
            self.save_data = self.job_details["Save_data"]
            self.write = help.flush_to_file
        else:
            self.save_data = False
        # Save data
        # -----------------------------------------------------------------------------


    def estimate_duration(self, start_time):
        """Estimate time
        Will not be correct, since CV usually is faster, but it is just a estimation.
        -----------------------------------------------------------------------------
        Start and end timer. all of this quick and dirty but it will suffice"""
        # self.settings["Defaults"]["Start_time"] = datetime.datetime.now()
        est_end = 0
        for measurements in self.list_strip_measurements:
            # Loop over all strip measurements
            if measurements in self.job_details.get("stripscan", {}):
                est_end += float(self.total_strips)*float(self.settings["Defaults"]["strip_scan_time"])
                break # breaks out of loop if one measurement was found


        if "IV" in self.job_details.get("IVCV", {}):
            est_end += float(self.settings["Defaults"]["IVCV_time"])
        if "CV" in self.job_details.get("IVCV", {}):
            est_end += float(self.settings["Defaults"]["IVCV_time"])

        est_end = start_time + datetime.timedelta(seconds=est_end)
        self.settings["Defaults"]["End_time"] = str(est_end)
        # Estimate time
        # Will not be correct, since CV usually is faster, but it is just a estimation.
        # -----------------------------------------------------------------------------


    def find_stripnumber(self):
        # Try find the strip number of the sensor.
        try:
            self.total_strips = len(self.pad_data[self.settings["Defaults"]["Current_project"]][str(self.current_sensor)]["data"])
        except:
            l.error("Sensor " + str(self.current_sensor) + " not recognized. Can be due to missing pad file.")
            self.main.stop_measurement = True
            self.queue_to_main.put({"DataError": "Sensor " + str(self.current_sensor) + " not recognized. Can be due to missing pad file."})
            if "strip" in self.job_details:
                self.queue_to_main.put({"DataError": "Fatal error Sensor " + str(self.current_sensor) + " not recognized. Strip scan cannot be conducted. Check Pad files"})
                self.queue_to_event_loop.put({"Status": {"MEASUREMENT_FINISHED": True}})  # States that the measurement is finished, or aborted due to an error


    def load_plugins(self):
        # Load all measurement functions
        #install_directory = os.getcwd() # Obtain the install path of this module
        all_measurement_functions = os.listdir("./modules/measurement_plugins/")
        all_measurement_functions = list(set([modules.split(".")[0] for modules in all_measurement_functions]))

        l.info("All measurement functions found: " + str(all_measurement_functions) + ".")

        for modules in all_measurement_functions:  # import all modules from all files in the plugins folder
            self.all_plugins.update({modules: importlib.import_module("modules.measurement_plugins." + modules)})

    def create_data_file(self, header, filepath, filename="default"):
        file = help.create_new_file(filename, filepath) # Creates the file at the destination
        help.flush_to_file(file, header) # Writes the header to the file
        return file # Finally returns the file object

    def check_setup(self):
        '''This function checks if all requirements are met for successful measurement'''
        abort = False # Variable to quantify if abort program or not
        # Check if all devices have a visa resource assigned otherwise
        for device in self.devices.values():
            if "Visa_Resource" not in device:
                self.queue_to_main.put({"MEASUREMENT_FAILED": "Visa resources missing in device " + str(device["Display_name"])})
                l.critical(device["Display_name"] + " has no Visa Resource assigned! Measurement cannot be conducted.")
                return True

        # Check if lights and environement is valid
        if self.settings["Defaults"]["internal_lights"]:
            # Wait a few seconds for the controller to send the data if the box was open previously
            counter = 0
            lights_ON = True
            self.queue_to_main.put({"Info":"There seems to be light in the Box."})
            l.info("Box seems to be open or the lights are still On in the Box")
            while lights_ON:
                sleep(5)
                if self.settings["Defaults"]["internal_lights"]:
                    counter += 1
                else: lights_ON = False

                if counter >= 3:
                    l.critical("Box seems to be open or the lights are still On in the Box, aborting program")
                    self.queue_to_main.put({"MeasError":"Box seems to be open or the lights are still On in the Box, aborting program"})
                    return True

        if self.settings["Defaults"]["humidity_control"]:
            min = self.settings["Defaults"]["current_hummin"]
            max = self.settings["Defaults"]["current_hummax"]

            if (self.main.humidity_history[-1] < min or self.main.humidity_history[-1] > max): # If something is wrong
                self.queue_to_main.put({"Info":"The humidity levels not reached. Wait until state is reached. Waiting time: " + str(self.env_waiting_time)})
                wait_for_env = True
                start_time = time.time()
                while wait_for_env:
                    if not self.main.stop_measurement:
                        sleep(3)
                        if (self.main.humidity_history[-1] > min and self.main.humidity_history[-1] < max):
                            self.queue_to_main.put({"Info": "Humidity levels reached, proceeding with measurement..." })
                            wait_for_env = False
                        else:
                            diff = abs(start_time - time.time())
                            if diff > self.env_waiting_time:
                                self.queue_to_main.put({"FatalError":"The humidity levels could not be reached. Aborting program"})
                                return True
                    else:
                        return True

        return abort


    def make_measurement_plan(self):
        '''This function recieves the orders from the main and creates a measurement plan.'''

        # Check if order of measurement is in place

        if "measurement_order" in self.settings["Defaults"]:
            for measurement in self.settings["Defaults"]["measurement_order"]:
                abort = False
                if self.main.stop_measurement:
                    break
                if measurement in self.job_details and measurement in self.all_plugins:
                    if self.save_data:  # First create files, if necessary.
                        filepath = self.job_details["Filepath"]
                        filename = str(measurement)[:3] + "_" + self.job_details["Filename"]
                        if "Header" in self.job_details:
                            self.measurement_files.update({measurement: self.create_data_file(self.job_details["Header"] + "\n", filepath, filename)})  # If a header is present create file with header

                elif measurement not in self.all_plugins and measurement in self.job_details:
                    l.error("Measurement " + str(measurement) + " was not found as a defined measurement module.")
                    self.queue_to_main.put({"MEASUREMENT_FAILED": "Measurement " + str(measurement) + " was not found as a defined measurement module."})
                    abort = True
                else:
                    abort = True

                # here the actuall measurement starts
                if not abort:
                    print "Starting measurement " + str(measurement)
                    l.info("Starting measurement " + str(measurement))
                    starttime = time.time()
                    getattr(self.all_plugins[measurement], str(measurement)+"_class")(self)
                    endtime = time.time()

                    deltaT = abs(starttime-endtime)
                    print "The " + str(measurement) + " took " + str(round(deltaT,0)) + " seconds."
                    l.info("The " + str(measurement) + " took " + str(round(deltaT,0)) + " seconds.")

        if "ramp_voltage" in self.job_details:
            params = self.job_details["ramp_voltage"]
            self.ramp_voltage(params["Resource"], params["Order"], params["StartVolt"], params["EndVolt"], params["Steps"], params["Wait"], params["Complience"])

        if self.settings["Defaults"]["Test_mode"]:
            getattr(self.all_plugins["test_mode"],"test_mode_class")(self)

    def steady_state_check(self, device, max_slope = 0.001, wait = 0.2, samples = 4, Rsq = 0.95, complience = 50e-6, do_anyway = False, check_complience=True): # Not yet implemented
        '''This functions waits dynamically until the sensor has reached an equilibrium after changing the bias voltage'''
        steady_state = False
        stop = False

        if self.main.stop_measurement:
            stop = True

        if do_anyway:
            stop = False

        counter = 0
        while not steady_state and not stop and check_complience:

            if counter > 5:
                # If too many attempts where made
                l.warning("Attempt to reach steady state was not successfull after 5 times")
                self.queue_to_main.put({"Warning": "Attempt to reach steady state was not successfull after 5 times"})
                return False

            counter += 1

            values = []
            if complience:
                if self.check_complience(device, float(complience)):
                    self.stop_measurement()
                    return False

            for i in range(samples):
                command = self.build_command(device, "Read")
                values.append(float(str(vcw.query(device, command)).split(",")[0]))
                sleep(wait)

            slope, intercept, r_value, p_value, std_err = stats.linregress([i for i in range(len(values))], values)

            if std_err <= 1e-6:
                if abs(slope) <= abs(max_slope):
                    steady_state = True
                    return True

    def ramp_value_log10(self, min_value, max_value, deltasteps):
        '''This function takes a min and max value, deltasteps and generates a list of values in log10 format with each deltasteps values per decade'''
        #Todo: from max to min is not working yet
        if max_value > min_value:
            positive = True
        else:
            positive = False

        # Make it linear
        min = np.log10([abs(min_value)])[0]
        max = np.log10([abs(max_value)])[0]

        # Find absolute delta
        abs_delta = abs(min - max)
        delta_steps = round(abs(abs_delta / deltasteps), 5)
        ramp_list = [min + delta_steps * step for step in range(int(deltasteps))]
        to_big = True
        while to_big and len(ramp_list) > 1:
            if ramp_list[-1] >= max_value:
                ramp_list = ramp_list[:-1]
            else:
                to_big = False

        if positive:
            ramp_list.append(max)
        else:
            ramp_list.append(min)

        # Now make a log skale out of it
        ramp_list = map(lambda x: round(10**x,0), ramp_list)

        #if not positive: # Reverses the ramp list
        #    ramp_list = [x for x in reversed(ramp_list)]

        return ramp_list


    def ramp_value(self, min_value, max_value, deltaI):
        '''This function accepts single values and returns a list of values, which are interpreted as a ramp function
        Furthermore min and max are corresponding to the absolute value of the number!!!'''

        #Find out if positive or negative ramp
        if max_value > min_value:
            positive = True
        else:
            positive = False

        # Find absolute delta
        abs_delta = abs(min_value-max_value)
        delta_steps = round(abs(abs_delta/deltaI),0)

        if positive:
            ramp_list = [min_value + deltaI * step for step in range(int(delta_steps))]

            to_big = True
            while to_big and len(ramp_list)>1:
                if ramp_list[-1] > max_value:
                    ramp_list = ramp_list[:-1]
                else:
                    to_big = False

        else:
            ramp_list = [min_value - deltaI * step for step in range(int(delta_steps))]

            to_big = True
            while to_big and len(ramp_list)>1:
                if ramp_list[-1] < max_value:
                    ramp_list = ramp_list[:-1]
                else:
                    to_big = False

        if len(ramp_list) > 1:
            if ramp_list[-1] != max_value:
                ramp_list.append(max_value)
        else:
            ramp_list.append(max_value)

        return ramp_list

    def ramp_voltage(self, resource, order, voltage_Start, voltage_End, step, wait_time = 0.05, complience=100e-6):
        '''This functions ramps the voltage of a device'''
        voltage_End = float(voltage_End)
        voltage_Start = float(voltage_Start)
        step = float(step)
        wait_time = float(wait_time)

        voltage_step_list = self.ramp_value(voltage_Start, voltage_End, step)

        # Check if current bias voltage is inside this ramp and delete if necessary
        bias_voltage = float(self.settings["Defaults"]["bias_voltage"])

        for i, voltage in enumerate(voltage_step_list):
            if abs(voltage) > abs(bias_voltage):
                voltage_step_list = voltage_step_list[i:]
                break

        for voltage in voltage_step_list:
            self.change_value(resource, order, voltage)
            if self.check_complience(resource, complience):
                return False
            #self.settings["Defaults"]["bias_voltage"] = float(voltage)  # changes the bias voltage
            sleep(wait_time)

        return True

    def change_value_query(self, device_dict, order, value="", answer="1"):
        """This function query a command to a device and waits for a return value and compares
        it with the answer statement, if they are the same a true is returend"""
        if type(order) == list:
            for com in order:
                command = self.build_command(device_dict, (com, value))
                answ = vcw.query(device_dict["Visa_Resource"], command) # writes the new order to the device
        else:
            command = self.build_command(device_dict, (order, value))
            answ = vcw.query(device_dict["Visa_Resource"], command)  # writes the new order to the device

        answ = str(answ).strip()
        if answ == answer:
            return None
        else:
            return answ # For errorhandling it is the return from the device which was not the expected answer

    def send_to_device(self, device_dict, command):
        """
        This command just sends the command to the device. Warning it is not recommended to use this function. Use this
        function only if you must!

        :param device_dict: Dictionary of the device
        :param command: The command you want to send to the device
        :return: None
        """

        try:
            vcw.write(device_dict["Visa_Resource"], str(command))  # writes the new order to the device
        except Exception as e:
            l.error("Could not send {command!s} to device {device!s}, error {error!s} occured".format(command=command, device=device_dict, error=e))

    def query_device(self, device_dict, command):
        """
        This command just sends the command to the device, and waits for an answer. Warning it is not recommended to use this function. Use this
        function only if you must!

        :param device_dict: Dictionary of the device
        :param command: The command you want to send to the device
        :return: Return string from the device
        """

        try:
            return vcw.query(device_dict["Visa_Resource"], str(command))  # writes the new order to the device
        except Exception as e:
            l.error("Could not send {command!s} to device {device!s}, error {error!s} occured".format(command=command,
                                                                                                      device=device_dict,
                                                                                                      error=e))

    def change_value(self, device_dict, order, value=""):
        '''This function sends a command to a device and changes the state in the dictionary (state machine)'''
        if type(order) == list:
            for com in order:
                command = self.build_command(device_dict, (com, value))
                vcw.write(device_dict["Visa_Resource"], command) # writes the new order to the device
        else:
            command = self.build_command(device_dict, (order, value))
            vcw.write(device_dict["Visa_Resource"], command)  # writes the new order to the device

    def check_complience(self, device, complience = None):
        '''This function checks if the current complience is reached'''
        try:
            if complience == None:
                l.error("No complience set for measurement, default complience is used! This may cause deamage to the sensor!")
                print "No complience set for measurement, default complience is used! This may cause deamage to the sensor!"
                complience = device["default_complience"]
        except:
            l.error("Device " + str(device) + " has no complience set!")

        command = self.build_command(device,"Read_iv")
        #value = float(str(vcw.query(device, command)).split(",")[0]) #237SMU
        value = str(vcw.query(device, command)).split("\t")
        self.settings["Defaults"]["bias_voltage"] = str(value[1]).strip()  # changes the bias voltage
        if 0. < (abs(float(value[0])) - abs(float(complience)*0.99)):
            l.error("Complience reached in instrument " + str(device["Display_name"]) + " at: "+ str(value[0]) + ". Complience at " + str(complience))
            self.queue_to_main.put({"MeasError": "Compliance reached. Value. " + str(value[0]) + " A"})
            return True
        else:
            return False

    @help.timeit
    def config_setup(self, device, commands = []):
        '''This function configures the setup for a specific measurement.
        Commands is a list of tuples, containing (command, values) if no value is defined only command will be send'''

        for command in commands:
            final_string = self.build_command(device, command)
            vcw.write(device["Visa_Resource"], str(final_string))  # finally writes the command to the device




    def build_command_depricated(self, device, command_tuple):
        print "You used an on build command, please use the one from utilities"
        #Todo build command is two folded in here
        if type(command_tuple) == unicode or type(command_tuple) == str:
            command_tuple = (str(command_tuple),) # so the correct casting is done

        for key, value in device.items():
            try:
                if command_tuple[0] == value: # finds the correct value
                    command_keyword = str(key.split("_")[-1])

                    if ("CSV_command_" + command_keyword) in device: # searches for CSV command in dict
                        data_struct = device["CSV_command_" + command_keyword].split(",")

                        final_string = str(command_tuple[0]) + " "  # so the key word

                        for i, given_orders in enumerate(command_tuple[1:]): # so if more values are given, these will be processed first
                            final_string += str(given_orders).upper() + ","  # so the value

                        if len(command_tuple[1:]) <= len(data_struct): # searches if additional data needs to be added
                            for data in data_struct[i+1:]:
                                # print device[command_keyword + "_" + data]
                                if command_keyword + "_" + data in device:
                                    final_string += str(device[command_keyword + "_" + data]).upper() + ","
                                else:
                                    final_string += ","# if no such value is in the dict

                        return final_string[:-1] # because there is a colon to much in it

                    else:
                        if len(command_tuple) > 1:
                            return str(command_tuple[0]) + " " + str(command_tuple[1])
                        else:
                            return str(command_tuple[0])

            except Exception, e:
                pass





    def capacitor_discharge(self, device_dict, relay_dict, termorder = None, terminal = None, do_anyway=False):
        '''This function checks if the capacitor of the decouple box is correctly discharged
        First is input is the device which measure something and relay_dict is the relay which need to be switched'''

        # First switch the smu terminals front/rear
        if termorder:
            self.change_value(device_dict, termorder, terminal)

        # Set the switching for the discharge (a relay must be switched in the decouple box by applying 5V
        #sleep(1.) # Slow switching shit on BB
        error = self.change_value_query(relay_dict, "set_discharge", "ON", "DONE")
        if error:
            self.queue_to_main.put({"RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " +  str("DONE") + " got " + str(error) + " instead."})
            l.error("Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " +  str("DONE") + " got " + str(error) + " instead.")
            return False
        sleep(1.) # relay is really slow

        # Next discharge the capacitor by running a current measurement
        #self.change_value(device_dict, device_dict["set_measure_current"])

        # Set output to On for reading mode
        #self.change_value(device_dict, device_dict["set_output"], "ON")

        #if self.steady_state_check(device_dict, samples = 7, do_anyway = do_anyway):
            #self.change_value(device_dict, device_dict["set_output"], "OFF")
        self.change_value(device_dict, "set_source_current")
        self.change_value(device_dict, "set_measure_voltage")
        self.change_value(device_dict, "set_output", "ON")
        counter = 0

        while True:
            counter += 1
            voltage = []
            for i in range(3):
                command = self.build_command(device_dict, "Read")
                voltage.append(float(vcw.query(device_dict["Visa_Resource"], command)))

            if sum(voltage)/len(voltage) <= 0.3: # this is when we break the loop
                self.change_value(device_dict, "set_output", "OFF")
                self.change_value(device_dict, "set_source_voltage")
                self.change_value(device_dict, "set_measure_current")

                self.change_value(device_dict, termorder, "REAR")
                # return to default mode for this switching
                sleep(1.)  # Slow switching shit on BB
                error = self.change_value_query(relay_dict, "set_discharge", "OFF", "DONE")
                if error:
                    self.queue_to_main.put({
                                               "RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                                                   "DONE") + " got " + str(error) + " instead."})
                    l.error(
                        "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                            "DONE") + " got " + str(error) + " instead.")

                    return False
                sleep(1.)  # relay is really slow
                return True
            else:
                self.queue_to_main.put({"Info": "Capacitor discharged failed: " + str(counter) + " times, with a voltage of " + str(sum(voltage)/len(voltage))})

            if counter >= 5:
                self.queue_to_main.put({"FatalError": "The capacitor discharge failed more than 5 times. Discharge the capacitor manually!"})
                # Set output to on for reading mode
                command = self.build_command(device_dict, ("set_output", "OFF"))  # switch back to default terminal
                vcw.write(device_dict["Visa_Resource"], command)  # writes the new order to the device
                # return to default mode for this switching
                error = self.change_value_query(relay_dict, "set_discharge", "OFF", "DONE")
                if error:
                    self.queue_to_main.put({"RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                                            "DONE") + " got " + str(error) + " instead."})
                    l.error(
                        "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                            "DONE") + " got " + str(error) + " instead.")

                return False


    def stop_measurement(self):
        """Stops the measurement"""
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)


if __name__ == "__main__":

    pass