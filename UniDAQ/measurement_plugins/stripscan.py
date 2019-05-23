# This file manages the stripscan measurements and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
from scipy import stats
sys.path.append('../UniDAQ')
import datetime
from time import time, sleep
from ..utilities import timeit, transformation


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
        self.voltage_End = self.main.job_details["stripscan"]["EndVolt"]
        self.voltage_Start = self.main.job_details["stripscan"]["StartVolt"]
        self.voltage_steps = self.main.job_details["stripscan"]["Steps"]
        self.complience = self.main.job_details["stripscan"]["Complience"]
        self.bias_SMU = self.main.devices["BiasSMU"]
        self.LCR_meter = self.main.devices["Agilent E4980A"]
        self.SMU2 = self.main.devices["2410 Keithley SMU"]
        self.discharge_SMU = self.main.devices["2410 Keithley SMU"]
        self.discharge_switching = self.main.devices["temphum_controller"]
        self.elmeter = self.main.devices["6517B Keithley Elektrometer"]
        self.measurement_order = ["Istrip", "Rpoly", "Idark", "Cac", "Cint", "Cback", "Idiel", "Rint"]
        self.units = [("Istrip","current[A]"), ("Rpoly", "res[Ohm]"),
                      ("Idiel","current[A]"), ("Idark","current[A]"),
                      ("Rint", "res[Ohm]"), ("Cac", "cap[F]"),
                      ("Cint", "cap[F]"), ("Cback", "cap[F]")]
        self.current_strip = self.main.main.default_dict["current_strip"] # Current pad position of the table
        self.height = self.main.main.default_dict["height_movement"]
        self.samples = 5
        self.last_istrip_pad = -1 # Number of the last pad on which a I strip was conducted, important for rpoly
        self.T = self.main.main.default_dict["trans_matrix"]
        self.V0 = self.main.main.default_dict["V0"]
        self.job = self.main.job_details
        self.sensor_pad_data = self.main.framework["Configs"]["additional_files"]["Pad_files"][self.job["Project"]][self.job["Sensor"]]
        self.strips = len(self.sensor_pad_data["data"])
        self.justlength = 24
        self.rintslopes = [] # here all values from the rint is stored
        self.project = self.main.settings["settings"]["Current_project"] # Warning these values are mutable while runtime!!!
        self.sensor = self.main.settings["settings"]["Current_sensor"] # Use with care!!!
        self.log = logging.getLogger(__name__)

    def run(self):
        # Check if alignment is present or not, if not stop measurement
        if not self.main.main.default_dict["Alignment"]:
            self.log.error("Alignment is missing. Stripscan can only be conducted if a valid alignment is present.")
            self.stop_everything()
            return


        # Preconfig the electrometer for current measurements, zero corr etc.
        commands = [("set_zero_check", "ON"),
                    ("set_measure_current", ""),
                    ("set_auto_current_range", "OFF"),
                    ("set_current_range", "20e-12"),
                    ("set_zero_correlation", "ON"),
                    ("set_current_range", "20e-9"),
                    ("set_auto_current_range", "ON")
                    ]
        self.main.config_setup(self.elmeter, commands)

        # Actually does something
        if "stripscan" in self.main.job_details:
            if "frequencyscan" not in self.main.job_details["stripscan"]:
                if "singlestrip" in self.main.job_details["stripscan"]:
                    self.do_singlestrip(self.main.job_details["stripscan"]["singlestrip"])
                else:
                    self.do_stripscan()

        # Ramp down the voltage after stripscan
        # Discharge the capacitors in the decouple box
        # Switch to IV for correct biasing for ramp
        self.switching.switch_to_measurement("IV")  # correct bias is applied

        self.main.ramp_voltage(self.bias_SMU, "set_voltage", self.current_voltage, 0, self.voltage_steps, wait_time=0.3, complience=0.001)
        self.main.change_value(self.bias_SMU,"set_voltage", "0")
        self.main.change_value(self.bias_SMU, "set_output", "0")

        if not self.main.capacitor_discharge(self.discharge_SMU, self.discharge_switching, "set_terminal", "FRONT", do_anyway=True):
            self.stop_everything()

        #self.save_rint_slopes()

    def stop_everything(self):
        """Stops the measurement
        A signal will be genereated and send to the event loops, which sets the statemachine to stop all measurements"""
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)
        self.log.warning("Measurement STOP was called, check logs for more information")


    def estimate_duration(self, start_time, list_strip_measurements):
        """Estimate time
        Will not be correct, since CV usually is faster, but it is just a estimation.
        -----------------------------------------------------------------------------
        Start and end timer. all of this quick and dirty but it will suffice"""
        # Todo: review code!!!
        est_end = 0
        for measurements in list_strip_measurements:
            # Loop over all strip measurements
            if measurements in self.job.get("stripscan", {}):
                est_end += float(self.total_strips)*float(self.main.settings["settings"]["strip_scan_time"])
                break # breaks out of loop if one measurement was found


        if "IV" in self.job.get("IVCV", {}):
            est_end += float(self.main.setting["settings"]["IVCV_time"])
        if "CV" in self.job.get("IVCV", {}):
            est_end += float(self.main.settings["settings"]["IVCV_time"])

        est_end = start_time + datetime.timedelta(seconds=est_end)
        self.main.settings["settings"]["End_time"] = str(est_end)
        # Estimate time
        # Will not be correct, since CV usually is faster, but it is just a estimation.
        # -----------------------------------------------------------------------------

    def find_stripnumber(self):
        # Try find the strip number of the sensor.
        # Todo: Review code!!!
        try:
            self.total_strips = len(self.sensor_pad_data[self.project][str(self.sensor)]["data"])
            self.log.debug("Extracted strip number is: {!s}".format(self.total_strips))
        except:
            self.log.error("Sensor " + str(self.sensor) + " not recognized. Can be due to missing pad file.")
            self.main.main.stop_measurement = True
            self.main.framework["Message_to_main"].put({"DataError": "Sensor " + str(self.sensor) + " not recognized. Can be due to missing pad file."})
            if "strip" in self.job:
                self.log.error("Fatal error Sensor " + str(self.sensor) + " not recognized. Strip scan cannot be conducted. Check Pad files")
                self.stop_everything()


    def save_rint_slopes(self):
        # If a rint measurement was done save the data to a file
        # Todo: save rint slopes as well
        if self.main.save_data and self.rintslopes:

            filepath = self.main.job_details["Filepath"]
            filename = "rint_ramp_" + self.main.job_details["Filename"]

            rintsettings = self.main.main.default_dict["Rint_MinMax"]
            header = self.main.job_details["Header"]
            header += " #Ramp Voltage: " + str(rintsettings[0]) + " - "+ str(rintsettings[0])+ "V\n"
            header += " #Delta V: " + str(int(rintsettings[2])) + " V\n\n"

            unitsheader = "Pad[#]".ljust(self.justlength) + "Voltage[V]".ljust(self.justlength) + "Current[A]".ljust(self.justlength)

            header += [unitsheader for i in self.rintslopes]
            header += "\n"
            file = self.main.create_data_file(header, filepath, filename)

    def do_preparations_for_stripscan(self):
        """This function prepares the setup, like ramping the voltage and steady state check
        """
        self.log.debug("Stripscan: Preparing everything for stripscans")
        if self.main.save_data and "frequencyscan" not in self.main.job_details["stripscan"]:
            self.main.write(self.main.measurement_files["stripscan"], self.main.job_details["stripscan"].get("Additional Header", ""))  # TODO: pretty useless, an additional header to the file if necessary

            # Add the additional params to the header
            params_string = ""
            for key, value in self.sensor_pad_data.get("additional_params", {}).items():
                params_string += "# " + str(key) + ": " + str(value) + "\n"
            params_string += "\n\n"
            self.main.write(self.main.measurement_files["stripscan"], params_string)
        # extend for additional files

        # Switch to IV for correct biasing for ramp
        if not self.switching.switch_to_measurement("IV"):
            self.stop_everything()

        #Configure the setup, complience and switch on the smu
        self.main.config_setup(self.bias_SMU, [("set_complience_current", str(self.complience))])
        self.main.change_value(self.bias_SMU, "set_output", "1")

        # Move the table down while ramp
        self.main.table.move_down(self.height)

        # Ramps the voltage, if ramp voltage returns false something went wrong -> stop
        if not self.main.ramp_voltage(self.bias_SMU, "set_voltage", self.voltage_Start, self.voltage_End, self.voltage_steps, wait_time = 1, complience=self.complience):
            self.current_voltage = self.main.main.default_dict["bias_voltage"]
            self.stop_everything()

        #If everything works make steady state check
        else:
            if self.main.steady_state_check(self.bias_SMU, command="get_read_current", max_slope = 1e-6, wait = 0, samples = 3, Rsq = 0.5, complience=self.complience): # Is a dynamic waiting time for the measuremnts
                self.current_voltage = self.main.main.default_dict["bias_voltage"]
                if self.main.check_complience(self.bias_SMU, self.complience): #if complience is reached stop everything
                    self.stop_everything()
            else:
                self.stop_everything()

        # Perform the open correction
        self.perform_open_correction(self.LCR_meter, "Cac")

        # Move the table up again
        self.main.table.move_up(self.height)

    def perform_open_correction(self, LCR, measurement = "Cac"):
        # Warning: table has to be down for that

        if not self.switching.switch_to_measurement(measurement):
            self.stop_everything()
            return
        sleep(0.2)
        self.main.change_value(LCR, "set_perform_open_correction", "")
        # Alot of time can be wasted by the timeout of the visa
        ready_command = self.main.build_command(LCR, "get_all_done")
        counter = 0  # counter how often the read attempt will be carried out
        self.vcw.write(LCR, ready_command)
        while True:
            done = self.vcw.read(LCR)
            if done:
                break
            else:
                if counter > 10:
                    self.log.error("LCR meter did not answer after 10 times during open correction calibration.")
                    self.stop_everything()
                counter += 1

    def do_singlestrip(self, job):
        """This function conducts the measurements defined for a single strip measurement"""
        self.log.debug("Stripscan: Singlestrip now started")
        self.do_preparations_for_stripscan()

        if not self.main.main.stop_measurement:
            measurement_header = "Pad".ljust(self.justlength)  # indicates the measurement
            unit_header = "#".ljust(self.justlength)  # indicates the units for the measurement

            # Now add the new header to the file
            if self.main.save_data:
                self.main.write(self.main.measurement_files["stripscan"], measurement_header + "\n" + unit_header + "\n")

            # Discharge the capacitors in the decouple box
            if not self.main.capacitor_discharge(self.discharge_SMU, self.discharge_switching, "set_terminal", "FRONT", do_anyway=True): self.stop_everything()

            # Conduct the actual measurements and send it to the main
            for measurement in self.measurement_order:
                if measurement in job["Measurements"] and not self.main.main.stop_measurement:  # looks if measurement should be done

                    # Now conduct the measurement
                    self.main.table.move_to_strip(self.sensor_pad_data, str(job["Strip"]), self.trans, self.T, self.V0, self.height)
                    value = getattr(self, "do_" + measurement)(job["Strip"], self.samples, write_to_main = False)

                    # Write this to the file
                    if value and self.main.save_data:
                        self.main.write(self.main.measurement_files["stripscan"],str(float(value)).ljust(self.justlength))  # Writes the value to the file
                    else:
                        if self.main.save_data:
                            self.main.write(self.main.measurement_files["stripscan"],
                                            "--".ljust(self.justlength))  # Writes nothing if no value is aquired

                    # Write the data back to the GUI thread
                    if value:
                        self.main.queue_to_main.put({str(measurement): [int(job["Strip"]), float(value)]})

            # Write new line
            if self.main.save_data:
                self.main.write(self.main.measurement_files["stripscan"], "\n")

    @timeit
    def do_stripscan(self):
        '''This function manages all stripscan measurements, also the frequency scan things
        Its ment to be used only once during the initiatior of the class'''

        self.do_preparations_for_stripscan()

        if not self.main.main.stop_measurement:
            # generate the list of strips per measurement which should be conducted and the units and so on for the
            measurement_header = "Pad".ljust(self.justlength) # indicates the measuremnt
            unit_header = "#".ljust(self.justlength) # indicates the units for the measurement
            for measurement in self.measurement_order:
                if measurement in self.main.job_details["stripscan"]:  # looks if measurement should be done
                    # Now generate a list of strips from the settings of the measurement
                    min = self.main.job_details["stripscan"][measurement]["start_strip"]
                    max = self.main.job_details["stripscan"][measurement]["end_strip"]
                    delta = self.main.job_details["stripscan"][measurement]["measure_every"]
                    strip_list = self.main.ramp_value(min, max, delta)
                    self.main.job_details["stripscan"][measurement].update({"strip_list": strip_list})
                    unit_index = [x[0] for x in self.units].index(measurement) # gets me the index for the units
                    unit_header += str(self.units[unit_index][1]).ljust(self.justlength)
                    measurement_header += str(measurement).ljust(self.justlength)

            # Now add humidity and temperature header
            if self.main.job_details.get("environemnt", True):
                measurement_header += "Temperature".ljust(self.justlength)+"Humidity".ljust(self.justlength)
                unit_header += "degree[C]".ljust(self.justlength)+"rel. percent[rel%]".ljust(self.justlength)

            # Now add the new header to the file
            if self.main.save_data:
                self.main.write(self.main.measurement_files["stripscan"], measurement_header + "\n" + unit_header + "\n")

            # Discharge the capacitors in the decouple box
            if not self.main.capacitor_discharge(self.discharge_SMU, self.discharge_switching, "set_terminal", "FRONT", do_anyway=True):
                self.stop_everything()

            #  Do the actual measurements, first move, then conduct
            #Todo: make it possible to measure from up to down
            #results = []
            for current_strip in range(1, int(self.strips+1)): # Loop over all strips
                if not self.main.main.stop_measurement: # Prevents that empty entries will be written to file after aborting the measurement
                    self.current_strip = current_strip
                    #results.append({}) # Adds an empty dict to the results for the bad strip detection
                    start = time()  # start timer for a strip measurement
                    if self.main.save_data:
                        self.main.write(self.main.measurement_files["stripscan"], str(self.sensor_pad_data["data"][str(current_strip)][0]).ljust(self.justlength))  # writes the strip to the file
                    for measurement in self.measurement_order:
                        if measurement in self.main.job_details["stripscan"] and not self.main.main.stop_measurement: # looks if measurement should be done
                            # Now conduct the measurement
                            # But first check if this strip should be measured with this specific measurement
                            if current_strip in self.main.job_details["stripscan"][measurement]["strip_list"]:
                                self.main.table.move_to_strip(self.sensor_pad_data, str(self.current_strip), self.trans, self.T, self.V0, self.height)
                                if not self.main.main.stop_measurement and not self.main.check_complience(self.bias_SMU, self.complience):
                                    value = 0
                                    try:
                                        self.log.info("Conducting measurement: {!s}".format(measurement))
                                        value = getattr(self, "do_"+measurement)(current_strip, self.samples)
                                        if not value:
                                            self.log.error("An Error happened during strip measurement {!s}, please check logs!".format(measurement))
                                    except Exception as err:
                                        self.log.error("During strip measurement {!s} a fatal error occured: {!s}".format(measurement, err), exc_info=True)  # log exception info at FATAL log level

                                    # Write this to the file
                                    if value and self.main.save_data:
                                        self.main.write(self.main.measurement_files["stripscan"],
                                                str(float(value)).ljust(self.justlength))  # Writes the value to the file
                            else:
                                if self.main.save_data:
                                    self.main.write(self.main.measurement_files["stripscan"], "--".ljust(
                                        self.justlength))  # Writes nothing if no value is aquired

                    # In the end do a quick bad strip detection
                    try:
                        # Todo. This does not work now
                        #badstrip = self.main.main.analysis.do_contact_check(self.main.measurement_data)
                        badstrip = False
                        if badstrip:
                            self.log.error("Bad contact of needles detected!: " + str(current_strip))
                            # Add the bad strip to the list of bad strips
                            if str(current_strip) in self.main.badstrip_dict:
                                self.main.badstrip_dict[str(current_strip)].update(badstrip)
                            else:
                                self.main.badstrip_dict[str(current_strip)] = badstrip
                                self.main.main.default_dict["Bad_strips"] += 1  # increment the counter
                    except Exception as e:
                        self.log.error("An error happend while performing the bad contact determination with error: "
                                       "{}".format(e))
                        badstrip = False

                    if not self.main.main.stop_measurement:
                        # After all measurements are conducted write the environment variables to the file
                        if self.main.job_details.get("enviroment", False):
                            string_to_write = str(self.main.main.temperatur_history[-1]).ljust(self.justlength) + str(self.main.main.humidity_history[-1]).ljust(self.justlength)
                        self.main.write(self.main.measurement_files["stripscan"], string_to_write)

                        # Write new line
                        if self.main.save_data:
                            self.main.write(self.main.measurement_files["stripscan"], "\n")

                        # Do the bad strip detection


                    if abs(float(start - time())) > 1.: # Rejects all measurements which are to short to be real measurements
                        delta = float(self.main.main.default_dict["strip_scan_time"]) + abs(start - time())
                        self.main.main.default_dict["strip_scan_time"] = str(delta / 2.)  # updates the time for strip measurement


    def __do_simple_measurement(self, str_name, device, xvalue = -1, samples = 5, write_to_main = True, query="get_read"):
        '''
         Does a simple measurement - really simple. Only acquire some values and build the mean of it

        :param str_name: What measurement is conducted
        :param device: Which device schould be used
        :param xvalue: Which strip we are on, -1 means arbitrary
        :param samples: How many samples should be taken
        :param write_to_main: Writes the value back to the main loop
        :return: Returns the mean of all aquired values
        '''
        # Do some averaging over values
        values = []
        for i in range(samples): # takes samples
            values.append(float(str(self.vcw.query(device, device[query])).split(",")[0]))
        value = sum(values) / len(values)  # averaging

        self.main.measurement_data[str(str_name)][0] = np.append(self.main.measurement_data[str(str_name)][0],[float(xvalue)])
        self.main.measurement_data[str(str_name)][1] = np.append(self.main.measurement_data[str(str_name)][1],[float(value)])

        if write_to_main: # Writes data to the main, or not
            self.main.queue_to_main.put({str(str_name): [float(xvalue), float(value)]})

        return value

    def do_Rpoly(self,  xvalue = -1, samples = 5, write_to_main = True):
        '''Does the rpoly measurement'''
        device_dict = self.SMU2
        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("Rpoly"):
                self.stop_everything()
                return
            voltage = -1.
            self.main.config_setup(device_dict, [("set_source_voltage", ""), ("set_measure_current", ""),("set_voltage", voltage), ("set_complience", 90E-6), ("set_output", "ON")])  # config the 2410 for 1V bias on bias and DC pad
            if self.main.steady_state_check(device_dict, command="get_read", max_slope=1e-6, wait=0, samples=3, Rsq=0.5, check_complience=False):  # Is a dynamic waiting time for the measuremnt
                value = self.__do_simple_measurement("Rpoly", device_dict, xvalue, samples, write_to_main=False) # This value is istrip +
            else:
                self.main.config_setup(device_dict, [("set_output", "OFF"), ("set_voltage", 0)])
                return False
            # Now subtract the Istrip
            if self.last_istrip_pad == xvalue:
                #todo: richtiger wert nehemen
                Istrip = self.main.measurement_data["Istrip"][1][-1]
            else:# If no Istrip then aquire a value
                self.log.info("No Istrip value for Rpoly calculation could be found, Istrip measurement will be conducted on strip {}".format(int(xvalue)))
                Istrip = self.do_Istrip(xvalue, samples, False)
                # Iges = Ipoly+Istrip
            value = float(value)-float(Istrip) # corrected current value

            rpoly = voltage/float(value)

            if write_to_main:  # Writes data to the main, or not
                self.main.measurement_data[str("Rpoly")][0] = np.append(self.main.measurement_data[str("Rpoly")][0],[float(xvalue)])
                self.main.measurement_data[str("Rpoly")][1] = np.append(self.main.measurement_data[str("Rpoly")][1],[float(rpoly)])
                self.main.queue_to_main.put({str("Rpoly"): [float(xvalue), float(rpoly)]})

            self.main.config_setup(device_dict, [("set_output", "OFF"), ("set_voltage", 0)])

            return rpoly

    def do_Rint(self, xvalue = -1, samples = 5, write_to_main = True):
        '''Does the Rint measurement'''
        device_dict = self.elmeter
        voltage_device = self.SMU2
        d = device_dict
        rint = 0
        config_commands = [("set_zero_check", "ON"), ("set_measure_current", ""), ("set_zero_check", "OFF")]
        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("Rint"):
                self.stop_everything()
                return
            self.main.config_setup(voltage_device, [("set_voltage", 0), ("set_complience", 50E-6)])  # config the 2410
            self.main.config_setup(device_dict, config_commands)  # config the elmeter
            self.main.change_value(voltage_device, "set_output", "ON") # Sets the output of the device to on

            rintsettings = self.main.main.default_dict["Rint_MinMax"]
            minvoltage = rintsettings[0]
            maxvoltage = rintsettings[1]
            steps = rintsettings[2]

            voltage_list = self.main.ramp_value(minvoltage, maxvoltage, steps)

            # Get to the first voltage and wait till steady state
            self.main.change_value(voltage_device, "set_voltage", minvoltage)
            if self.main.steady_state_check(device_dict, command="get_read", max_slope=1e-2, wait=0, samples=5, Rsq=0.3, check_complience=False):  # Is a dynamic waiting time for the measuremnt
                values_list = []
                past_volts = []
                for i, voltage in enumerate(voltage_list): # make all measurements for the Rint ramp
                    if not self.main.main.stop_measurement:
                        self.main.change_value(voltage_device, "set_voltage", voltage)
                        value = self.__do_simple_measurement("Rint_scan", device_dict, xvalue, samples, write_to_main=False)
                        values_list.append(float(value))
                        past_volts.append(float(voltage))
                        self.main.queue_to_main.put({"Rint_scan": [past_volts, values_list]})

                if not self.main.main.stop_measurement:
                    # Now make the linear fit for the ramp
                    slope, intercept, r_value, p_value, std_err = stats.linregress(voltage_list[2:], values_list[2:])
                    # TODO: make some comparision if it is ok, write this to a separate file etc.
                    rint = 1./slope
                    self.rintslopes.append([xvalue, rint, voltage_list, values_list ,slope, intercept, r_value, p_value, std_err]) # so everything is saved in the end
            else:
                self.main.queue_to_main.put({"MeasError": "Steady state could not be reached for the Rint measurement"})

        self.main.change_value(voltage_device, "set_voltage", 0)
        self.main.change_value(voltage_device, "set_output", "OFF")  # Sets the output of the device to off
        self.main.config_setup(device_dict, [("set_zero_check", "ON")])  # unconfig elmeter

        if write_to_main:  # Writes data to the main, or not
            self.main.measurement_data[str("Rint")][0] = np.append(self.main.measurement_data[str("Rint")][0],[float(xvalue)])
            self.main.measurement_data[str("Rint")][1] = np.append(self.main.measurement_data[str("Rint")][1],[float(rint)])
            self.main.queue_to_main.put({str("Rint"): [float(xvalue), float(rint)]})

        return rint

    def do_Idiel(self, xvalue = -1, samples = 5, write_to_main = True):
        '''Does the idiel measurement'''
        device_dict = self.SMU2
        #config_commands = [("set_zero_check", "ON"), ("set_measure_current", ""), ("set_zero_check", "OFF")]
        config_commands = [("set_source_voltage", ""), ("set_measure_current", ""), ("set_current_range", 2.0E-6), ("set_complience", 1.0E-6), ("set_voltage", "5.0"), ("set_output", "ON")]

        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("Idiel"):
                self.stop_everything()
                return
            self.main.config_setup(device_dict, config_commands) # config the elmeter
            if self.main.steady_state_check(device_dict, command="get_read", max_slope=1e-6, wait=0, samples=5, Rsq=0.5, check_complience=False): # Is a dynamic waiting time for the measuremnt
            #sleep(0.5) # Dynamic waiting time does not work here, idont know why
                value = self.__do_simple_measurement("Idiel", device_dict, xvalue, samples, write_to_main=write_to_main)
            else:
                value =  False
            #self.main.config_setup(device_dict, [("set_zero_check", "ON")])  # unconfig elmeter
            self.main.config_setup(device_dict, [("set_voltage", "0"), ("set_output", "OFF"), ("set_current_range", device_dict.get("default_current_range",10E6))])  # unconfig elmeter
            return value

    def do_Istrip(self, xvalue = -1, samples = 5, write_to_main = True):
        '''Does the istrip measurement'''
        device_dict = self.elmeter
        d=device_dict # alias for faster writing
        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("Istrip"):
                self.stop_everything()
                return
            config_commands = [("set_zero_check", "ON"), ("set_measure_current", ""), ("set_zero_check", "OFF")]
            self.main.config_setup(device_dict, config_commands)  # config the elmeter
            if self.main.steady_state_check(device_dict, command="get_read", max_slope=1e-6, wait=0, samples=2, Rsq=0.5, check_complience=False):  # Is a dynamic waiting time for the measuremnt
                value = self.__do_simple_measurement("Istrip", device_dict, xvalue, samples, write_to_main=write_to_main)
            else:
                value = False
            self.main.config_setup(device_dict, [("set_zero_check", "ON")])  # unconfig elmeter
            self.last_istrip_pad = xvalue
            return value

    def do_Idark(self, xvalue = -1, samples = 5, write_to_main = True):
        '''Does the idark measurement'''
        device_dict = self.bias_SMU
        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("Idark"):
                self.stop_everything()
                return
            if self.main.steady_state_check(device_dict, command="get_read_current", max_slope=1e-6, wait=0, samples=2, Rsq=0.5):  # Is a dynamic waiting time for the measuremnt
                value = self.__do_simple_measurement("Idark", device_dict, xvalue, samples, query="get_read_current", write_to_main=write_to_main)
            else:
                return False
            return value
        else:
            return None

    def do_Cint(self, xvalue = -1, samples = 5,  freqscan = False, write_to_main = True):
        '''Does the cint measurement'''
        device_dict = self.LCR_meter
        # Config the LCR to the correct freq of 1 MHz
        self.main.change_value(device_dict, "set_frequency", 1000000)
        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("Cint"):
                self.stop_everything()
                return
            sleep(0.2)  # Is need due to some stray capacitances which corrupt the measurement
            if self.main.steady_state_check(device_dict,  command="get_read",max_slope=1e-6, wait=0, samples=5,Rsq=0.5, check_complience=False):  # Is a dynamic waiting time for the measuremnt
                value = self.__do_simple_measurement("Cint", device_dict, xvalue, samples, write_to_main=not freqscan)
            else:
                return False
            return value

    def do_CintAC(self, xvalue= -1, samples=5, freqscan=False, write_to_main=True):
        '''Does the cint measurement on the AC strips'''
        device_dict = self.LCR_meter
        # Config the LCR to the correct freq of 1 MHz
        self.main.change_value(device_dict, "set_frequency", 1000000)
        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("CintAC"):
                self.stop_everything()
                return
            sleep(0.2) #Because fuck you thats why. (Brandbox to LCR meter)
            if self.main.steady_state_check(device_dict, command="get_read", max_slope=1e-6, wait=0, samples=2, Rsq=0.5,
                                         check_complience=False):  # Is a dynamic waiting time for the measuremnt
                value = self.__do_simple_measurement("CintAC", device_dict, xvalue, samples, write_to_main=not freqscan)
            else:
                return False
            return value

    def do_Cac(self, xvalue = -1, samples = 5, freqscan = False, write_to_main = True):
        '''Does the cac measurement'''
        device_dict = self.LCR_meter
        # Config the LCR to the correct freq of 1 kHz
        self.main.change_value(device_dict, "set_frequency", 1000)
        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("Cac"):
                self.stop_everything()
                return
            sleep(0.2) # Is need due to some stray capacitances which corrupt the measurement
            if self.main.steady_state_check(device_dict, command="get_read", max_slope=1e-6, wait=0, samples=5,Rsq=0.5, check_complience=False):  # Is a dynamic waiting time for the measuremnt
                value = self.__do_simple_measurement("Cac", device_dict, xvalue, samples, write_to_main=not freqscan)
            else: return False
            return value

    def do_Cback(self, xvalue = -1, samples = 5, freqscan = False, write_to_main = True):
        '''Does a capacitance measurement from one strip to the backside'''
        device_dict = self.LCR_meter
        # Config the LCR to the correct freq of 1 MHz
        self.main.change_value(device_dict, "set_frequency", 1000000)
        if not self.main.main.stop_measurement:
            if not self.switching.switch_to_measurement("Cback"):
                self.stop_everything()
                return
            sleep(0.2)  # Is need due to some stray capacitances which corrupt the measurement
            if self.main.steady_state_check(device_dict, command="get_read", max_slope=1e-6, wait=0, samples=5, Rsq=0.5, check_complience=False):  # Is a dynamic waiting time for the measuremnt
                value = self.__do_simple_measurement("Cback", device_dict, xvalue, samples, write_to_main=not freqscan)
            else: return 0
            return value
