"""This file contains a class containing all tools necessary for forging your own
Measurement plugins"""


import numpy as np
from time import sleep
from scipy import stats


class forge_tools(object):
    """Some tools for forging your own measurement plugin
    """

    def steady_state_check(self, device, command="get_read", max_slope = 0.001,
                           wait = 0.2, samples = 4, Rsq = 0.95, complience = 50e-6, do_anyway = False,
                           check_complience=True):
        '''This functions waits dynamically until the sensor has reached an equilibrium after changing the bias voltage'''
        # TODO: I have the feeling that this function is not exactly dooing what she is supposed to do, check!
        steady_state = False
        stop = self.main.stop_measurement
        if do_anyway:
            self.log.warning("Overwriting steady_state_check is not adviced. Use with caution")
            stop = False
        counter = 0
        while not steady_state and not stop :
            if counter > 5:
                # If too many attempts where made
                self.log.error("Attempt to reach steady state was not successfully after 5 times")
                return False
            counter += 1
            values = []
            if complience and check_complience:
                if self.check_complience(device, float(complience)):
                    self.stop_measurement()
                    return False

            comm = self.build_command(device, command)
            for i in range(samples):
                self.log.debug("Conducting steady state check...")
                values.append(float(str(self.vcw.query(device, comm)).split(",")[0]))
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
            ref_ramp = self.ramp_value(start, stop, step)
            to_delete = np.logical_and(abs(ramp) >= abs(start), abs(ramp) <= abs(stop))
            start_ind = np.nonzero(to_delete)[0][0]  # Finds the index where I have to insert the new array
            del_list = ramp[~to_delete].tolist()
            for ind, elem in enumerate(ref_ramp):
                del_list.insert(start_ind + ind, elem)
            return del_list
        else:
            self.log.error(
                "Refining of array not possible. Boundaries for refinement must be inside source array. Returning input array")
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

    def change_value_query(self, device_dict, order, value="", answer="1", ignore_answer=True):
        """This function query a command to a device and waits for a return value and compares
        it with the answer statement, if they are the same a true is returned"""
        if not ignore_answer:
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
        else:
            self.log.critical("Overwrite in progress in change_value_query, no check of correct answer is done!!!!")
            command = self.build_command(device_dict, (order, value))
            self.vcw.write(device_dict, command)
            return None

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
            #self.queue_to_main.put({"MeasError": "Compliance reached. Value. " + str(value[0]) + " A"})
            return True
        else:
            return False

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
        error = self.change_value_query(relay_dict, "set_discharge", "ON", "OK")
        if error:
            self.queue_to_main.put({"RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " +  str("OK") + " got " + str(error) + " instead."})
            self.log.error("Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " +  str("OK") + " got " + str(error) + " instead.")
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
                error = self.change_value_query(relay_dict, "set_discharge", "OFF", "OK")
                if error:
                    self.queue_to_main.put({
                                               "RequestError": "Capacitor discharged failed! Switching the discharge"
                                                               " relay failed! Expected reply from device would be: "
                                                               + str("OK") + " got " + str(error) + " instead."})
                    self.log.error(
                        "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                            "OK") + " got " + str(error) + " instead.")

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
                error = self.change_value_query(relay_dict, "set_discharge", "OFF", "OK")
                if error:
                    self.queue_to_main.put({"RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                                            "OK") + " got " + str(error) + " instead."})
                    self.log.error(
                        "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: " + str(
                            "OK") + " got " + str(error) + " instead.")

                return False