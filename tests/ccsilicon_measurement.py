import logging
import random
import time

from COMET.core.process import Process, StopProcessIteration
from COMET.core.measurement import Measurement
from COMET.VisaConnectWizard import VisaConnectWizard import VisaDeviceManager

class ClimateChamberDevice(object):
    """Fake climate chamber device."""

    def __init__(self, manager):
        self.manager = manager
        self.__voltage = 0.0

    def readTemperature(self):
        return random.uniform(21.5, 22.5)

    def readHumidity(self):
        return random.uniform(42.0, 44.0)

class SMUDevice(object):
    """Fake generic SMU device."""

    def __init__(self, manager):
        self.manager = manager
        self.__voltage = 0.0

    def readVoltage(self):
        return random.uniform(self.__voltage-0.01, self.__voltage+0.01)

    def readCurrent(self):
        return random.uniform(0.8, 1.2)

    def getVoltage(self):
        return self.__voltage

    def setVoltage(self, voltage):
        self.__voltage = voltage

class RampVProcess(Process):
    """Voltage ramp up/down process.

    Keyword Arguments:
        - device -- SMU device
        - begin -- ramp begin in volts
        - end -- ramp end in volts
        - step -- ramp step in volts (negative for ramp down)
    """

    def __init__(self, parent, delay, device, v_begin, v_end, v_step):
        super(RampVProcess, self).__init__(parent, delay)
        self.device = device
        self.v_begin = v_begin
        self.v_end = v_end
        self.v_step = v_step
        self.v_current = self.v_begin

    def is_alive(self):
        if self.v_begin < self.v_end:
            return self.v_current < self.v_end
        return self.v_end < self.v_current

    def iteration_begin(self):
        voltage = self.device.getVoltage()
        self.v_current = voltage + self.v_step
        self.device.setVoltage(self.v_current)

    def iteration_end(self):
        voltage = self.device.readVoltage()
        current = self.device.readCurrent()
        mode = "UP" if self.v_step > 0 else "DOWN"
        logging.info("voltage ramp %s (%+fV): %fV %fA", mode, self.v_step, voltage, current)

class DAQProcess(Process):
    """Infinite data aquisition."""

    def __init__(self, parent, delay, smu_device, cc_device, i_compliance):
        super(DAQProcess, self).__init__(parent, delay)
        self.smu_device = smu_device
        self.cc_device = cc_device
        self.i_compliance = i_compliance

    def is_alive(self):
        return True

    def iteration_begin(self):
        current = self.smu_device.readCurrent()
        # NOTE Random silicon breakdown simualtion!
        if random.randint(0, 12) == 0 and self.iteration > 8:
            current = random.uniform(self.i_compliance+0.5, self.i_compliance+7.0)
        # Compliance check
        if current > self.i_compliance:
            raise StopProcessIteration("*** FAILED: silicon breakdown")
        logging.info("compliance met: %fA (<%fA)", current, self.i_compliance)
        # Read climate chamber (this should be moved to background readings?)
        temperature = self.cc_device.readTemperature()
        humidity = self.cc_device.readHumidity()
        logging.info("climate chamber: temp=%f humid=%f", temperature, humidity)
        # Show occasional hint on how to stop DAQ
        if self.iteration % 16 == 0:
            logging.debug("--------------------------------")
            logging.debug("Hit CTRL+C to stop longterm DAQ!")
            logging.debug("--------------------------------")

class CCSiliconMeasurement(Measurement):
    """Climate chamber silicon measurement."""

    def __init__(self, manager):
        super(CCSiliconMeasurement, self).__init__(manager)
        # Default values
        self.v_min = 0.0
        self.v_max = 12.0
        self.v_longterm = 9.0
        self.v_step = 0.1
        self.i_compliance = 1.5
        self.ramp_delay = 0.1
        self.daq_delay = 0.25

    def init(self):
        # Get SMU device
        smu_device = self.manager.get_device('SMU1234')
        cc_device = self.manager.get_device('CC100')
        self.ramp_up = RampVProcess(self, self.ramp_delay, smu_device, self.v_min, self.v_max, self.v_step)
        self.ramp_down = RampVProcess(self, self.ramp_delay, smu_device, self.v_max, self.v_longterm, -self.v_step)
        self.longterm_daq = DAQProcess(self, self.daq_delay, smu_device, cc_device, self.i_compliance)
        self.ramp_out = RampVProcess(self, self.ramp_delay, smu_device, self.v_longterm, self.v_min, -self.v_step)

    def process(self):
        self.ramp_up.run()
        self.ramp_down.run()
        try:
            self.longterm_daq.run()
        except KeyboardInterrupt:
            logging.info("stopping longterm run (acquired %d samples)...", self.longterm_daq.iteration)
        self.ramp_out.run()

    def final(self):
        # Reset voltage
        smu_device = self.manager.get_device('SMU1234')
        smu_device.setVoltage(self.v_min)

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)

    manager = VisaDeviceManager('@sim')
    context = {} # placeholder

    # Add fake devices
    manager.devices = {
        'SMU1234': SMUDevice(manager),
        'CC100': ClimateChamberDevice(manager),
    }

    measurement = CCSiliconMeasurement(manager)
    measurement.v_min = 0.1
    measurement.v_max = 12.0

    measurement.run()
