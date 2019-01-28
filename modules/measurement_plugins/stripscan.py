# This file manages the stripscan measurements and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
from scipy import stats
sys.path.append('../modules')
from ..VisaConnectWizard import *
from ..utilities import *
l = logging.getLogger(__name__)

help = help_functions()
vcw = VisaConnectWizard.VisaConnectWizard()
trans = transformation()


class stripscan_class:

    def __init__(self, main_class):
        """
        This class takes only one parameter, the main class, in which all parameters must be prevalent. It further
        starts the actual stripscan measuremnt, no further action need to be taken

        :param main_class:
        """
        self.main = main_class
        self.switching = self.main.switching
        self.current_voltage = self.main.settings["Defaults"]["bias_voltage"]
        self.voltage_End = self.main.job_details["stripscan"]["EndVolt"]
        self.voltage_Start = self.main.job_details["stripscan"]["StartVolt"]
        self.voltage_steps = self.main.job_details["stripscan"]["Steps"]
        self.complience = self.main.job_details["stripscan"]["Complience"]
        self.bias_SMU = self.main.devices["IVSMU"]
        self.LCR_meter = self.main.devices["LCR"]
        self.SMU2 = self.main.devices["2410SMU"]
        self.discharge_SMU = self.main.devices["2410SMU"]
        self.discharge_switching = self.main.devices["temphum_controller"]
        self.elmeter = self.main.devices["Elmeter"]
        self.measurement_order = ["Istrip", "Rpoly", "Idark", "Cac", "Cint", "Cback", "Idiel", "Rint", "frequencyscan"]
        self.units = [("Istrip","current[A]"), ("Rpoly", "res[Ohm]"),
                      ("Idiel","current[A]"), ("Idark","current[A]"),
                      ("Rint", "res[Ohm]"), ("Cac", "cap[F]"),
                      ("Cint", "cap[F]"), ("Cback", "cap[F]")]
        self.strips = self.main.total_strips # now the program knows the total number of strips
        self.current_strip = self.main.main.default_dict["Defaults"]["current_strip"] # Current pad position of the table
        #self.T = self.main.main.default_dict["Defaults"]["T"]
        #self.V0 = self.main.main.default_dict["Defaults"]["V0"]
        self.height = self.main.main.default_dict["Defaults"]["height_movement"]
        self.samples = 3
        self.last_istrip_pad = -1 # Number of the last pad on which a I strip was conducted, important for rpoly
        self.T = self.main.main.default_dict["Defaults"]["trans_matrix"]
        self.V0 = self.main.main.default_dict["Defaults"]["V0"]
        self.job = self.main.job_details
        self.sensor_pad_data = self.main.pad_data[self.job["Project"]][self.job["Sensor"]]
        self.justlength = 24
        self.rintslopes = [] # here all values from the rint is stored


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

        if "stripscan" in self.main.job_details:
            if "frequencyscan" in self.main.job_details["stripscan"]:
                self.do_frequencyscan(self.main.job_details["stripscan"]["frequencyscan"]["Measurements"].keys(),
                                      # gets the measurements
                                      self.main.job_details["stripscan"]["frequencyscan"]["Strip"],
                                      # the strip which should be measured
                                      self.LCR_meter, 5,  # device and sample size
                                      self.main.job_details["stripscan"]["frequencyscan"]["StartFreq"],
                                      self.main.job_details["stripscan"]["frequencyscan"]["EndFreq"],
                                      self.main.job_details["stripscan"]["frequencyscan"]["FreqSteps"],
                                      self.main.job_details["stripscan"]["frequencyscan"]["MinVolt"])

        # Ramp down the voltage after stripscan

        # Discharge the capacitors in the decouple box

        # Switch to IV for correct biasing for ramp
        self.switching.switch_to_measurement("IV")  # correct bias is applied

        self.main.ramp_voltage(self.bias_SMU, "set_voltage", self.current_voltage, 0, self.voltage_steps, wait_time=0.3, complience=0.001)
        self.main.change_value(self.bias_SMU,"set_voltage", "0")
        self.main.change_value(self.bias_SMU, "set_output", "0")

        if not self.main.capacitor_discharge(self.discharge_SMU, self.discharge_switching, "set_terminal", "FRONT", do_anyway=True):
            self.stop_everything()

        #self.save_rint_slopes()y

    def stop_everything(self):
        """Stops the measurement
        A signal will be genereated and send to the event loops, which sets the statemachine to stop all measurements"""
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)

    def save_rint_slopes(self):
        # If a rint measurement was done save the data to a file
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

            # TODO: save the values to the file

            # xvalue, rint, voltage_list, values_list ,slope, intercept, r_value, p_value, std_err
            #for pad in self.rintslopes:
            #    string_to_write += self.rintslopes



            #self.main.write(file, string_to_write + "\n")

    def do_preparations_for_stripscan(self):
        """This function prepares the setup, like ramping the voltage and steady state check
        """
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
            self.current_voltage = self.main.main.default_dict["Defaults"]["bias_voltage"]
            self.stop_everything()

        #If everything works make steady state check
        else:
            if self.main.steady_state_check(self.bias_SMU, max_slope = 1e-6, wait = 0, samples = 3, Rsq = 0.5, complience=self.complience): # Is a dynamic waiting time for the measuremnts
                self.current_voltage = self.main.main.default_dict["Defaults"]["bias_voltage"]
                if self.main.check_complience(self.bias_SMU, self.complience): #if complience is reached stop everything
                    self.stop_everything()
            else:
                self.stop_everything()

        # Move the table up again
        self.main.table.move_up(self.height)

    def do_singlestrip(self, job):
        """This function conducts the measurements defined for a single strip measurement"""
        self.do_preparations_for_stripscan()

        if not self.main.stop_measurement():
            measurement_header = "Pad".ljust(self.justlength)  # indicates the measuremnt
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
                    self.main.table.move_to_strip(self.sensor_pad_data, int(job["Strip"] - 1), trans, self.T, self.V0, self.height)
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

    @help.timeit
    def do_stripscan(self):
        '''This function manages all stripscan measurements, also the frequency scan things
        Its ment to be used only once during the initiatior of the class'''

        self.do_preparations_for_stripscan()


        if not self.main.stop_measurement():
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
            for current_strip in range(1, int(self.strips)): # Loop over all strips
                if not self.main.stop_measurement(): # Prevents that empty entries will be written to file after aborting the measurement
                    self.current_strip = current_strip
                    #results.append({}) # Adds an empty dict to the results for the bad strip detection
                    start = time.time()  # start timer for a strip measurement
                    if self.main.save_data:
                        self.main.write(self.main.measurement_files["stripscan"], str(self.sensor_pad_data["data"][current_strip-1][0]).ljust(self.justlength))  # writes the strip to the file
                    for measurement in self.measurement_order:
                        if measurement in self.main.job_details["stripscan"] and not self.main.main.stop_measurement: # looks if measurement should be done

                            # Now conduct the measurement
                            # But first check if this strip should be measured with this specific measurement
                            if current_strip in self.main.job_details["stripscan"][measurement]["strip_list"]:
                                self.main.table.move_to_strip(self.sensor_pad_data, self.current_strip-1, trans, self.T, self.V0, self.height)

                                if not self.main.stop_measurement() and not self.main.check_complience(self.bias_SMU, self.complience):
                                    value = getattr(self, "do_"+measurement)(current_strip, self.samples)

                                    # In the end do a quick bad strip detection
                                    #badstrip = self.main.main.analysis.do_online_singlestrip_analysis((measurement, value))
                                    badstrip = False
                                    if badstrip:
                                        l.info("Badstrip detected at strip: " + str(current_strip) + " Error code: " + str(badstrip))
                                        self.main.queue_to_main.put({"Thresholderror": "Badstrip detected at strip: " + str(current_strip) + " Error code: " + str(badstrip)})
                                        # Add the bad strip to the list of bad strips
                                        if str(current_strip) in self.main.badstrip_dict:
                                            self.main.badstrip_dict[str(current_strip)].update(badstrip)
                                        else:
                                            self.main.badstrip_dict[str(current_strip)] = badstrip
                                            self.main.main.default_dict["Defaults"]["Bad_strips"] += 1 # increment the counter


                                    # Write this to the file
                                    if value and self.main.save_data:
                                        self.main.write(self.main.measurement_files["stripscan"], str(float(value)).ljust(self.justlength)) # Writes the value to the file
                            else:
                                if self.main.save_data:
                                    self.main.write(self.main.measurement_files["stripscan"], "--".ljust(self.justlength)) # Writes nothing if no value is aquired

                    if not self.main.stop_measurement():
                        # After all measurements are conducted write the environment variables to the file
                        if self.main.job_details.get("enviroment", False):
                            string_to_write = str(self.main.main.temperatur_history[-1]).ljust(self.justlength) + str(self.main.main.humidity_history[-1]).ljust(self.justlength)
                        self.main.write(self.main.measurement_files["stripscan"], string_to_write)

                        # Write new line
                        if self.main.save_data:
                            self.main.write(self.main.measurement_files["stripscan"], "\n")

                        # Do the bad strip detection


                    if abs(float(start - time.time())) > 1.: # Rejects all measurements which are to short to be real measurements
                        delta = float(self.main.main.default_dict["Defaults"]["strip_scan_time"]) + abs(start - time.time())
                        self.main.main.default_dict["Defaults"]["strip_scan_time"] = str(delta / 2.)  # updates the time for strip measurement


    def do_frequencyscan(self, measurement_obj, strip, device_dict, samples, startfreq, endfreq, steps, voltage):
        '''This function performes a frequency scan of the lcr meter and at each step it executes a LIST of mesaurement'''

        self.do_preparations_for_stripscan()

        if not self.main.stop_measurement():
            # Generate frequency list
            freq_list = self.main.ramp_value_log10(startfreq, endfreq, steps)

            # Create a measurement file for the frequency scan, (per strip)
            if self.main.save_data:
                filepath = self.main.job_details["Filepath"]
                filename = "fre_strip_" + str(int(strip)) + "_" + self.main.job_details["Filename"]

                header = self.main.job_details["Header"]
                header += " #AC Voltage: " + str(voltage) + "\n"
                header += " #Measured strip: " + str(int(strip)) + "\n\n"
                for meas in measurement_obj:
                    func_name = str(meas)
                    header += str(func_name) + "\t\t\t\t"
                header += "\n"

                for meas in measurement_obj: # adds the units header
                    header += "frequency [Hz]".ljust(self.justlength) +  "capacitance [F]".ljust(self.justlength)
                header += "\n"

                file = self.main.create_data_file(header, filepath, filename)

            # Set the LCR amplitude voltage for measurement
            self.main.change_value(self.LCR_meter, "set_voltage", str(voltage))

            # Moves to strip
            self.main.table.move_to_strip(self.sensor_pad_data, int(self.job["stripscan"]["frequencyscan"]["Strip"])-1, trans, self.T, self.V0, self.height)

            for freq in freq_list: #does the loop over the frequencies
                if not self.main.stop_measurement(): #stops the loop if shutdown is necessary
                    self.main.change_value(self.LCR_meter, "set_frequency", str(freq))
                    value = []
                    for i, meas in enumerate(measurement_obj):
                        func_name = str(meas)
                        value.append(getattr(self, "do_" + func_name)(freq, samples=samples, freqscan=True)) #calls the measurement
                        # Append the data to the data array and sends it to the main as frequency scan measurement
                        if not self.main.stop_measurement():
                            self.main.measurement_data[func_name + "_scan"][0] = np.append(self.main.measurement_data[func_name + "_scan"][0],[float(freq)])
                            self.main.measurement_data[func_name + "_scan"][1] = np.append(self.main.measurement_data[func_name + "_scan"][1], [float(value[i])])
                            self.main.queue_to_main.put({func_name + "_scan": [float(freq), float(value[i])]})

                    if self.main.save_data:
                        string_to_write = ""
                        for val in value:
                            string_to_write += str(freq).ljust(self.justlength) + str(val).ljust(self.justlength)
                        self.main.write(file, string_to_write + "\n")
                    else:
                        break


    def __do_simple_measurement(self, str_name, device, xvalue = -1, samples = 5, write_to_main = True):
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
            values.append(float(str(vcw.query(device, device["Read"])).split(",")[0]))
        value = sum(values) / len(values)  # averaging

        self.main.measurement_data[str(str_name)][0] = np.append(self.main.measurement_data[str(str_name)][0],[float(xvalue)])
        self.main.measurement_data[str(str_name)][1] = np.append(self.main.measurement_data[str(str_name)][1],[float(value)])

        if write_to_main: # Writes data to the main, or not
            self.main.queue_to_main.put({str(str_name): [float(xvalue), float(value)]})

        return value

    def do_Rpoly(self,  xvalue = -1, samples = 5, write_to_main = True):
        '''Does the rpoly measurement'''
        device_dict = self.SMU2
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("Rpoly"):
                self.stop_everything()
                return
            voltage = -1.
            self.main.config_setup(device_dict, [("set_source_voltage", ""), ("set_measure_current", ""),("set_voltage", voltage), ("set_complience", 90E-6), ("set_output", "ON")])  # config the 2410 for 1V bias on bias and DC pad
            self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=3, Rsq=0.5, check_complience=False)  # Is a dynamic waiting time for the measuremnt
            value = self.__do_simple_measurement("Rpoly", device_dict, xvalue, samples, write_to_main=False) # This value is istrip +
            # Now subtract the Istrip
            if self.last_istrip_pad == xvalue:
                #todo: richtiger wert nehemen
                Istrip = self.main.measurement_data["Istrip"][1][-1]
            else:# If no Istrip then aquire a value
                l.info("No Istrip value for Rpoly calculation could be found, Istrip measurement will be conducted on strip {}".format(int(xvalue)))
                Istrip = self.do_Istrip(xvalue, samples, False)
                # Iges = Ipoly+Istrip
            value = float(value)-float(Istrip) # corrected current value

            rpoly = voltage/float(value)

            if write_to_main:  # Writes data to the main, or not
                self.main.measurement_data[str("Rpoly")][0] = np.append(self.main.measurement_data[str("Rpoly")][0],[float(xvalue)])
                self.main.measurement_data[str("Rpoly")][1] = np.append(self.main.measurement_data[str("Rpoly")][1],[float(rpoly)])
                self.main.queue_to_main.put({str("Rpoly"): [float(xvalue), float(rpoly)]})

            self.main.config_setup(device_dict, [("set_output", "OFF")])

            return rpoly

    def do_Rint(self, xvalue = -1, samples = 5, write_to_main = True):
        '''Does the Rint measurement'''
        device_dict = self.elmeter
        voltage_device = self.SMU2
        d = device_dict
        rint = 0
        config_commands = [("set_zero_check", "ON"), ("set_measure_current", ""), ("set_zero_check", "OFF")]
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("Rint"):
                self.stop_everything()
                return
            self.main.config_setup(voltage_device, [("set_voltage", 0), ("set_complience", 50E-6)])  # config the 2410
            self.main.config_setup(device_dict, config_commands)  # config the elmeter
            self.main.change_value(voltage_device, "set_output", "ON") # Sets the output of the device to on

            rintsettings = self.main.main.default_dict["Defaults"]["Rint_MinMax"]
            minvoltage = rintsettings[0]
            maxvoltage = rintsettings[1]
            steps = rintsettings[2]

            voltage_list = self.main.ramp_value(minvoltage, maxvoltage, steps)

            # Get to the first voltage and wait till steady state
            self.main.change_value(voltage_device, "set_voltage", minvoltage)
            if True or self.main.steady_state_check(device_dict, max_slope=1e-2, wait=0, samples=5, Rsq=0.3, check_complience=False):  # Is a dynamic waiting time for the measuremnt
                values_list = []
                past_volts = []
                for i, voltage in enumerate(voltage_list): # make all measurements for the Rint ramp
                    if not self.main.stop_measurement():
                        self.main.change_value(voltage_device, "set_voltage", voltage)
                        value = self.__do_simple_measurement("Rint_scan", device_dict, xvalue, samples, write_to_main=False)
                        values_list.append(float(value))
                        past_volts.append(float(voltage))
                        self.main.queue_to_main.put({"Rint_scan": [past_volts, values_list]})

                if not self.main.stop_measurement():
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
        config_commands = [("set_voltage", "5.0"), ("set_output", "ON")]

        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("Idiel"):
                self.stop_everything()
                return
            self.main.config_setup(device_dict, config_commands) # config the elmeter
            self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=2, Rsq=0.5, check_complience=False)  # Is a dynamic waiting time for the measuremnt

            value = self.__do_simple_measurement("Idiel", device_dict, xvalue, samples, write_to_main=write_to_main)
            #self.main.config_setup(device_dict, [("set_zero_check", "ON")])  # unconfig elmeter
            self.main.config_setup(device_dict, [("set_voltage", "0"), ("set_output", "OFF")])  # unconfig elmeter

            return value

    def do_Istrip(self, xvalue = -1, samples = 5, write_to_main = True):
        '''Does the istrip measurement'''
        device_dict = self.elmeter
        d=device_dict # alias for faster writing
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("Istrip"):
                self.stop_everything()
                return
            config_commands = [("set_zero_check", "ON"), ("set_measure_current", ""), ("set_zero_check", "OFF")]
            self.main.config_setup(device_dict, config_commands)  # config the elmeter
            self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=2, Rsq=0.5, check_complience=False)  # Is a dynamic waiting time for the measuremnt

            value = self.__do_simple_measurement("Istrip", device_dict, xvalue, samples, write_to_main=write_to_main)
            self.main.config_setup(device_dict, [("set_zero_check", "ON")])  # unconfig elmeter
            self.last_istrip_pad = xvalue
            return value

    def do_Idark(self, xvalue = -1, samples = 5, write_to_main = True):
        '''Does the idark measurement'''
        device_dict = self.bias_SMU
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("Idark"):
                self.stop_everything()
                return
            self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=2, Rsq=0.5)  # Is a dynamic waiting time for the measuremnt

            value = self.__do_simple_measurement("Idark", device_dict, xvalue, samples, write_to_main=write_to_main)
            return value
        else:
            return None

    def do_Cint(self, xvalue = -1, samples = 5,  freqscan = False, write_to_main = True):
        '''Does the cint measurement'''
        device_dict = self.LCR_meter
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("Cint"):
                self.stop_everything()
                return
            sleep(0.2)  # Is need due to some stray capacitances which corrupt the measurement
            self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=5,Rsq=0.5, check_complience=False)  # Is a dynamic waiting time for the measuremnt
            value = self.__do_simple_measurement("Cint", device_dict, xvalue, samples, write_to_main=not freqscan)
            return value

    def do_CintAC(self, xvalue= -1, samples=5, freqscan=False, write_to_main=True):
        '''Does the cint measurement on the AC strips'''
        device_dict = self.LCR_meter
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("CintAC"):
                self.stop_everything()
                return
            sleep(0.2) #Because fuck you thats why. (Brandbox to LCR meter)
            self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=2, Rsq=0.5,
                                         check_complience=False)  # Is a dynamic waiting time for the measuremnt
            value = self.__do_simple_measurement("CintAC", device_dict, xvalue, samples, write_to_main=not freqscan)
            return value

    def do_Cac(self, xvalue = -1, samples = 5, freqscan = False, write_to_main = True):
        '''Does the cac measurement'''
        device_dict = self.LCR_meter
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("Cac"):
                self.stop_everything()
                return
            sleep(0.2) # Is need due to some stray capacitances which corrupt the measurement
            self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=5,Rsq=0.5, check_complience=False)  # Is a dynamic waiting time for the measuremnt
            value = self.__do_simple_measurement("Cac", device_dict, xvalue, samples, write_to_main=not freqscan)
            return value

    def do_Cback(self, xvalue = -1, samples = 5, freqscan = False, write_to_main = True):
        '''Does a capacitance measurement from one strip to the backside'''
        device_dict = self.LCR_meter
        if not self.main.stop_measurement():
            if not self.switching.switch_to_measurement("Cback"):
                self.stop_everything()
                return
            sleep(0.2)  # Is need due to some stray capacitances which corrupt the measurement
            self.main.steady_state_check(device_dict, max_slope=1e-6, wait=0, samples=5, Rsq=0.5, check_complience=False)  # Is a dynamic waiting time for the measuremnt
            value = self.__do_simple_measurement("Cback", device_dict, xvalue, samples, write_to_main=not freqscan)
            return value
