# This file conducts a full test on the KIT Test Card nearly automatically

import logging
import sys

sys.path.append("../COMET")
from time import time, sleep
import time
from ..utilities import transformation, force_plot_update
from .forge_tools import tools
import numpy as np
from scipy import stats


class QTCTESTSYSTEM_class(tools):
    def __init__(self, main_class):
        """
        This class can conduct a stripscan. Furthermore, it is baseclass for shortend stripscan measurements like
        singlestrip and freqquencyscan. These measurements, in principal do the same like stripscan but only on one
        strip. Therefore, we can derive.

        :param main_class:
        """
        self.main = main_class
        super(QTCTESTSYSTEM_class, self).__init__(self.main.framework, self.main)
        self.log = logging.getLogger(__name__)

        # Aux. classes
        self.trans = transformation()
        self.vcw = self.main.framework["VCW"]
        self.switching = self.main.switching

        # These are generall parameters which can either be changed here or in the settings in the optional parameter seen above
        self.device_configs = {
            # Devices Configs
            "BiasSMU": "BiasSMU",
            "LCRMeter": "LCRMeter",
            "DischargeSMU": "DischargeSMU",
            "Switching": "temphum_controller",
            "Elmeter": "Elektrometer",
            "SMU2": "DischargeSMU",
            # Commands Configs
            "Discharge": ("set_terminal", "FRONT"),
            "OutputON": ("set_output", "1"),
            "OutputOFF": ("set_output", "0"),
            "GetReadSMU": "get_read",  # This read can be a single current read or current, voltage pair
            "GetReadLCR": "get_read",
            "GetReadSMU2": "get_read",
            "GetReadElmeter": "get_read",
            # General Configs for the measurement
            "BaseConfig": [],
            "IstripConfig": [],
            "IdielConfig": [],
            "IdarkConfig": [],
            "RpolyConfig": [],
            "RintConfig": [],
            "CacConfig": [],
            "CintConfig": [],
        }

        self.log.info("Acquiring devices for QTC test measurements...")
        self.discharge_SMU = None
        self.bias_SMU = None
        self.LCR_meter = None
        self.discharge_switching = None
        self.elmeter = None
        self.SMU2 = None
        try:
            self.bias_SMU = self.main.devices[self.device_configs["BiasSMU"]]
            self.LCR_meter = self.main.devices[self.device_configs["LCRMeter"]]
            self.discharge_SMU = self.main.devices[self.device_configs["DischargeSMU"]]
            self.elmeter = self.main.devices[self.device_configs["Elmeter"]]
            self.SMU2 = self.main.devices[self.device_configs["SMU2"]]
            self.discharge_dev = self.main.devices[self.device_configs["Switching"]]
            self.discharge_switching = self.main.devices[
                self.device_configs["Switching"]
            ]
            self.testmode = False
        except KeyError as valErr:
            self.log.critical(
                "One or more devices could not be found for the QTC test measurements. Error: {}".format(
                    valErr
                )
            )
            self.testmode = True

        # Misc.
        self.job = self.main.job_details
        self.sensor_pad_data = (
            self.main.framework["Configs"]["additional_files"]["Pad_files"]
            .get("KIT Test Card", {})
            .get("KIT Test Card", None)
        )
        self.height = 3000  # 5 mm height movement
        self.T = self.main.framework["Configs"]["config"]["settings"]["trans_matrix"]
        self.V0 = self.main.framework["Configs"]["config"]["settings"]["V0"]

        self.samples = 5 # The amount of samples each measurement must have
        self.subsamples = 1  # Number of samples for filtering
        self.do_IV = False # If a chuck IV should be done or not
        self.T = self.main.framework["Configs"]["config"]["settings"].get(
            "trans_matrix", None
        )
        self.V0 = self.main.framework["Configs"]["config"]["settings"].get("V0", None)
        self.justlength = 24
        self.current_voltage = self.main.framework["Configs"]["config"]["settings"].get(
            "bias_voltage", 0
        )
        self.cal_to = {"Cac": 1000, "Cint": 1000000, "CV": 1000}  # Hz
        self.open_corrections = {}
        self.progress = 0

        # Data arrays
        self.data = {
            "Switching": [
                ("Chuckleakage", "IV", self.bias_SMU),
                ("Cacempty", "Cac", self.LCR_meter),
                ("Cintempty", "Cint", self.LCR_meter),
                ("Rpolyempty", "Rpoly", self.SMU2),
                ("Rintempty", "Rint", self.elmeter),
                ("Idielempty", "Idiel", self.SMU2),
                ("CVempty", "CV", self.LCR_meter),
                ("R1", "Rpoly", self.SMU2),
                ("R2", "Rint", self.elmeter),
                ("C1", "Cac", self.LCR_meter),
                ("C2", "Cint", self.LCR_meter),

            ],
            "Empty": {
                "Chuckleakage": np.zeros(self.samples),
                "Cacempty": np.zeros(self.samples),
                "Cintempty": np.zeros(self.samples),
                "Rpolyempty": np.zeros(self.samples),
                "Rintempty": np.zeros(self.samples),
                "Idielempty": np.zeros(self.samples),
                "CVempty": np.zeros(self.samples),
            },
            "units": {
                "Chuckleakage": "A",
                "Cacempty": "F",
                "Cintempty": "F",
                "Rpolyempty": "A",
                "Rintempty": "A",
                "Idielempty": "A",
                "CVempty": "F",
                "R1": "Ohm",
                "R2": "Ohm",
                "C1": "F",
                "C2": "F",
            },
            "TestCard": {
                "R1": np.zeros(self.samples),
                "R2": np.zeros(self.samples),
                "C1": np.zeros(self.samples),
                "C2": np.zeros(self.samples),
            },
        }

        # Vars for testsystem and GUI
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"] = {}
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "proceed"
        ] = False
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "text"
        ] = "This is the QTC test, init text."
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "currenttest"
        ] = "None"
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "overallprogress"
        ] = 0
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "partialprogress"
        ] = 0
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "data"
        ] = self.data
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "branch"
        ] = None

        if "Rint_MinMax" not in self.main.framework["Configs"]["config"]["settings"]:
            self.main.framework["Configs"]["config"]["settings"]["Rint_MinMax"] = [
                -1.0,
                1.0,
                0.1,
            ]
            self.log.warning(
                "No Rint boundaries given, defaulting to [-1.,1.,0.1]. Consider adding it to your settings"
            )

        # Check if alignment is present or not, if not stop measurement
        if (
            not self.main.framework["Configs"]["config"]["settings"].get(
                "Alignment", False
            )
            or not isinstance(self.T, np.ndarray)
            or not self.sensor_pad_data
        ):
            self.log.error(
                "Alignment is missing. Only non table critical measurements will be conducted!"
            )
            self.validalignment = False
        else:
            self.validalignment = True

        self.log = logging.getLogger(__name__)
        self.main.queue_to_main.put({"INFO": "Initialization of Setup test finished."})

    def run(self):
        """Does all the testing"""

        # Do device empty tests - Do switching uncontacted and do self.samples measurements
        if not self.testmode:
            self.main.table.move_down(1000.)
            if not self.capacitor_discharge(
                    self.discharge_SMU,
                    self.discharge_dev,
                    *self.device_configs["Discharge"],
                    do_anyway=True
            ):
                self.stop_everything()
            self.perform_open_correction(self.LCR_meter, self.cal_to, count=50)
            self.empty_measurements()
            self.main.table.move_up(1000.)

            # Do the probe card measurements - Contact the probe card and measurer the KIT resistors and capacitors
            if self.validalignment:
                self.test_card_measurements()

            # Save the data to an ASCII/JSON file
            self.save_results()
        else:
            self.empty_measurements_test()

    def empty_measurements(self):
        """Does all the empty measurements"""

        # DO loop
        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "branch"
        ] = "Empty"
        for j, meas in enumerate(list(self.data["Empty"].keys())):

            if self.main.event_loop.stop_all_measurements_query():
                break # If the stop signal was send

            # Get the necessary data
            self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                "overallprogress"
            ] = (j+1) / len(list(self.data["Empty"].keys()))
            self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                "currenttest"
            ] = meas
            idx = [k[0] for k in self.data["Switching"]].index(meas)
            self.switching.switch_to_measurement(self.data["Switching"][idx][1])
            command = self.main.build_command(
                self.data["Switching"][idx][2], "get_read"
            )

            # Check if not the IVempty measurement######################################################################
            if meas == "IVempty" and self.do_IV:

                set_voltage_0 = self.main.build_command(
                    self.data["Switching"][idx][2], ("set_voltage", "0")
                )
                self.vcw.write(self.data["Switching"][idx][2], set_voltage_0)

                outputon = self.main.build_command(
                    self.data["Switching"][idx][2], ("set_output", "1")
                )
                self.vcw.write(self.data["Switching"][idx][2], outputon)

                # Ramping up
                for i in range(0, -1020, -20):
                    set_voltage = self.main.build_command(
                        self.data["Switching"][idx][2], ("set_voltage", "{}".format(i))
                    )
                    self.vcw.write(self.data["Switching"][idx][2], set_voltage)
                    sleep(0.1)
                    value = self.query_values(idx, command, self.subsamples)
                    self.data["Empty"][meas][i] = value

                # Ramping down
                for i in range(-1000, 20, 20):
                    set_voltage = self.main.build_command(
                        self.data["Switching"][idx][2], ("set_voltage", "{}".format(i))
                    )
                    self.vcw.write(self.data["Switching"][idx][2], set_voltage)

                # Return to normal
                self.vcw.write(self.data["Switching"][idx][2], set_voltage_0)
                outputoff = self.main.build_command(
                    self.data["Switching"][idx][2], ("set_output", "0")
                )
                self.vcw.write(self.data["Switching"][idx][2], outputoff)

                continue
            ############################################################################################################

            # If output can be switched on, turn it on
            if "set_output" in self.data["Switching"][idx][2]:
                outputon = self.main.build_command(
                    self.data["Switching"][idx][2], ("set_output", "1")
                )
                self.vcw.write(self.data["Switching"][idx][2], outputon)
            if meas[:-5] in self.open_corrections:
                freq = self.main.build_command(
                    self.data["Switching"][idx][2], ("set_frequency", self.cal_to[meas[:-5]])
                )
                self.vcw.write(self.data["Switching"][idx][2], freq)
            if meas == "Rintempty":
                curr = self.main.build_command(
                    self.data["Switching"][idx][2],("set_measure_current", ""))
                zero = self.main.build_command(
                    self.data["Switching"][idx][2],
                    ("set_zero_check", "OFF"))
                self.vcw.write(self.data["Switching"][idx][2], curr)
                self.vcw.write(self.data["Switching"][idx][2], zero)

            # Perform the measurements
            corr = self.open_corrections.get(meas[:-5],0)
            self.perform_measurement_loop(idx, command, meas, corr)

            # If output can be switched off, turn it off
            if "set_output" in self.data["Switching"][idx][2]:
                outputoff = self.main.build_command(
                    self.data["Switching"][idx][2], ("set_output", "0")
                )
                self.vcw.write(self.data["Switching"][idx][2], outputoff)
            if meas == "Rintempty":
                zero = self.main.build_command(
                    self.data["Switching"][idx][2],
                    ("set_zero_check", "ON"))
                self.vcw.write(self.data["Switching"][idx][2], zero)

    def empty_measurements_test(self):
        """Does the device empty measurement (TEST). It switches to the measurement and then takes samples. The card is
        not contacted at this time"""
        mu, sigma = 0, 0.1  # mean and standard deviation
        s = np.random.normal(mu, sigma, self.samples)
        i = 0
        from time import sleep

        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
            "branch"
        ] = "Empty"
        for j, meas in enumerate(list(self.data["Empty"].keys())):
            self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                "overallprogress"
            ] = j / len(list(self.data["Empty"].keys()))
            self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                "currenttest"
            ] = meas
            for k, sam in enumerate(s):
                self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                    "partialprogress"
                ] = ((k+1) / self.samples)
                self.data["Empty"][meas][i] = sam
                i += 1
                sleep(0.05)
                force_plot_update(self.main.framework["Configs"]["config"]["settings"])
            i = 0

    def test_card_measurements(self):
        """Does the KIT test card measurements. It switches either to Rpoly, Cac, or Cint and conducts the measurement
        on the card. Each measurement will be repeated self.samples times and the table will recontact every time."""
        for j, part in enumerate(self.data["TestCard"]): # Loop over all testcard entries

            if self.main.event_loop.stop_all_measurements_query():
                break # If the stop signal was send

            switching = {v[0]: v[1] for v in self.data["Switching"]}

            if self.main.table.move_to_strip(
                    self.sensor_pad_data,
                    part,
                    self.trans,
                    self.T,
                    self.V0,
                    self.height,
            ) and self.switching.switch_to_measurement(switching[part]):
                idx = [k[0] for k in self.data["Switching"]].index(part)
                device = self.data["Switching"][idx][2]

                # Update the framework
                self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                    "overallprogress"
                ] = (j+1) / len(list(self.data["TestCard"].keys()))
                self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                    "currenttest"
                ] = part

                # Move table up and down
                self.move_up_down()

                if part == "R1":  # Rpoly measurement
                    # Set the voltage to -1
                    voltage = -1.0
                    set_voltage = self.main.build_command(device, ("set_voltage", voltage))
                    set_output_on = self.main.build_command(device, ("set_output", "ON"))
                    read = self.main.build_command(device, "get_read")
                    self.vcw.write(device, set_output_on)
                    self.vcw.write(device, set_voltage)
                    sleep(1.0)
                    # Perform the measurements
                    self.perform_measurement_loop(idx, read, part, corr=0, type="TestCard", precommand=self.move_up_down)
                    voltage = 0.
                    set_voltage = self.main.build_command(device, ("set_voltage", voltage))
                    self.vcw.write(device, set_voltage)
                    set_output_off = self.main.build_command(device, ("set_output", "OFF"))
                    self.vcw.write(device, set_output_off)

                elif part == "R2": # Rint measurement
                    read = self.main.build_command(device, "get_read")
                    set_output = self.main.build_command(self.SMU2, ("set_output", "ON"))
                    self.vcw.write(self.SMU2, set_output)

                    for i in range(self.samples):
                        self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                            "partialprogress"
                        ] = ((i+1) / self.samples)

                        if not self.main.event_loop.stop_all_measurements_query():
                            values = []

                            self.move_up_down()

                            # Zero check off
                            zero = self.main.build_command(
                                self.data["Switching"][idx][2],
                                ("set_zero_check", "OFF"))
                            self.vcw.write(self.data["Switching"][idx][2], zero)

                            for voltage in np.linspace(-1.0, 1.0, num=10, endpoint=True):
                                set_voltage = self.main.build_command(self.SMU2, ("set_voltage", voltage))
                                self.vcw.write(self.SMU2, set_voltage)
                                values.append(float(self.query_values(idx, read, self.subsamples)))
                            slope, intercept, r_value, p_value, std_err = stats.linregress(
                                np.linspace(-1.0, 1.0, num=10, endpoint=True), values
                            )
                            self.data["TestCard"][part][i] = 1/slope
                            force_plot_update(self.main.framework["Configs"]["config"]["settings"])

                            # Zero check on
                            zero = self.main.build_command(
                                self.data["Switching"][idx][2],
                                ("set_zero_check", "ON"))
                            self.vcw.write(self.data["Switching"][idx][2], zero)

                    set_voltage = self.main.build_command(self.SMU2, ("set_voltage", 0))
                    self.vcw.write(self.SMU2, set_voltage)
                    set_output = self.main.build_command(self.SMU2, ("set_output", "OFF"))
                    self.vcw.write(self.SMU2, set_output)
                    # Zero check on
                    zero = self.main.build_command(
                        self.data["Switching"][idx][2],
                        ("set_zero_check", "ON"))
                    self.vcw.write(self.data["Switching"][idx][2], zero)

                elif part == "C1" or part == "C2":
                    read = self.main.build_command(device, "get_read")
                    corr = self.open_corrections[switching[part]]
                    freq = self.cal_to[switching[part]]
                    self.main.build_command(self.LCR_meter, ("set_frequency", freq))
                    self.vcw.write(self.LCR_meter, freq)
                    # Perform the measurements
                    self.perform_measurement_loop(idx, read, part, corr=corr, type="TestCard", precommand=self.move_up_down)




    def save_results(self):
        """Saves everything to a file"""
        padding = 24  # Padding for each of the data points
        header = "SQC self test measurement file \n Date: {} \n Operator: {} \n\n".format(
            time.asctime(),
            self.main.framework["Configs"]["config"]["settings"].get(
                "Current_operator", "None"
            ),
        )
        empttykeys = list(self.data["Empty"].keys())
        Cardkeys = list(self.data["TestCard"].keys())

        measurements = list(empttykeys)
        measurements.extend(list(Cardkeys))
        units = [
            "#".ljust(padding),
        ]

        # Append units:
        for meas in measurements:
            header += meas.ljust(padding)
            units.append(self.data["units"].get(meas, "arb. units").ljust(padding))
        header += "\n" + "".join(units)

        finalarray = np.ones(shape=(self.samples, (len(empttykeys) + len(Cardkeys))))
        # Add empty meas
        i = 0
        for meas in empttykeys:
            finalarray[:, i] = self.data["Empty"][meas]
            i += 1
        # Add Test card
        for meas in Cardkeys:
            finalarray[:, i] = self.data["TestCard"][meas]
            i += 1

        filecontent = "\n"
        for line in finalarray:
            for entry in line:
                filecontent += str(entry).ljust(padding)
            filecontent += "\n"

        self.main.write(self.main.measurement_files["QTCTESTSYSTEM"], header+filecontent)

    def perform_open_correction(self, LCR, measurements, count=15):
        read_command = self.main.build_command(LCR, "get_read")
        for meas, freq in measurements.items():
            data = []
            self.main.queue_to_main.put(
                {"INFO": "LCR open calibration on {} path...".format(meas)}
            )
            if not self.switching.switch_to_measurement(meas):
                self.stop_everything()
                return
            self.change_value(LCR, "set_frequency", freq)
            sleep(0.2)
            for i in range(count):
                data.append(
                    self.vcw.query(LCR, read_command).split(LCR.get("separator", ","))[
                        0
                    ]
                )
            self.open_corrections[meas] = np.mean(
                np.array(data, dtype=float), dtype=float
            )
        self.switching.switch_to_measurement("IV")
        self.main.queue_to_main.put({"INFO": "LCR open calibration finished!"})

    def query_values(self, idx, command, samples):
        """Queries some values from a device and makes an average out of the values"""
        values = []
        for k in range(samples):  # takes samples
            val = self.vcw.query(self.data["Switching"][idx][2], command)
            values.append(float(val.split(",")[0].split()[0]))
        return np.mean(values)

    def perform_measurement_loop(self, idx, command, meas, corr=0, type = "Empty", precommand=None, postcommand=None):
        """Performs the loop"""
        for i in range(self.samples):
            if not self.main.event_loop.stop_all_measurements_query():

                if precommand:
                    precommand()

                self.main.framework["Configs"]["config"]["settings"]["QTC_test"][
                    "partialprogress"
                ] = ((i+1) / self.samples)
                value = self.query_values(idx, command, self.subsamples)
                self.data[type][meas][i] = value-corr
                force_plot_update(self.main.framework["Configs"]["config"]["settings"])

                if postcommand:
                    postcommand()

    def move_up_down(self):
        """Moves the table up and down for recontacting to the pad"""
        if self.main.table.move_down(1000.):
            self.main.table.move_up(1000.)
        else:
            self.log.error("Table movement failed in test!!!")

    def stop_everything(self):
        """Stops the measurement
        A signal will be genereated and send to the event loops, which sets the statemachine to stop all measurements"""
        self.main.queue_to_main.put({"Warning": "Stop QTC test was called..."})
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)
        self.log.warning("Measurement STOP was called, check logs for more information")
