# Here the measurement procedures are defined
import logging
import numpy as np
import os
from time import sleep, time, asctime
import datetime
import importlib
from threading import Thread
import traceback

from .utilities import (
    build_command,
    flush_to_file,
    create_new_file,
    save_dict_as_hdf5,
    save_dict_as_json,
)
from .utilities import send_telegram_message


class measurement_class(Thread):
    # meas_loop, main_defaults, pad_data, devices, queue_to_main, queue_to_event_loop, job_details, queue_to_GUI, table, switching, stop_measurement)

    # Todo: write the framework function into the docs how you access all, and the simplification by directly accessing the member of measurement_class
    def __init__(self, event_loop, framework, job_details):

        Thread.__init__(self)
        self.log = logging.getLogger(__name__)
        self.framework = framework
        self.log.info("Initializing measurement thread...")
        self.queue_to_main = framework["Message_to_main"]
        self.event_loop = event_loop
        self.queue_to_event_loop = framework["Message_from_main"]
        self.queue_to_GUI = framework["Queue_to_GUI"]
        self.setup_not_ready = True
        self.job_details = job_details
        self.vcw = framework["VCW"]
        self.measured_data = {}
        self.settings = framework["Configs"]["config"]
        self.default_values_dict = self.settings["settings"]
        self.table = framework["Table"]
        self.switching = framework["Switching"]
        self.devices = framework["Devices"]
        self.client = framework["Client"]
        self.time_const = 1  # sec
        self.all_plugins = {}
        self.measurement_files = {}
        self.measurement_data = {}
        self.write = None
        self.save_data = False
        self.env_waiting_time = 60 * 15  # Five minutes
        self.build_command = build_command
        self.skip_tests = False  # This must always be False!!! only for debugging !!!

        # Build all data arrays
        if self.settings["settings"].get("measurement_types", None):
            for data_files in self.settings["settings"]["measurement_types"]:
                self.measurement_data.update(
                    {data_files: [[np.zeros(0)], [np.zeros(0)]]}
                )
        else:
            self.log.warning(
                "No measurement_types specified, no data storage initiated!"
            )

    def run(self):
        self.log.info("Starting measurement thread...")
        self.queue_to_main.put({"STATE": "Preparing Setup..."})
        self.settings["settings"]["Start_time"] = str(datetime.datetime.now())
        self.load_plugins()
        self.reload_plugins()  # This seems useless, but this ensures, that the newest version of the plugin is in memory!
        self.write_data()

        # Start the humidity/temperature control if checked
        if (
            self.event_loop.default_dict["control_environment"]
            and "temphum_controller" in self.devices
        ):
            self.change_value(
                self.devices["temphum_controller"], "set_environement_control", "ON"
            )

        # Perform the setup check and start the measurement
        # -------------------------------------------------------------------------------
        if (
            self.setup_ready()
        ):  # Checks if measurements can be conducted or not if True: an critical error occured

            # Start the light that the measurement is running
            if "lights_controller" in self.devices:
                self.external_light(self.devices["lights_controller"], True)
            else:
                self.log.info("No external lights controller found")
            # -----------------------------------------------------------------------------------------------------------
            try:
                self.make_measurement_plan()
            except Exception as err:
                raise err
            # -----------------------------------------------------------------------------------------------------------
            sleep(0.1)
            if "lights_controller" in self.devices:
                self.external_light(self.devices["lights_controller"], False)
            else:
                self.log.info("No external lights controller found")
            self.close_measurement_files()
            # Stop the humidity/temperature control if checked
            #if "temphum_controller" in self.devices:
            #    self.change_value(
            #        self.devices["temphum_controller"],
            #        "set_environement_control",
            #        "OFF",
            #    )

        elif (
            self.skip_tests
        ):  # This is just for debugging and can lead to unwanted behavior
            self.make_measurement_plan()
            self.close_measurement_files()

        else:
            self.log.error(
                "Measurement could not be conducted. Setup failed the readiness check. "
                "Please check the logs for more information what happened"
            )
            operator = self.default_values_dict.get("Current_operator", "None")
            send_telegram_message(
                operator,
                "Measurement was not conducted, since the setup failed the readiness check. "
                "Check the Log files to see what exactly failed.",
                self.default_values_dict,
                self.client,
            )

        # Perfom the setup check and start the measurement
        # -------------------------------------------------------------------------------
        self.queue_to_event_loop.put(
            {"Status": {"MEASUREMENT_FINISHED": True}}
        )  # States that the measurement is finished
        self.queue_to_main.put({"STATE": "Measurement finished"})

    def close_measurement_files(self):
        """
        This function closes all measurement files which have been opened during a measurement run
        """
        for file in self.measurement_files.values():
            os.close(file)
            self.log.info("Closed measurement file: {!s}".format(file))
        self.measurement_files = {}

    def external_light(self, device_dict, bool):
        """Turns the light on when measurements are running"""
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
        all_measurement_functions = os.listdir(
            os.path.join(self.framework["rootdir"], "measurement_plugins")
        )
        all_measurement_functions = list(
            set([modules.split(".")[0] for modules in all_measurement_functions])
        )

        self.log.debug(
            "All found measurement functions: " + str(all_measurement_functions) + "."
        )

        # import all modules specified in the measurement order, so not all are loaded
        if "measurement_order" in self.settings["settings"]:
            for modules in self.settings["settings"]["measurement_order"]:
                if modules in all_measurement_functions:
                    self.all_plugins.update(
                        {
                            modules: importlib.import_module(
                                "COMET.measurement_plugins." + modules
                            )
                        }
                    )
                    self.log.debug("Imported module: {}".format(modules))
                else:
                    if modules not in to_ignore:
                        self.log.error(
                            "Could not load module: {}. It was specified in the settings but"
                            " no module matches this name.".format(modules)
                        )
        else:
            self.settings["settings"]["measurement_order"] = []
            self.log.warning(
                "No measurement_order specified, no measurements can be conducted!"
            )

    def reload_plugins(self):
        """Reloads the measurement plugins that are already loaded. Only works if plugins are already init"""
        self.log.debug("Relaoding measurement plugins...")
        for module in self.all_plugins.values():
            importlib.reload(module)

    def create_data_file(self, header, filepath, filename="default"):
        self.log.debug("Creating new data file with name: {!s}".format(filename))
        file, version = create_new_file(
            filename, filepath
        )  # Creates the file at the destination
        self.default_values_dict["file_version"] = float(version)
        flush_to_file(file, header)  # Writes the header to the file
        return file  # Finally returns the file object

    def setup_ready(self):
        """This function checks if all requirements are met for successful measurement"""
        self.log.debug("Conducting setup check...")
        # Check if all devices have a visa resource assigned otherwise return false
        for device in self.devices.values():
            if not device.get("Visa_Resource", None):
                self.log.error(
                    device["Device_name"]
                    + " has no Visa Resource assigned! Measurement cannot be conducted."
                )
                return False

        # Check if lights and environment is valid
        if "lights" in self.settings["settings"]:
            if self.settings["settings"]["lights"]:
                # Wait a few seconds for the controller to send the data if the box was open previously
                counter = 0
                lights_ON = True
                self.queue_to_main.put({"Info": "There seems to be light in the Box."})
                self.log.warning(
                    "The box seems to be open or the lights are still on in the Box"
                )
                while lights_ON:
                    sleep(5)
                    if self.settings["settings"]["lights"]:
                        counter += 1
                    else:
                        lights_ON = False

                    if counter >= 3:
                        self.log.error(
                            "Box seems to be open or the lights are still on in the Box, aborting program"
                        )
                        return False
        else:
            self.log.warning(
                "Variable missing for internal lights settings. No lights check!"
            )

        if "control_environment" in self.event_loop.default_dict:
            if self.event_loop.default_dict["control_environment"]:
                min = self.settings["settings"]["current_hummin"]
                max = self.settings["settings"]["current_hummax"]

                if (
                    self.event_loop.humidity_history[-1] < min
                    or self.event_loop.humidity_history[-1] > max
                ):  # If something is wrong
                    self.queue_to_main.put(
                        {
                            "Info": "The humidity levels not reached. Wait until state is reached. Waiting time: "
                            + str(self.env_waiting_time)
                        }
                    )
                    wait_for_env = True
                    start_time = time()
                    while wait_for_env:
                        if not self.event_loop.stop_measurement:
                            sleep(1)
                            if (
                                self.event_loop.humidity_history[-1] > min
                                and self.event_loop.humidity_history[-1] < max
                            ):
                                self.queue_to_main.put(
                                    {
                                        "Info": "Humidity levels reached, proceeding with measurement..."
                                    }
                                )
                                wait_for_env = False
                            else:
                                diff = abs(start_time - time())
                                if diff > self.env_waiting_time:
                                    self.queue_to_main.put(
                                        {
                                            "FatalError": "The humidity levels could not be reached. Aborting program"
                                        }
                                    )
                                    return False
                        else:
                            return False
            else:
                self.log.warning(
                    "Variable missing for humidity_control settings. No humidity check made!"
                )

            # Test if realy of the brandbox is ok
            try:
                if not self.perform_relay_switch_state_check():
                    self.log.error("Relay state could not be verified. Please check and try again!")
                    return False
            except:
                self.log.error("Relay state could not be verified. Most likely a deivce is not present. Please check and try again")
                abort = True

        return True  # If everything worked

    def make_measurement_plan(self):
        """This function recieves the orders from the main and creates a measurement plan."""

        # Check if order of measurement is in place
        self.log.debug("Generating measurement plan...")
        if "measurement_order" in self.settings["settings"]:
            for measurement in self.settings["settings"]["measurement_order"]:
                abort = False
                if (
                    self.event_loop.stop_measurement
                ):  # Check if some abort signal was send
                    return
                if measurement in self.job_details and measurement in self.all_plugins:
                    if self.save_data:  # First create files, if necessary.
                        filepath = self.job_details.get("Filepath", None)
                        filename = (
                            str(measurement)[:3]
                            + "_"
                            + self.job_details.get("Filename", "None")
                        )
                        if "Header" in self.job_details and filepath:
                            self.measurement_files.update(
                                {
                                    measurement: self.create_data_file(
                                        self.job_details["Header"] + "\n",
                                        filepath,
                                        filename,
                                    )
                                }
                            )
                        else:
                            self.log.error(
                                "While trying to create a measurement file for measurement {} "
                                "an error happened. This usually happens if either/both a filepath and "
                                "a header are missing for the measurement".format(
                                    str(measurement)
                                )
                            )
                elif (
                    measurement not in self.all_plugins
                    and measurement in self.job_details
                ):
                    self.log.error(
                        "Measurement "
                        + str(measurement)
                        + " was not found as a defined measurement module."
                        "This should never happen, only possible if you "
                        "temper with the plugins dict"
                    )
                    abort = True
                else:
                    abort = True

                # Here the actual measurement starts -------------------------------------------------------------------
                if not abort:
                    self.queue_to_main.put({"STATE": "Measurement running"})
                    self.log.info("Trying to start measurement " + str(measurement))
                    operator = self.default_values_dict.get("Current_operator", "None")
                    send_telegram_message(
                        operator,
                        "Starting measurement: {}".format(measurement),
                        self.default_values_dict,
                        self.client,
                    )
                    starttime = time()
                    try:
                        meas_object = getattr(
                            self.all_plugins[measurement],
                            str(measurement).replace(" ", "") + "_class",
                        )(self)
                        meas_object_return = meas_object.run()
                        if meas_object_return:
                            self.log.critical(
                                "The measurement {} returned: {}".format(
                                    measurement, meas_object_return
                                )
                            )
                        endtime = time()
                        deltaT = abs(starttime - endtime)
                        self.log.info(
                            "The "
                            + str(measurement)
                            + " took "
                            + str(round(deltaT, 0))
                            + " seconds."
                        )

                        # Inform the user about the outcome
                        operator = self.default_values_dict.get(
                            "Current_operator", "None"
                        )
                        if self.event_loop.stop_all_measurements_query():
                            send_telegram_message(
                                operator,
                                "Hi {}, \nI want to inform you that your measurement has been ABORTED! \n"
                                "The system shutdown was successfull. Please see the LogFile to see what happened. \n\n"
                                "The measurement took {} h \n\n".format(
                                    operator, round(deltaT / 3600, 2)
                                ),
                                self.default_values_dict,
                                self.client,
                            )
                        else:
                            send_telegram_message(
                                operator,
                                "Hi {}, \n I want to inform you that your measurement has FINISHED! \n\n"
                                "The measurement took {} h".format(
                                    operator, round(deltaT / 3600, 2)
                                ),
                                self.default_values_dict,
                                self.client,
                            )
                    except Exception as err:
                        errormsg = (
                            "An error happened while conducting"
                            " the measurement: {} with error: {} \n"
                            "Traceback: {}".format(
                                measurement, err, traceback.format_exc()
                            )
                        )
                        self.log.error(errormsg)
                        send_telegram_message(
                            operator, errormsg, self.default_values_dict, self.client
                        )

                        # Shut down the SMU gracely
                        try:
                            if "BiasSMU" in self.devices:
                                send_telegram_message(
                                    operator,
                                    "Emergency SMU shutdown initiated!",
                                    self.default_values_dict,
                                    self.client,
                                )
                                self.emergency_shutdown()
                                send_telegram_message(
                                    operator,
                                    "Emergency SMU shutdown successful!",
                                    self.default_values_dict,
                                    self.client,
                                )
                            else:
                                self.log.error(
                                    "Could not determine bias SMU -> no shutdown!!!"
                                )
                                send_telegram_message(
                                    operator,
                                    "Could not determine bias SMU -> no shutdown!!!"
                                    "The setup may by under high voltage!!!",
                                    self.default_values_dict,
                                    self.client,
                                )
                        except:
                            self.log.error("Emergency shutdown failed!")
                            send_telegram_message(
                                operator,
                                "Emergency shutdown failed! The setup may by under high voltage!!!",
                                self.default_values_dict,
                                self.client,
                            )
                # Here the actual measurement starts -------------------------------------------------------------------

            try:
                if "store_data_as" in self.settings["settings"]:
                    self.save_data_as(
                        self.settings["settings"]["store_data_as"], self.job_details
                    )
            except Exception as err:
                self.log.critical(
                    "Saving data was not possible due to an error: {}".format(err)
                )

    def emergency_shutdown(self):
        self.log.critical("Emergency shutdown of SMU initiated...")
        from .measurement_plugins.forge_tools import tools

        tool = tools(self.framework, self.queue_to_main)
        if "BiasSMU" in self.devices:
            SMU = self.devices["BiasSMU"]
        else:
            self.log.error("Could not determine bias SMU -> no shutdown!!!")
            return
        # Ramp down the voltage

        # Switch to IV for correct biasing for ramp
        self.switching.switch_to_measurement("IV")  # correct bias is applied

        # Get the current voltage from the SMU
        command = self.build_command(SMU, "get_read")
        voltage = round(float(self.vcw.query(SMU, command).split(SMU.get("\t"))[1]))

        # Ramp down to zero and close output
        tool.do_ramp_value(
            resource=SMU,
            order="set_voltage",
            voltage_Start=voltage,
            voltage_End=0,
            step=20,
            wait_time=0.3,
            compliance=0.001,
        )

        tool.change_value(SMU, "set_voltage", "0")
        self.framework["Configs"]["config"]["settings"]["bias_voltage"] = 0.0
        tool.change_value(SMU, "set_output", "0")

    def stop_measurement(self):
        """Stops the measurement"""
        self.log.critical("Measurement stop sended by framework...")
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.queue_to_main.put(order)

    def change_value(self, device_dict, order, value=""):
        """This function sends a command to a device and changes the state in the dictionary (state machine)"""
        if type(order) == list:
            for com in order:
                command = build_command(device_dict, (com, value))
                self.vcw.write(
                    device_dict, command
                )  # writes the new order to the device
        else:
            command = build_command(device_dict, (order, value))
            self.vcw.write(device_dict, command)  # writes the new order to the device

    def save_data_as(
        self, type="json", details={}, data=None, xunits=None, yunits=None
    ):
        """Saves data in a specific data format after completion of measurement.
        This is for databank compatibility """

        # Generate dict
        if not data:
            data_to_dump = self.measurement_data
        else:
            data_to_dump = data
        filepath = os.path.normpath(details["Filepath"])
        final_dict = {"data": {}, "units": [], "measurements": []}
        # Add the endtime in the header as additional header entry
        if "Header" in details:
            details["Header"] += "Endtime: {}".format(asctime())
        final_dict.update(details)
        xaxis = []

        # Sanitize data (exclude x data from every dataset and store the xaxis seperately)
        units_found = False
        for key, data in data_to_dump.items():
            try:
                if np.array(data[1]).any() and np.sum(np.isnan(data[1])) < len(
                    data[1]
                ):  # looks if the array has any data in it
                    xaxis = data[0]
                    final_dict["data"][key] = data[1]  # only ydata here
                    final_dict["measurements"].append(key)
                    # Find the units
                    units_found = False
                    for item in final_dict.values():
                        if isinstance(item, dict):
                            if "Units" in item:
                                if key in item["Units"]:
                                    units_found = True
                                    final_dict["units"].append(item["Units"][key][1])
                    if not units_found:
                        self.log.warning(
                            "No units found for measurement {}. Please add one in the config".format(
                                key
                            )
                        )
                        final_dict["units"].append("arb. units")

            except Exception as err:  # if some other error happens
                self.log.warning(
                    "Could not save data with key {}. Error. {}".format(key, err)
                )

        # add the units

        if xunits and yunits and not units_found:
            for meas in final_dict["measurements"]:
                final_dict["units"].append(yunits[1])
            # Add x axis
            final_dict["measurements"].append(xunits[0])
            final_dict["units"].append(xunits[1])
            final_dict["data"][xunits[0]] = xaxis

        if not units_found:
            self.log.warning(
                "Could not save data, due to missing units specifier. This can be normal!"
            )
            return

        try:
            if final_dict:
                if type.lower() == "json":
                    save_dict_as_json(final_dict, filepath, details["Filename"])
                    return

                elif type.lower() == "hdf5":
                    save_dict_as_hdf5(final_dict, filepath, details["Filename"])
                    return
        except Exception as err:
            self.log.error(
                "Measurement output could not be saved as {}, due to error {}".format(
                    type, err
                )
            )
        else:
            self.log.warning("No data for saving found...")

    def perform_relay_switch_state_check(self):
        """Checks if the relay in the brandbox is correctly switched so that not more than 200 V can be applied to the matrix"""

        self.bias_SMU = self.devices["BiasSMU"]
        self.LCR_meter = self.devices["LCRMeter"]
        self.SMU2 = self.devices["2410SMU"]

        self.change_value(self.LCR_meter, "set_voltage", "0.1")
        self.change_value(self.bias_SMU, "set_voltage", "-3")
        self.change_value(self.bias_SMU, "set_output", "1")
        self.change_value(self.SMU2, "set_terminal", "FRONT")
        self.change_value(self.SMU2, "set_measure_voltage", "")
        self.change_value(self.SMU2, "set_reading_mode", "VOLT")
        self.change_value(self.SMU2, "set_output", "ON")
        sleep(1.)

        voltage = self.vcw.query(self.SMU2, "READ?").split(",")

        if abs(float(voltage[0])) >= 1.:
            self.log.error("It seems that the brandbox is not correctly switched or the relay is malfunctioning!!! ABORT!")
            return False

        self.change_value(self.bias_SMU, "set_voltage", "0.")
        self.change_value(self.bias_SMU, "set_output", "0")
        self.change_value(self.LCR_meter, "set_voltage", "1.")
        self.change_value(self.SMU2, "set_output", "OFF")
        self.change_value(self.SMU2, "set_measure_current", "")
        self.change_value(self.SMU2, "set_terminal", "REAR")
        self.change_value(self.SMU2, "set_reading_mode", "CURR")

        return True
