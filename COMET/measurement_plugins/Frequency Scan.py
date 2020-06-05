# This file manages the stripscan measurements and it is intended to be used as a plugin for the QTC software

import logging
import sys
import numpy as np
from time import sleep

sys.path.append("../COMET")
try:
    from .IVCV import IVCV_class
    from .Stripscan import Stripscan_class
except:
    from .stripscan import Stripscan_class


class FrequencyScan_class(Stripscan_class):
    def __init__(self, main_class):
        """
        This class takes only one parameter, the main class, in which all parameters must be prevalent. It further
        starts the actual stripscan measurement, no further action need to be taken

        :param main_class:
        """
        super(FrequencyScan_class, self).__init__(main_class)
        self.log = logging.getLogger(__name__)
        self.main = main_class
        self.job = self.main.job_details["Frequency Scan"]
        self.job_details = self.main.job_details
        self.general_options = self.job["General"]
        self.measurements = self.job.copy()
        self.measurements.pop("General")

        # Define a few values, so inital ramp up values etc.
        # These varaibles are used for the stripscan preparations!!!
        self.voltage_End = self.general_options["Start Voltage [V]"]
        self.voltage_Start = 0
        self.voltage_steps = 10
        self.compliance = self.general_options["Compliance [uA]"]

        # Voltage step list
        self.voltage_ramp = self.ramp_value(
            self.general_options["Start Voltage [V]"],
            self.general_options["End Voltage [V]"],
            self.general_options["Voltage Step [V]"],
        )

    def run(self):
        """This function conducts the measurements """
        self.do_preparations_for_stripscan(do_cal=False, measurement="Frequency Scan")

        # Do the voltage ramp
        self.numVSteps = len(self.voltage_ramp)
        self.numMSteps = len(self.measurements)
        for iter, volt in enumerate(self.voltage_ramp):
            self.change_value(self.bias_SMU, "set_voltage", str(volt))
            self.main.framework["Configs"]["config"]["settings"]["bias_voltage"] = volt
            if self.steady_state_check(
                self.bias_SMU,
                command="get_read_current",
                max_slope=1e-8,
                wait=0.05,
                samples=7,
                Rsq=0.8,
                compliance=self.compliance,
            ):  # Is a dynamic waiting time for the measuremnts
                self.current_voltage = self.main.framework["Configs"]["config"][
                    "settings"
                ]["bias_voltage"]
                if self.check_compliance(
                    self.bias_SMU, self.compliance
                ):  # if compliance is reached stop everything
                    self.stop_everything()
            else:
                self.stop_everything()
            self.do_frequencyscan(iter + 1, volt)

        try:
            for i, func_name in enumerate(self.measurements.keys()):
                self.write_to_file(
                    self.main.measurement_files["Frequency Scan"],
                    self.voltage_ramp,
                    self.main.measurement_data[func_name + "_freq"][0],
                    self.main.measurement_data[func_name + "_freq"][1],
                )
                if i > 0:
                    self.log.critical(
                        "ASCII output cannot cope with multiple data structures, output may be compromised."
                    )
        except Exception as err:
            self.log.error(
                "Writting to ASCII file failed due to an error: {}".format(err)
            )

        # self.write_to_json()

        self.clean_up()

    def write_to_json(self):
        """Writes the individual data arrays to stand alone json files for easy plotting"""
        for i, func_name in enumerate(self.measurements.keys()):  # Measuremnts
            data_to_dump = {}
            for j, data in enumerate(
                zip(
                    self.main.measurement_data[func_name + "_freq"][0],
                    self.main.measurement_data[func_name + "_freq"][1],
                )
            ):  # Voltage steps
                data_to_dump["{}V".format(self.voltage_ramp[j])] = [data[0], data[1]]
            new_name = {
                "Filename": self.job_details["Filename"] + "_{}".format(func_name)
            }
            details = self.job_details.copy()
            details.update(new_name)
            self.main.save_data_as(
                "json",
                details,
                data=data_to_dump,
                xunits=("frequency", "Hz"),
                yunits=("capacitance", "F"),
            )

    def do_frequencyscan(self, iteration, voltage):
        """This function performes a frequency scan of the lcr meter and at each step it executes a LIST of mesaurement"""

        # Loop over all measurements
        step = 0
        for func_name, measurement in self.measurements.items():
            if not self.main.event_loop.stop_all_measurements_query():
                step += 1
                start_freq = measurement["Start Freq [Hz]"]
                end_freq = measurement["End Freq [Hz]"]
                step_freq = measurement["Steps"]
                LCR_volt = measurement["Amplitude [mV]"] * 0.001
                strip = measurement.get("Strip [#]", -1)

                # Generate frequency list
                freq_list = list(self.ramp_value_log10(start_freq, end_freq, step_freq))
                # Construct results array
                self.xvalues = np.zeros(len(freq_list))
                self.yvalues = np.zeros(len(freq_list))

                # Set the LCR amplitude voltage for measurement
                self.change_value(self.LCR_meter, "set_voltage", str(LCR_volt))

                # Move to strip if necessary
                if (
                    strip > 0
                    and self.main.framework["Configs"]["config"]["settings"][
                        "Alignment"
                    ]
                ):
                    if not self.main.table.move_to_strip(
                        self.sensor_pad_data,
                        strip,
                        self.trans,
                        self.T,
                        self.V0,
                        self.height,
                    ):
                        self.log.error("Could not move to strip {}".format(strip))
                        break
                elif not self.main.framework["Configs"]["config"]["settings"][
                    "Alignment"
                ]:
                    self.log.critical(
                        "No alignment done, conducting frequency scan without moving table!"
                    )

                for i, freq in enumerate(
                    list(freq_list)
                ):  # does the loop over the frequencies
                    if (
                        not self.main.event_loop.stop_all_measurements_query()
                    ):  # stops the loop if shutdown is necessary
                        self.main.framework["Configs"]["config"]["settings"][
                            "progress"
                        ] = (i + 1) / len(freq_list)
                        yvalue = getattr(self, "do_" + func_name)(
                            strip,
                            samples=self.samples,
                            freqscan=True,
                            frequency=freq,
                            write_to_main=False,
                        )  # calls the measurement
                        self.yvalues[i] = (
                            yvalue[0] if isinstance(yvalue, np.ndarray) else yvalue
                        )
                        self.xvalues[i] = float(freq)

                # Append the data to the data array and sends it to the main as frequency scan measurement
                if not self.main.event_loop.stop_all_measurements_query():
                    if self.main.measurement_data[func_name + "_freq"][0][0]:
                        self.main.measurement_data[func_name + "_freq"][0] = np.vstack(
                            [
                                self.main.measurement_data[func_name + "_freq"][0],
                                self.xvalues,
                            ]
                        )
                        self.main.measurement_data[func_name + "_freq"][1] = np.vstack(
                            [
                                self.main.measurement_data[func_name + "_freq"][1],
                                self.yvalues,
                            ]
                        )
                    else:
                        self.main.measurement_data[func_name + "_freq"][
                            0
                        ] = self.xvalues
                        self.main.measurement_data[func_name + "_freq"][
                            1
                        ] = self.yvalues

                    self.main.queue_to_main.put(
                        {func_name + "_freq": [self.xvalues, self.yvalues]}
                    )

    def write_to_file(self, file, voltages, xvalues, yvalues):
        """
        Writes data to the ascii file
        """
        # Check if length of voltages matches the length of data array
        if len(xvalues) == len(yvalues):
            data = np.array([xvalues, yvalues])
            # data = np.transpose(data)
            # Write voltage header for each measurement first the voltages
            self.main.write(
                file,
                ""
                + "".join(
                    [format(el, "<{}".format(self.justlength * 2)) for el in voltages]
                )
                + "\n",
            )
            # Then the Units
            self.main.write(
                file,
                "".join(
                    [
                        format(
                            "frequency[Hz]{}capacitance[F]".format(
                                " " * (self.justlength - 7)
                            ),
                            "<{}".format(self.justlength * 2),
                        )
                        for x in range(len(voltages))
                    ]
                )
                + "\n",
            )
            try:
                for i in range(len(data[0, 0, :])):  # For multidimensional data
                    freq = [
                        format(time, "<{}".format(self.justlength))
                        for time in data[:, :, i][0]
                    ]
                    cap = [
                        format(curr, "<{}".format(self.justlength))
                        for curr in data[:, :, i][1]
                    ]
                    final = "".join([t + c for t, c in zip(freq, cap)])
                    self.main.write(file, final + "\n")
            except:
                freq = [format(time, "<{}".format(self.justlength)) for time in data[0]]
                cap = [format(curr, "<{}".format(self.justlength)) for curr in data[1]]
                final = "".join([t + c + "\n" for t, c in zip(freq, cap)])
                self.main.write(file, final + "\n")
        else:
            self.log.error(
                "Length of results array are non matching, abort storing data to file"
            )

    def do_CV(
        self,
        xvalue=-1,
        samples=5,
        freqscan=False,
        write_to_main=True,
        alternative_switching=False,
        frequency=1000,
    ):
        """Does the cac measurement"""
        device_dict = self.LCR_meter
        # Config the LCR to the correct freq of 1 kHz
        self.change_value(device_dict, "set_frequency", frequency)
        if not self.main.event_loop.stop_all_measurements_query():
            if not self.switching.switch_to_measurement("CV"):
                self.stop_everything()
                return
            sleep(
                5.0
            )  # Is need due to some stray capacitances which corrupt the measurement
            if self.steady_state_check(
                device_dict,
                command="get_read",
                max_slope=1e-6,
                wait=0.0,
                samples=2,
                Rsq=0.5,
                check_compliance=False,
            ):  # Is a dynamic waiting time for the measuremnt
                value = self.do_measurement(
                    "CV",
                    device_dict,
                    xvalue,
                    samples,
                    write_to_main=not freqscan,
                    correction=0,
                )
            else:
                return False

            return value

    def do_measurement(
        self,
        name,
        device,
        xvalue=-1,
        samples=5,
        write_to_main=True,
        query="get_read",
        apply_to=None,
        correction=None,
    ):
        """
         Does a simple measurement - really simple. Only acquire some values and build the mean of it

        :param name: What measurement is to be conducetd, if you pass a list, values returned, must be the same shape, other wise error will occure
        :param device: Which device schould be used
        :param xvalue: Which strip we are on, -1 means arbitrary
        :param samples: How many samples should be taken
        :param write_to_main: Writes the value back to the main loop
        :param query: what query should be used
        :param apply_to: data array will be given to a function for further calculations
        :param correction: single value or list of values subtracted to the resulting solution
        :return: Returns the mean of all aquired values
        """
        # Do some averaging over values
        values = []
        command = self.main.build_command(device, query)
        for i in range(samples):  # takes samples
            values.append(self.vcw.query(device, command))
        values = np.array(
            list(map(lambda x: x.split(device.get("separator", ",")), values)),
            dtype=float,
        )
        values = np.mean(values, axis=0)

        # Apply correction values
        if isinstance(correction, list) or isinstance(correction, tuple):
            for i, val in enumerate(correction):
                values[i] -= val
        elif isinstance(correction, float) or isinstance(correction, int):
            values[0] -= correction

        if apply_to:
            # Only a single float or int are allowed as returns
            value = apply_to(values)
        elif values.shape == (1,) or isinstance(values, float):
            value = values
        else:
            value = values[0]

        if write_to_main:  # Writes data to the main, or not
            if isinstance(name, str):
                self.main.measurement_data[str(name)][0][self.strip_iter] = float(
                    xvalue
                )
                self.main.measurement_data[str(name)][1][self.strip_iter] = float(value)
                self.main.queue_to_main.put({str(name): [float(xvalue), float(value)]})
            elif isinstance(name, list) or isinstance(name, tuple):
                try:
                    for i, sub in enumerate(name):
                        self.main.measurement_data[str(sub)][0][
                            self.strip_iter
                        ] = float(xvalue)
                        self.main.measurement_data[str(sub)][1][
                            self.strip_iter
                        ] = float(values[i])
                        self.main.queue_to_main.put(
                            {str(sub): [float(xvalue), float(values[i])]}
                        )
                except IndexError as err:
                    self.log.error(
                        "An error happened during values indexing in multi value return",
                        exc_info=True,
                    )

        return values
