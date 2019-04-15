# Here the measurement procedures are defined
import logging
import numpy as np
#from .VisaConnectWizard import VisaConnectWizard
import os
from time import sleep, time
import datetime
from scipy import stats
import importlib
from threading import Thread

from .utilities import timeit, build_command, flush_to_file, create_new_file

class measurement_class(Thread):
    #meas_loop, main_defaults, pad_data, devices, queue_to_main, queue_to_event_loop, job_details, queue_to_GUI, table, switching, stop_measurement)

    def __init__(self, event_loop, framework, job_details):

        Thread.__init__(self)
        self.log = logging.getLogger(__name__)
        self.framework = framework
        self.log.info("Initializing measurement thread...")
        self.queue_to_main = framework["Message_to_main"]
        self.main = event_loop
        self.stop_measurement = self.main.stop_measurement # this is a function and need to be called via brackets to work correctly!!!
        self.queue_to_event_loop = framework["Message_from_main"]
        self.queue_to_GUI = framework["Queue_to_GUI"]
        self.setup_not_ready = True
        self.job_details = job_details
        self.vcw = framework["VCW"]
        #self.IVCV_job = []
        #self.strip_scan_job = []
        self.measured_data = {}
        self.settings = framework["Configs"]["config"]
        #self.pad_data = framework["Configs"]pad_data
        self.table = framework["Table"]
        self.switching = framework["Switching"]
        self.devices = framework["Devices"]
        #self.IVCV_file = ""
        #self.strip_file = ""
        #self.IV_longterm_file = ""
        #self.list_strip_measurements = ["Rint", "Istrip", "Idiel", "Rpoly", "Cac", "Istrip_overhang", "Cint", "Idark", "Cback"]
        #self.IV_data = np.array([])
        #self.CV_data = np.array([])
        #self.IV_longterm_data = np.array([])
        self.time_const = 1 # sec
        #self.current_sensor = self.settings["settings"]["Current_sensor"]
        self.all_plugins = {}
        #self.total_strips = None
        self.measurement_files = {}
        self.measurement_data = {}
        self.write = None
        self.save_data = False
        self.env_waiting_time = 60*5 # Five minutes
        self.build_command = build_command
        #self.badstrip_dict = {}
        self.skip_tests = False # This must always be False!!! only for debugging !!!


        # Build all data arrays
        for data_files in self.settings["settings"]["measurement_types"]:
            self.measurement_data.update({data_files: [[np.zeros(0)], [np.zeros(0)]]})


    def run(self):
        self.log.info("Starting measurement thread...")
        self.settings["settings"]["Start_time"] = str(datetime.datetime.now())
        self.load_plugins()
        #self.find_stripnumber()
        #self.estimate_duration(datetime.datetime.now())
        self.write_data()

        # Perform the setup check and start the measurement
        # -------------------------------------------------------------------------------
        if self.setup_ready(): # Checks if measurements can be conducted or not if True: an critical error occured
            # Start the light that the measurement is running
            if "lights_controller" in self.devices:
                self.external_light(self.devices["lights_controller"], True)
            else:
                self.log.info("No external lights controller found")
            #-----------------------------------------------------------------------------------------------------------
            self.make_measurement_plan()
            #-----------------------------------------------------------------------------------------------------------
            sleep(0.1)
            if "lights_controller" in self.devices:
                self.external_light(self.devices["lights_controller"], False)
            else:
                self.log.info("No external lights controller found")
            self.close_measurement_files()

        elif self.skip_tests: # This is just for debugging and can lead to unwanted behavior
            self.make_measurement_plan()
            self.close_measurement_files()

        else:
            self.log.error("Measurement could not be conducted. Setup failed the readiness check. "
                           "Please check the logs for more information what happened")
        # Perfom the setup check and start the measurement
        # -------------------------------------------------------------------------------
        self.queue_to_event_loop.put({"Status":{"MEASUREMENT_FINISHED": True}}) # States that the measurement is finished

    def close_measurement_files(self):
        """
        This function closes all measurement files which have been opened during a measurement run
        """
        for file in self.measurement_files.values():
            os.close(file)
            self.log.info("Closed measurement file: {!s}".format(file))

    def external_light(self, device_dict, bool):
        '''Turns the light on when measurements are running'''
        if bool:
            self.log.debug("Switched on external lights...")
            self.change_value(device_dict, "set_external_light", "ON")
            self.settings["settings"]["external_lights"] = True
        else:
            self.log.debug("Switched off external lights...")
            self.change_value(device_dict, "set_external_light", "OFF")
            self.settings["settings"]["external_lights"] = False

    def write_data(self):
        # Save data
        # -----------------------------------------------------------------------------
        if "Save_data" in self.job_details:
            self.save_data = self.job_details["Save_data"]
            self.write = flush_to_file
        else:
            self.save_data = False
        # Save data
        # -----------------------------------------------------------------------------

    def load_plugins(self):
        # Load all measurement functions
        to_ignore = ["__init__", "__pycache__"]
        all_measurement_functions = os.listdir(os.path.join(self.framework["rootdir"], "measurement_plugins"))
        all_measurement_functions = list(set([modules.split(".")[0] for modules in all_measurement_functions]))

        self.log.info("All measurement functions found: " + str(all_measurement_functions) + ".")

        # import all modules specified in the measurement order, so not all are loaded
        for modules in self.settings["settings"]["measurement_order"]:
            if modules in all_measurement_functions:
                self.all_plugins.update({modules: importlib.import_module("UniDAQ.measurement_plugins." + modules)})
                self.log.info("Imported module: {}".format(modules))
            else:
                if modules not in to_ignore:
                    self.log.error("Could not load module: {}. It was specified in the settings but"
                               " no module matches this name.".format(modules))

    def create_data_file(self, header, filepath, filename="default"):
        self.log.info("Creating new data file with name: {!s}".format(filename))
        file = create_new_file(filename, filepath) # Creates the file at the destination
        flush_to_file(file, header) # Writes the header to the file
        return file # Finally returns the file object

    def setup_ready(self):
        '''This function checks if all requirements are met for successful measurement'''
        self.log.debug("Conducting setup check...")
        # Check if all devices have a visa resource assigned otherwise return false
        for device in self.devices.values():
            if "Visa_Resource" not in device:
                self.log.error(device["Device_name"] + " has no Visa Resource assigned! Measurement cannot be conducted.")
                return False

        # Check if lights and environment is valid
        if "internal_lights" in  self.settings["settings"]:
            if self.settings["settings"]["internal_lights"]:
                # Wait a few seconds for the controller to send the data if the box was open previously
                counter = 0
                lights_ON = True
                self.queue_to_main.put({"Info":"There seems to be light in the Box."})
                self.log.info("The box seems to be open or the lights are still on in the Box")
                while lights_ON:
                    sleep(5)
                    if self.settings["settings"]["internal_lights"]:
                        counter += 1
                    else: lights_ON = False

                    if counter >= 3:
                        self.log.error("Box seems to be open or the lights are still on in the Box, aborting program")
                        return False
        else:
            self.log.warning("Variable missing for internal lights settings. No lights check!")

        if "humidity_control" in self.settings["settings"]:
            if self.settings["settings"]["humidity_control"]:
                min = self.settings["settings"]["current_hummin"]
                max = self.settings["settings"]["current_hummax"]

                if (self.main.humidity_history[-1] < min or self.main.humidity_history[-1] > max): # If something is wrong
                    self.queue_to_main.put({"Info":"The humidity levels not reached. Wait until state is reached. Waiting time: " + str(self.env_waiting_time)})
                    wait_for_env = True
                    start_time = time()
                    while wait_for_env:
                        if not self.main.stop_measurement:
                            sleep(1)
                            if (self.main.humidity_history[-1] > min and self.main.humidity_history[-1] < max):
                                self.queue_to_main.put({"Info": "Humidity levels reached, proceeding with measurement..." })
                                wait_for_env = False
                            else:
                                diff = abs(start_time - time())
                                if diff > self.env_waiting_time:
                                    self.queue_to_main.put({"FatalError":"The humidity levels could not be reached. Aborting program"})
                                    return False
                        else:
                            return False
            else:
                self.log.warning("Variable missing for humidity_control settings. No humidity check made!")
        return True # If everything worked

    def make_measurement_plan(self):
        '''This function recieves the orders from the main and creates a measurement plan.'''

        # Check if order of measurement is in place
        self.log.debug("Generating measurement plan...")
        if "measurement_order" in self.settings["settings"]:
            for measurement in self.settings["settings"]["measurement_order"]:
                abort = False
                if self.main.stop_measurement: # Check if some abort signal was send
                    return
                if measurement in self.job_details and measurement in self.all_plugins:
                    if self.save_data:  # First create files, if necessary.
                        filepath = self.job_details.get("Filepath", None)
                        filename = str(measurement)[:3] + "_" + self.job_details.get("Filename", "None")
                        if "Header" in self.job_details and filepath:
                            self.measurement_files.update({measurement:
                                                               self.create_data_file(self.job_details["Header"] + "\n",
                                                                                     filepath, filename)})
                        else:
                            self.log.error("While trying to create a measurement file for measurement {} "
                                           "an error happened. This usually happens if either/both a filepath and "
                                           "a header are missing for the measurement".format(str(measurement)))
                elif measurement not in self.all_plugins and measurement in self.job_details:
                    self.log.error("Measurement " + str(measurement) + " was not found as a defined measurement module."
                                                                       "This should never happen, only possible if you "
                                                                       "temper with the plugins dict")
                    abort = True
                else:
                    abort = True

                # Here the actual measurement starts -------------------------------------------------------------------
                if not abort:
                    self.log.info("Trying to start measurement " + str(measurement))
                    starttime = time()
                    try:
                        meas_object = getattr(self.all_plugins[measurement], str(measurement)+"_class")(self)
                        meas_object_return = meas_object.run()
                        if meas_object_return:
                            self.log.critical("The measurement {} returned: {}".format(measurement, meas_object_return) )
                        endtime = time()
                        deltaT = abs(starttime-endtime)
                        self.log.info("The " + str(measurement) + " took " + str(round(deltaT,0)) + " seconds.")
                    except Exception as err:
                        self.log.error("An error happend while conducting"
                                       " the measurement: {} with error: {}".format(measurement, err))
                # Here the actual measurement starts -------------------------------------------------------------------

    def steady_state_check(self, device, command="get_read", max_slope = 0.001, wait = 0.2, samples = 4, Rsq = 0.95, complience = 50e-6, do_anyway = False, check_complience=True): # Not yet implemented
        '''This functions waits dynamically until the sensor has reached an equilibrium after changing the bias voltage'''
        # TODO: I have the feeling that this function is not exactly dooing what she is supposed to do, check!
        steady_state = False
        stop = self.main.stop_measurement
        if do_anyway:
            self.log.warning("Overwriting steady_state_check is not adviced. Use with caution")
            stop = False
        counter = 0
        while not steady_state and not stop and check_complience:
            if counter > 5:
                # If too many attempts where made
                self.log.error("Attempt to reach steady state was not successfully after 5 times")
                return False
            counter += 1
            values = []
            if complience:
                if self.check_complience(device, float(complience)):
                    self.stop_measurement()
                    return False

            command = self.build_command(device, command)
            for i in range(samples):
                self.log.debug("Conducting steady state check...")
                values.append(float(str(self.vcw.query(device, command)).split(",")[0]))
                sleep(wait)
            slope, intercept, r_value, p_value, std_err = stats.linregress([i for i in range(len(values))], values)
            if std_err <= 1e-6 and abs(slope) <= abs(max_slope):
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

    def refine_ramp(self, ramp, start, stop, step):
        """Refines a ramp of values eg. for IVCV, in the beginning it makes sense to refine the ramp"""

        if ramp[0] * start >= 0 and ramp[-1] * stop >= 0 and abs(ramp[0]) <= abs(start) and abs(ramp[-1]) >= abs(stop):
            # Todo: if the refined array has positive and negative values it does not work currently
            ramp = np.array(ramp)
            ref_ramp = ramp_value(start, stop, step)
            to_delete = np.logical_and(abs(ramp) >= abs(start), abs(ramp) <= abs(stop))
            start_ind = np.nonzero(to_delete)[0][0]  # Finds the index where I have to insert the new array
            del_list = ramp[~to_delete].tolist()
            for ind, elem in enumerate(ref_ramp):
                del_list.insert(start_ind + ind, elem)
            return del_list
        else:
            self.log.error(
                "Refining of array not possible. Boundaries for refinement must be inside source array. Returning imput array")
            return ramp

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
        self.log.info("Start ramping voltage...")
        voltage_End = float(voltage_End)
        voltage_Start = float(voltage_Start)
        step = float(step)
        wait_time = float(wait_time)

        voltage_step_list = self.ramp_value(voltage_Start, voltage_End, step)

        # Check if current bias voltage is inside this ramp and delete if necessary
        bias_voltage = float(self.settings["settings"]["bias_voltage"])

        for i, voltage in enumerate(voltage_step_list):
            if abs(voltage) > abs(bias_voltage):
                voltage_step_list = voltage_step_list[i:]
                break

        for voltage in voltage_step_list:
            self.change_value(resource, order, voltage)
            if self.check_complience(resource, complience):
                return False
            #self.settings["settings"]["bias_voltage"] = float(voltage)  # changes the bias voltage
            sleep(wait_time)

        return True

    def change_value_query(self, device_dict, order, value="", answer="1"):
        """This function query a command to a device and waits for a return value and compares
        it with the answer statement, if they are the same a true is returned"""
        if type(order) == list:
            for com in order:
                command = self.build_command(device_dict, (com, value))
                answ = self.vcw.query(device_dict, command) # writes the new order to the device
        else:
            command = self.build_command(device_dict, (order, value))
            answ = self.vcw.query(device_dict, command)  # writes the new order to the device

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
            self.vcw.write(device_dict, str(command))  # writes the new order to the device
        except Exception as e:
            self.log.error("Could not send {command!s} to device {device!s}, error {error!s} occured".format(command=command, device=device_dict, error=e))

    def query_device(self, device_dict, command):
        """
        This command just sends the command to the device, and waits for an answer. Warning it is not recommended to use this function. Use this
        function only if you must!

        :param device_dict: Dictionary of the device
        :param command: The command you want to send to the device
        :return: Return string from the device
        """

        try:
            return self.vcw.query(device_dict, str(command))  # writes the new order to the device
        except Exception as e:
            self.log.error("Could not send {command!s} to device {device!s}, error {error!s} occured".format(command=command,
                                                                                                      device=device_dict,
                                                                                                      error=e))

    def change_value(self, device_dict, order, value=""):
        '''This function sends a command to a device and changes the state in the dictionary (state machine)'''
        if type(order) == list:
            for com in order:
                command = self.build_command(device_dict, (com, value))
                self.vcw.write(device_dict, command) # writes the new order to the device
        else:
            command = self.build_command(device_dict, (order, value))
            self.vcw.write(device_dict, command)  # writes the new order to the device

    def check_complience(self, device, complience = None, command="get_read_iv"):
        '''This function checks if the current complience is reached'''
        try:
            if complience == None:
                self.log.error("No complience set for measurement, default complience is used! This may cause deamage to the sensor!")
                complience = device["default_complience"]
        except:
            self.log.error("Device " + str(device) + " has no complience set!")

        command = self.build_command(device, command)
        #value = float(str(self.vcw.query(device, command)).split(",")[0]) #237SMU
        value = str(self.vcw.query(device, command)).split("\t")
        self.settings["settings"]["bias_voltage"] = str(value[1]).strip()  # changes the bias voltage
        if 0. < (abs(float(value[0])) - abs(float(complience)*0.99)):
            self.log.error("Complience reached in instrument " + str(device["Device_name"]) + " at: "+ str(value[0]) + ". Complience at " + str(complience))
            self.queue_to_main.put({"MeasError": "Compliance reached. Value. " + str(value[0]) + " A"})
            return True
        else:
            return False

    @timeit
    def config_setup(self, device, commands = []):
        '''This function configures the setup for a specific measurement.
        Commands is a list of tuples, containing (command, values) if no value is defined only command will be send'''

        for command in commands:
            final_string = self.build_command(device, command)
            self.vcw.write(device, str(final_string))  # finally writes the command to the device

    def capacitor_discharge(self, device_dict, relay_dict, termorder = None, terminal = None, do_anyway=False):
        '''This function checks if the capacitor of the decouple box is correctly discharged
        First is input is the device which measure something and relay_dict is the relay which need to be switched'''

        self.log.info("Discharging capacitors...")
        # First switch the smu terminals front/rear
        if termorder:
            self.change_value(device_dict, termorder, terminal)

        # Set the switching for the discharge (a relay must be switched in the decouple box by applying 5V
        #sleep(1.) # Slow switching shit on BB
        error = self.change_value_query(relay_dict, "set_discharge", "ON", "DONE")
        if error:
            self.queue_to_main.put({"RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " +  str("DONE") + " got " + str(error) + " instead."})
            self.log.error("Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " +  str("DONE") + " got " + str(error) + " instead.")
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
                command = self.build_command(device_dict, "get_read")
                voltage.append(float(self.vcw.query(device_dict, command)))

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
                                               "RequestError": "Capacitor discharged failed! Switching the discharge"
                                                               " relay failed! Expected reply from device would be: "
                                                               + str("DONE") + " got " + str(error) + " instead."})
                    self.log.error(
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
                self.vcw.write(device_dict, command)  # writes the new order to the device
                # return to default mode for this switching
                error = self.change_value_query(relay_dict, "set_discharge", "OFF", "DONE")
                if error:
                    self.queue_to_main.put({"RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                                            "DONE") + " got " + str(error) + " instead."})
                    self.log.error(
                        "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                            "DONE") + " got " + str(error) + " instead.")

                return False


    def stop_measurement(self):
        """Stops the measurement"""
        self.log.critical("Measurement stop sended by framework...")
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)

if __name__ == "__main__":
    def refine_ramp(ramp, start, stop, step):
        """Refines a ramp of values eg. for IVCV, in the beginning it makes sense to refine the ramp"""

        # Check if new ramp fits inside the to refine array
        if ramp[0] * start >= 0 and ramp[-1] * stop >= 0 and abs(ramp[0]) <= abs(start) and abs(ramp[-1]) >= abs(stop):
            # Todo: if the refined array has positive and negative values it does not work currently
            ramp = np.array(ramp)
            ref_ramp = ramp_value(start, stop, step)
            to_delete = np.logical_and(abs(ramp) >= abs(start), abs(ramp) <= abs(stop))
            start_ind = np.nonzero(to_delete)[0][0] # Finds the index where I have to insert the new array
            del_list = ramp[~to_delete].tolist()
            for ind, elem in enumerate(ref_ramp):
                del_list.insert(start_ind+ind, elem)
            return del_list
        else:
            print("Refining of array not possible. Boundaries for refinement must be inside source array. Returning imput array")
            return ramp

    def ramp_value(min_value, max_value, deltaI):
        '''This function accepts single values and returns a list of values, which are interpreted as a ramp function
        Furthermore min and max are corresponding to the absolute value of the number!!!'''

        # Find out if positive or negative ramp
        if max_value > min_value:
            positive = True
        else:
            positive = False

        # Find absolute delta
        abs_delta = abs(min_value - max_value)
        delta_steps = round(abs(abs_delta / deltaI), 0)

        if positive:
            ramp_list = [min_value + deltaI * step for step in range(int(delta_steps))]

            to_big = True
            while to_big and len(ramp_list) > 1:
                if ramp_list[-1] > max_value:
                    ramp_list = ramp_list[:-1]
                else:
                    to_big = False

        else:
            ramp_list = [min_value - deltaI * step for step in range(int(delta_steps))]

            to_big = True
            while to_big and len(ramp_list) > 1:
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

    ramp = ramp_value(0,-100, 10)
    ref = refine_ramp(ramp, -90, -101, 1)
    print(ref)