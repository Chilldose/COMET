# This file manages the dynamic waiting time measurements and it is intended to be used as a plugin for the QTC software

import logging
from time import time, sleep
import sys
import re
sys.path.append('../UniDAQ')
from ..utilities import timeit, transformation
from .forge_tools import tools

ttime = time
import numpy as np

class dynamicwaiting_class(tools):

    def __init__(self, main_class):

        # Init the tools class and the variables from the main
        self.main = main_class
        super(dynamicwaiting_class, self).__init__(self.main.framework, self.main)
        self.log = logging.getLogger(__name__)

        # Get data from the framework
        self.vcw = main_class.framework["VCW"]
        self.switching = main_class.framework["Switching"]
        self.biasSMU = main_class.devices["BiasSMU"]


        # Job specific variables
        self.compliance = main_class.job_details["dynamicwaiting"]["Compliance"]
        self.justlength = 24
        # The intervall of every measurement, (is something else then the delay value!)
        self.interval = self.main.job_details["dynamicwaiting"]["Interval"]/1000.
        self.buffer = self.main.job_details["dynamicwaiting"]["Samples"]
        # This delay is the fixed measurement delay, which delays EVERY measurement before a value is aquired
        # If you get bad values increase this to give the ADC some time to aquire a value
        self.delay = self.main.job_details["dynamicwaiting"]["Delay"]
        self.NPLC = self.main.job_details["dynamicwaiting"]["NPLC"]
        # The Start delay defines a global offset before a measurement series actually starts
        self.start_delay = self.main.job_details["dynamicwaiting"]["start_delay"]
        self.SMURange = self.main.job_details["dynamicwaiting"]["Range"]

        # Some variables
        self.current_voltage = None
        self.voltage_step_list = []
        self.xvalues = []
        self.yvalues = []

        # The commands differ from device to device
        # Therefore I need to write the commands for every device on its own. Nice work Keithley....


        if "2470 Keithley SMU" in self.biasSMU["Device_name"]:
            # Config parameters for the 2470 Keithley SMU
            self.get_data_query = "printbuffer(1, {samples!s}, measbuffer)"
            self.get_timestamps_query = "printbuffer(1, {samples!s}, measbuffer.relativetimestamps)"
            self.SMU_clean_buffer = "measbuffer = nil"
            self.SMUON = "smu.ON"
            self.SMUOFF = "smu.OFF"
            self.separate = "\n"

            self.SMU_config = "smu.measure.count = {samples!s} \n" \
                              "measbuffer = buffer.make(smu.measure.count, buffer.STYLE_COMPACT)\n" \
                              "smu.source.level = {level!s} \n" \
                              "loadscript DiodeRelax \n" \
                              "smu.measure.read(measbuffer)\n" \
                              "waitcomplete()\n" \
                              "endscript "

            self.measureItobuffer = "measbuffer.clear() \n" \
                                    "smu.source.level = {level!s} \n" \
                                    "DiodeRelax()" # Maybe not the fastest method ???

            self.setup_config = [("set_autorange", "smu.OFF"),
                                 ("set_range", str(self.SMURange)),
                                 ("set_compliance", str(self.compliance)),
                                 ("set_NPLC", "{!s}".format(self.NPLC)),
                                 ("set_filter_enable", "smu.OFF"),
                                 ("set_autozero", "smu.OFF"),
                                 ("set_source_readback", "smu.OFF"),
                                 ("set_autozero", "smu.OFF"),
                                 ("set_source_delay", str(self.start_delay)) # will be done internally
                                 ]


        else:
            # Config parameters for the 2657 Keithley SMU
            self.get_data_query = "printbuffer(1, {samples!s}, measbuffer)"
            self.get_timestamps_query = "printbuffer(1, {samples!s}, measbuffer.timestamps)"
            self.SMU_clean_buffer = "measbuffer = nil"
            self.SMUON = "1"
            self.SMUOFF = "0"
            self.separate = None

            self.SMU_config = "smua.measure.count = {samples!s} \n" \
                              "smua.measure.interval = {interval!s}\n" \
                              "measbuffer = smua.makebuffer(smua.measure.count)\n" \
                              "measbuffer.collecttimestamps = 1" \

            self.measureItobuffer = "smua.source.levelv = {level!s} \n" \
                                    "delay(" + str(self.start_delay) + ")"\
                                    "smua.measure.overlappedi(measbuffer)\n" \
                                    "waitcomplete()\n"

            self.setup_config = [("set_compliance_current", str(self.compliance)),
                                              ("set_NPLC", "{!s}".format(self.NPLC)),
                                              #("set_measurement_delay_factor", "{!s}".format(self.delay)),
                                              ("set_measure_adc", "smua.ADC_FAST"),
                                              ("set_current_range_low", str(self.SMURange)),
                                              ("set_meas_delay", str(self.delay))
                                             ]


    def run(self):
        # Starts the actual measurement
        time = self.do_dynamic_waiting()
        self.log.info("Dynamic warting time took: {} sec".format(time))

    def stop_everything(self):
        """Stops the measurement"""
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)

    @timeit
    def do_dynamic_waiting(self):
        """
        This function does everything concerning the dynamic waiting time measurement
        :return:
        """

        # Config the SMU
        self.do_preparations(self.biasSMU, self.buffer, self.interval)

        # Construct results array
        self.xvalues = np.zeros((len(self.voltage_step_list), int(self.buffer)))
        self.yvalues = np.zeros((len(self.voltage_step_list), int(self.buffer)))
        # Conduct the measurement
        for i, voltage in enumerate(self.voltage_step_list):
            if not self.main.event_loop.stop_all_measurements_query():  # To shut down if necessary

                # Some elusive error happens sometimes, where the smu forgets its pervious config
                #self.main.send_to_device(self.biasSMU, self.SMU_config.format(samples=self.buffer, interval=self.interval))
                # Here the magic happens it changes all values and so on
                self.xvalues[i], self.yvalues[i], time = self.do_dynamic_measurement("dynamicwaiting", self.biasSMU, voltage, self.buffer, self.interval, True)

                if self.check_complience(self.biasSMU, float(self.compliance), command="get_read",):
                    self.stop_everything()  # stops the measurement if compliance is reached

                if not self.steady_state_check(self.biasSMU, command="get_read_current", max_slope=1e-6, wait=0, samples=5, Rsq=0.5, complience=self.compliance):  # Is a dynamic waiting time for the measuremnts
                    self.stop_everything()

                sleep(1.)

        # Ramp down and switch all off
        self.current_voltage = self.framework["Configs"]["config"]["settings"]["bias_voltage"]
        self.ramp_voltage(self.biasSMU, "set_voltage", self.current_voltage, 0, 20, 0.01)
        self.change_value(self.biasSMU, "set_voltage", "0")
        self.change_value(self.biasSMU, "set_output", self.SMUOFF)
        self.framework["Configs"]["config"]["settings"]["bias_voltage"] = 0

        self.write_dyn_to_file(self.main.measurement_files["dynamicwaiting"], self.voltage_step_list, self.xvalues, self.yvalues)

    def write_dyn_to_file(self, file, voltages, xvalues, yvalues):
        """
        """

        # Check if length of voltages matches the length of data array
        if len(xvalues) == len(yvalues):
            data = np.array([xvalues, yvalues])
            #data = np.transpose(data)
            # Write voltage header for each measurement first the voltages
            self.main.write(file, 'V'+''.join([format(el, '<{}'.format(self.justlength*2)) for el in voltages])+"\n")
            #Then the Units
            self.main.write(file, ''.join([format("time[s]{}current[A]".format(" "*(self.justlength-7)),
                                                  '<{}'.format(self.justlength*2)) for x in range(len(voltages))]) + "\n")

            for i in range(len(data[0,0,:])):
                times = [format(time, '<{}'.format(self.justlength)) for time in data[:, :, i][0]]
                curr = [format(curr, '<{}'.format(self.justlength)) for curr in data[:, :, i][1]]
                final = "".join([t+c for t, c in zip(times, curr)])
                self.main.write(file, final+"\n")
        else:
            self.log.error("Length of results array are non matching, abort storing data to file")

    def do_preparations(self, device, samples = 100, interval = 0.01):
        """This function prepares the setup, like ramping the voltage and steady state check
        """

        # Get ramping list
        voltage_Start = self.main.job_details["dynamicwaiting"].get("StartVolt", 0)
        voltage_End = self.main.job_details["dynamicwaiting"].get("EndVolt", 0)
        voltage_steps = self.main.job_details["dynamicwaiting"].get("Steps", 10)
        self.voltage_step_list = self.ramp_value(voltage_Start, voltage_End, voltage_steps)

        # Switch to IV for correct biasing for ramp
        if not self.switching.switch_to_measurement("IV"):
            self.stop_everything()

        # Configure the setup, compliance and switch on the smu
        self.send_to_device(self.biasSMU, self.SMU_clean_buffer)
        self.config_setup(self.biasSMU, self.setup_config)
        self.change_value(self.biasSMU, "set_voltage", "0.0")
        self.change_value(self.biasSMU, "set_output", self.SMUON)

        if self.steady_state_check(self.biasSMU, command="get_read_current", max_slope=1e-6, wait=0, samples=3, Rsq=0.5, complience=self.compliance):  # Is a dynamic waiting time for the measuremnts
            self.current_voltage = self.framework["Configs"]["config"]["settings"]["bias_voltage"]
        else:
            self.stop_everything()

        # Send the sweep command to the device
        self.send_to_device(self.biasSMU, self.SMU_config.format(samples=samples, interval=interval, level=0),
                            self.separate)

    def do_dynamic_measurement(self, str_name, device, voltage = 0, samples = 100, interval = 0.01, write_to_main = True):
        '''
         Does a simple dynamic waiting time measurement
        '''
        from time import time
        #self.main.send_to_device(self.biasSMU, self.SMU_clean_buffer)

        # Send the command to the device and wait till complete
        starttime = time()
        self.send_to_device(device, self.measureItobuffer.format(level=voltage, samples=samples))
        self.framework["Configs"]["config"]["settings"]["bias_voltage"] = voltage

        # Get the data from the device
        device_ansered = False
        iter = 0
        ans = ""
        times = ""
        while not device_ansered:
            ans = self.vcw.query(device, self.get_data_query.format(samples=samples)).strip()
            times = self.vcw.query(device, self.get_timestamps_query.format(samples=samples)).strip()
            if ans:
                device_ansered = True
            elif iter > 5:
                ans = ""
                break
            else:
                iter += 1

        endtime = time()
        time = abs(endtime - starttime)

        if ans:
            #xvalues, yvalues = self.pic_device_answer(ans, time/self.buffer)
            xvalues, yvalues = self.pic_device_answer(ans, times, self.start_delay)

            if len(xvalues) > samples:  # because some devices add an extra value to the end, and some dont. Good work again keithley
                xvalues = xvalues[:int(samples)]
                yvalues = yvalues[:int(samples)]

            if write_to_main: # Writes data to the main, or not
                self.main.queue_to_main.put({str(str_name): [xvalues, yvalues]})
            # Clear buffer
            #self.main.send_to_device(device, self.SMU_clean_buffer)

            return xvalues, yvalues, time

        else:
            self.log.error("Timeout occured while reading from the device! Increase timeout for devices if necessary"
                           "Or a buffer overflow happend. Check the buffer of the device!")
            return [], [], 0.0

    def pic_device_answer(self, values, times, offset):
        """
        Dissects the answer string and returns 2 array containing the x an y values
        """
        expression = re.compile(r"\S+\b", re.MULTILINE)
        yvalues = list(map(float, expression.findall(values)))
        xvalues = list(map(float, expression.findall(times)))
        xvalues.append(xvalues[-1]+abs(xvalues[-2]-xvalues[-1]))
        xvalues = [x+offset for x in xvalues]

        return xvalues, yvalues
