import os
import logging
from PyQt5.QtWidgets import *
from ..misc_plugins import engineering_notation as en
import time

from ..utilities import ramp_voltage_job, transformation, change_axis_ticks

class MeasurementDetails_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout

        # Settings tab
        single_widget = QWidget()
        self.single_strip = self.variables.load_QtUi_file("singlemeasurement.ui", single_widget)
        self.layout.addWidget(single_widget)