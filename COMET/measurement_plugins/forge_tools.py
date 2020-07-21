"""This file contains a class containing all tools necessary for forging your own
Measurement plugins"""

import numpy as np
from time import sleep, time
from scipy import stats

try:
    from ..utilities import build_command
except:
    pass
import logging


class tools(object):
    """
    Some tools for forging your own measurement plugins. It needs the framework and the event_loop object
    """

    def __init__(self, framework=None, event_loop=None):
        self.framework = framework
        self.event_loop = event_loop
        self.vcw = framework["VCW"]
        self.settings = framework["Configs"]["config"]
        self.queue_to_main = framework["Message_to_main"]
        self.toolslog = logging.getLogger(__name__)

    def steady_state_check(
        self,
        device,
        command="get_read",
        max_slope=0.001,
        wait=0.2,
        samples=4,
        Rsq=0.95,
        compliance=50e-6,
        do_anyway=False,
        check_compliance=True,
        iteration=7,
        wait_time_factor=1.0
    ):
        """
        This function reads values from a device and fits a linear fit to it. If the fit exceeds a maximum slope it waits a
        specified time and does ot again. If the slope condition is not reached after a few attempts the function returns False.
        Otherwise it returns True and indicates a equilibrium has been reached.

        :param device: The device object which should be queried
        :param command: The command which should be queried
        :param max_slope: The maximum slope, x-axis is measured in seconds, so a slope of 1e-9 is a change of 1n per second
        :param wait: How long to wait between attempts
        :param samples: How many samples should be used
        :param Rsq: Minimum R^2 value
        :param compliance: The compliance value which the value should not exceed
        :param do_anyway: If the result should be ignored
        :param check_compliance: If the program should check the compliance value
        :param iteration: number of iterations
        :param wait_time_factor: factor the waiting time is increased with every iteration
        :return: Bool - True means steady state reached
        """
        # TODO: I have the feeling that this function is not exactly doing what she is supposed to do, check!
        steady_state = False
        bad_fit = False
        high_error = False
        max_iterations = iteration
        if do_anyway:
            self.toolslog.warning(
                "Overwriting steady_state_check is not advised. Use with caution"
            )
            stop = False
        counter = 0
        # Todo: the stop signal does not work correctly here.
        while not steady_state:
            if counter > max_iterations:
                # If too many attempts where made
                self.toolslog.critical(
                    "Attempt to reach steady state was not successfully after {} times for device {}".format(
                        max_iterations, device["Device_name"]
                    )
                )
                return False
            counter += 1
            values = np.zeros(samples)
            times = np.zeros(samples)

            comm = build_command(device, command)
            if compliance and check_compliance:
                if self.check_compliance(device, float(compliance), command=command):
                    self.stop_measurement()
                    return False

            self.toolslog.debug(
                "Conducting steady state check. Iteration={}...".format(counter)
            )
            for i in range(samples):
                start = time()
                values[i] = float(
                    str(self.vcw.query(device, comm).split()[0]).split(",")[0]
                )
                times[i] = time()
                if (time() - start) <= wait*wait_time_factor:
                    sleep(abs(time() - start - wait)*wait_time_factor)
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                np.append([0], np.diff(times)), values
            )
            self.toolslog.debug(
                "Slope parameters: slope={}, intercept={}, r^2={}, err={}".format(
                    slope, intercept, r_value * r_value, std_err
                )
            )
            bad_fit = True if r_value * r_value < Rsq else False
            high_error = True if std_err * 2.5 > abs(slope) else False

            if std_err <= 1e-6 and abs(slope) <= abs(max_slope):
                self.toolslog.debug(
                    "Steady state in device {} was reached with slope={} at  Iteration={}".format(
                        device["Device_name"], slope, counter
                    )
                )
                if bad_fit:
                    self.toolslog.debug(
                        "Steady state check on device {} yielded bad fit conditions. Results may be compromised! R^2={} at iteration={}".format(
                            device["Device_name"], round(r_value * r_value, 2), counter
                        )
                    )
                high_error_slope = abs(slope) + 2.5 * std_err > abs(max_slope)
                # If fit errors are high, the 2.5x the error is bigger as the slope and 0.5% of the maximum_error_slope is bigger as the actuall value
                if (
                    high_error
                    and high_error_slope
                    and abs(slope) + 2.5 * std_err > abs(intercept)
                ):
                    self.toolslog.warning(
                        "Steady state check on device {} yielded high fit error conditions. Results may be compromised! std={} at iteration={}".format(
                            device["Device_name"], std_err, counter
                        )
                    )
                return True
            else:
                self.toolslog.debug(
                    "Steady state was not reached due to high error and steep slope. Iteration={}".format(
                        counter
                    )
                )
        return False

    def ramp_value_log10(self, min_value, max_value, deltasteps):
        """
        This function takes a min and max value, deltasteps and generates a list of values in log10 format with each deltasteps values per decade

        :param min_value: Start value
        :param max_value: End Value
        :param deltasteps: How many steps per decade
        :return: List
        """
        # Todo: from max to min is not working yet
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
        ramp_list = map(lambda x: round(10 ** x, 0), ramp_list)

        # if not positive: # Reverses the ramp list
        #    ramp_list = [x for x in reversed(ramp_list)]

        return ramp_list

    def refine_ramp(self, ramp, start, stop, step):
        """
        Refines a ramp of values eg. for IVCV, in the beginning it makes sense to refine the ramp

        :param ramp: A list of values
        :param start: Start point of refinement (must be inside of ramp)
        :param stop: End point of refinement (must be inside of ramp)
        :param step: The step size of the refinement
        :return: Updated list
        """

        if (
            ramp[0] * start >= 0
            and ramp[-1] * stop >= 0
            and abs(ramp[0]) <= abs(start)
            and abs(ramp[-1]) >= abs(stop)
        ):
            # Todo: if the refined array has positive and negative values it does not work currently
            ramp = np.array(ramp)
            ref_ramp = self.ramp_value(start, stop, step)
            to_delete = np.logical_and(abs(ramp) >= abs(start), abs(ramp) <= abs(stop))
            start_ind = np.nonzero(to_delete)[0][
                0
            ]  # Finds the index where I have to insert the new array
            del_list = ramp[~to_delete].tolist()
            for ind, elem in enumerate(ref_ramp):
                del_list.insert(start_ind + ind, elem)
            return del_list
        else:
            self.toolslog.error(
                "Refining of array not possible. Boundaries for refinement must be inside source array. Returning input array"
            )
            return ramp

    def ramp_value(self, min_value, max_value, deltaI):
        """
        Generates a list of values in the defined stepsize between the and min/max values

        :param min_value: Start point of list
        :param max_value: End point of list
        :param deltaI: Stepsize between points
        :return: List
        """

        deltaI = abs(deltaI)
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

    def do_ramp_value(
        self,
        resource,
        order,
        voltage_Start,
        voltage_End,
        step,
        wait_time=0.05,
        compliance=None,
        set_value=None,
    ):
        """
        This functions ramps a value from one point to another. It actually sends the commands to the device

        :param resource: Device object
        :param order: The command to set tje voltage
        :param voltage_Start: Start point
        :param voltage_End: End point
        :param step: Stepsize
        :param wait_time: Wait between values
        :param compliance: Compliance, if None the compliance check will be skipped
        :param set_value: If you want to set a value each interation in the state machine (must be a callable function)
        :return: True
        """
        self.toolslog.debug("Start ramping...")
        voltage_End = float(voltage_End)
        voltage_Start = float(voltage_Start)
        step = float(step)
        wait_time = float(wait_time)

        voltage_step_list = self.ramp_value(voltage_Start, voltage_End, step)

        # Check if current bias voltage is inside this ramp and delete if necessary
        # bias_voltage = float(self.settings["settings"]["bias_voltage"])

        # for i, voltage in enumerate(voltage_step_list):
        #    if abs(voltage) > abs(bias_voltage):
        #        voltage_step_list = voltage_step_list[i:]
        #        break

        for voltage in voltage_step_list:
            self.change_value(resource, order, voltage)
            if set_value:
                set_value(voltage)
            if (
                voltage != 0 and compliance
            ):  # Otherwise measurement can take to long, which leads to a potential timeout error
                if self.check_compliance(resource, compliance):
                    return False
            # self.settings["settings"]["bias_voltage"] = float(voltage)  # changes the bias voltage
            sleep(wait_time)

        return True

    def query_value(self, device_dict, order, value=""):
        """
        This function simply queries a command to a device.

        :param device_dict: The device object
        :param order: The command to be send
        :param value: The value for the command
        :return: the return from the device
        """
        command = build_command(device_dict, (order, value))
        return self.vcw.query(device_dict, command)

    def change_value_query(
        self, device_dict, order, value="", answer="1", ignore_answer=False,
    ):
        """
        This function query a command to a device and waits for a return value and compares
        it with the answer statement, if they are the same a true is returned otherwise a None

        :param device_dict: Device object
        :param order: The command to be send
        :param value: The value
        :param answer: The answer it should have
        :param ignore_answer: Should the answer be ignored
        :return: Answer or None
        """
        answ = ""
        if not ignore_answer:
            if type(order) == list:
                for com in order:
                    command = build_command(device_dict, (com, value))
                    answ = self.vcw.query(
                        device_dict, command
                    )  # writes the new order to the device
            else:
                command = build_command(device_dict, (order, value))
                answ = self.vcw.query(
                    device_dict, command
                )  # writes the new order to the device

            answ = str(answ).strip()
            if answ == answer:
                return None
            else:
                return answ  # For errorhandling it is the return from the device which was not the expected answer
        else:
            self.toolslog.critical(
                "Overwrite in progress in change_value_query, no check of correct answer is done!!!!"
            )
            command = build_command(device_dict, (order, value))
            self.vcw.write(device_dict, command)
            return None

    def send_to_device(self, device_dict, command, seperate=None):
        """
        This command just sends the command directly to the device. Warning it is not recommended to use this function. Use this
        function only if you must! Use change_value instead.

        :param device_dict: Dictionary of the device
        :param command: The command you want to send to the device
        :param seperate: if specified, the string gets split and the command will be send separately at the separator
        :return: None
        """

        try:
            if seperate:
                for x in str(command).split(seperate):
                    self.vcw.write(device_dict, str(x))
            else:
                self.vcw.write(
                    device_dict, str(command)
                )  # writes the new order to the device
        except Exception as e:
            self.toolslog.error(
                "Could not send {command!s} to device {device!s}, error {error!s} occured".format(
                    command=command, device=device_dict, error=e
                )
            )

    def query_device(self, device_dict, command):
        """
        This command just sends the command directly to the device, and waits for an answer. Warning it is not recommended to use this function. Use this
        function only if you must! Use query_value instead

        :param device_dict: Dictionary of the device
        :param command: The command you want to send to the device
        :return: Return string from the device
        """

        try:
            return self.vcw.query(
                device_dict, str(command)
            )  # writes the new order to the device
        except Exception as e:
            self.toolslog.error(
                "Could not send {command!s} to device {device!s}, error {error!s} occured".format(
                    command=command, device=device_dict, error=e
                )
            )

    def change_value(self, device_dict, order, value=""):
        """
        This function simply sends a command to a device.

        :param device_dict: The device object
        :param order: The command to be send
        :param value: The value for the command
        :return: None
        """
        command = build_command(device_dict, (order, value))
        self.vcw.write(device_dict, command)
        return None

    def check_compliance(self, device, compliance=None, command="get_read"):
        """
        This function checks if the current compliance is reached.

        :param device: The device object
        :param compliance: The compliance value
        :param command: The command to check
        :return: Bool
        """
        try:
            if compliance == None:
                self.toolslog.error(
                    "No compliance set for measurement, default compliance is used! This may cause deamage to the sensor!"
                )
                compliance = device["default_compliance"]
        except:
            self.toolslog.error("Device " + str(device) + " has no compliance set!")

        command = build_command(device, command)
        # value = float(str(self.vcw.query(device, command)).split(",")[0]) #237SMU
        value = str(self.vcw.query(device, command)).split("\t")
        if len(value) > 1:
            self.settings["settings"]["bias_voltage"] = str(
                value[1]
            ).strip()  # changes the bias voltage

        if 0.0 < (abs(float(value[0])) - abs(float(compliance) * 0.99)):
            self.toolslog.error(
                "compliance reached in instrument "
                + str(device["Device_name"])
                + " at: "
                + str(value[0])
                + ". compliance at "
                + str(compliance)
            )
            # self.queue_to_main.put({"MeasError": "Compliance reached. Value. " + str(value[0]) + " A"})
            return True
        else:
            return False

    def config_setup(self, device, commands=(), delay=0.0):
        """
        This function configures the setup for a specific measurement.
        Commands is a list of tuples, containing (command, values) if no value is defined only command will be send

        :param device: The device object
        :param commands: A list of tuples with (command, values). If no value is defined only command will be send
        :param delay: The delay between each command
        :return: None
        """

        for command in commands:
            final_string = build_command(device, command)
            self.vcw.write(
                device, str(final_string)
            )  # finally writes the command to the device
            sleep(delay)

    def stop_measurement(self):
        """Sends a signal to the framework to stop every measurement"""
        self.toolslog.critical("Measurement stop sended by tools functions...")
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.queue_to_main.put(order)

    def capacitor_discharge(
        self, device_dict, relay_dict, Setterminal=None, terminal=None, do_anyway=False,
    ):
        """
        This function is rather special for SQC. It checks if the capacitor of the decouple box is correctly discharged

        :param device_dict: Device object
        :param relay_dict: Relay object
        :param Setterminal: set terminla command
        :param terminal: terminal Front or back
        :param do_anyway: Do it anyway
        :return: Bool
        """

        # Todo: this function needs clean up and generalization
        self.toolslog.info("Discharging capacitors...")
        answer_from_device = "OK"

        if not device_dict or not relay_dict:
            self.toolslog.info(
                "No discharge device/switching specified, skipping discharge and returning True..."
            )
            return True

        # First switch the smu terminals front/rear
        if Setterminal:
            self.change_value(device_dict, Setterminal, terminal)

        # Set the switching for the discharge (a relay must be switched in the decouple box by applying 5V
        # sleep(1.) # Slow switching shit on BB
        all_ok = False
        while not all_ok:
            error = self.change_value_query(relay_dict, "set_discharge", "ON", answer_from_device)
            if error:
                self.queue_to_main.put(
                    {
                        "RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: "
                        + str(answer_from_device)
                        + " got "
                        + str(error)
                        + " instead."
                    }
                )
                self.toolslog.error(
                    "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: "
                    + str(answer_from_device)
                    + " got "
                    + str(error)
                    + " instead."
                )
                all_ok = False
            else: all_ok = True

        sleep(1.0)  # relay is really slow
        self.change_value(device_dict, "set_source_current")
        self.change_value(device_dict, "set_measure_voltage")
        self.change_value(device_dict, "set_output", "ON")
        counter = 0

        while True:
            counter += 1
            voltage = []
            for i in range(3):
                command = build_command(device_dict, "get_read")
                voltage.append(float(self.vcw.query(device_dict, command)))

            if sum(voltage) / len(voltage) <= 0.3:  # this is when we break the loop
                self.change_value(device_dict, "set_output", "OFF")
                self.change_value(device_dict, "set_source_voltage")
                self.change_value(device_dict, "set_measure_current")

                self.change_value(device_dict, Setterminal, "REAR")
                # return to default mode for this switching
                sleep(1.0)  # Slow switching shit on BB
                error = self.change_value_query(
                    relay_dict, "set_discharge", "OFF", answer_from_device
                )
                if error:
                    self.queue_to_main.put(
                        {
                            "RequestError": "Capacitor discharged failed! Switching the discharge"
                            " relay failed! Expected reply from device would be: "
                            + str(answer_from_device)
                            + " got "
                            + str(error)
                            + " instead."
                        }
                    )
                    self.toolslog.error(
                        "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: "
                        + str(answer_from_device)
                        + " got "
                        + str(error)
                        + " instead."
                    )

                    return False
                sleep(1.0)  # relay is really slow
                return True
            else:
                self.queue_to_main.put(
                    {
                        "Info": "Capacitor discharged failed: "
                        + str(counter)
                        + " times, with a voltage of "
                        + str(sum(voltage) / len(voltage))
                    }
                )

            if counter >= 5:
                self.queue_to_main.put(
                    {
                        "FatalError": "The capacitor discharge failed more than 5 times. Discharge the capacitor manually!"
                    }
                )
                # Set output to on for reading mode
                command = build_command(
                    device_dict, ("set_output", "OFF")
                )  # switch back to default terminal
                self.vcw.write(
                    device_dict, command
                )  # writes the new order to the device
                # return to default mode for this switching
                error = self.change_value_query(
                    relay_dict, "set_discharge", "OFF", "OK"
                )
                if error:
                    self.queue_to_main.put(
                        {
                            "RequestError": "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: "
                            + str("OK")
                            + " got "
                            + str(error)
                            + " instead."
                        }
                    )
                    self.toolslog.error(
                        "Capacitor discharged failed! Switching the discharge relay failed! Expected reply from device would be: "
                        + str("OK")
                        + " got "
                        + str(error)
                        + " instead."
                    )

                return False
