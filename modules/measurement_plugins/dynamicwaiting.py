# This file manages the dynamic waiting time measurements and it is intended to be used as a plugin for the QTC software

import sys

sys.path.append('../modules')
from ..utilities import *
l = logging.getLogger(__name__)

help = help_functions()
vcw = VisaConnectWizard.VisaConnectWizard()
trans = transformation()


class dynamicwaiting_class:

    def __init__(self, main_class):
        self.main = main_class
        self.switching = self.main.switching
        self.biasSMU = self.main.IVSMU
        self.justlength = 24
        self.do_dynamic_waiting()

    def stop_everything(self):
        """Stops the measurement"""
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.main.queue_to_main.put(order)

    def do_dynamic_waiting(self):
        """
        This function does everything concerning the dynamic waiting time meausurement
        :return:
        """