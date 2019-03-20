import ast
import json
import os
import os.path as osp
import sys, importlib, logging

import numpy as np
import pyqtgraph as pq
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


from ..utilities import raise_exception

l = logging.getLogger(__name__)

class Settings_window:

    def __init__(self, GUI_classes, layout):

        self.variables = GUI_classes
        self.layout = layout
        self.measurements = self.variables.default_values_dict["settings"]["measurement_types"]

        #self.measurements = ["IV_measure", "CV_measure", "Strip_measure", "Istrip_measure", "Idiel_measure", "Rpoly_measure", "Cac_measure", "Cback_measure", "Cint_measure", "Rint_measure"]
        # Settings tab
        settings_widget = QWidget()
        self.settings = self.variables.load_QtUi_file("settings_gui.ui", settings_widget)
        self.layout.addWidget(settings_widget)

        if self.measurements:
            self.configure_settings()

        # Add the shell commands
        self.variables.shell.add_cmd_command(self.load_new_settings)
        self.variables.shell.add_cmd_command(self.configure_settings)

    def get_all_settings(self):
        '''This function gets all settings'''

        #Just a list of all settings which should be included
        settings_list = self.measurements
        settings_dict = {}

        for setting in settings_list:
            settings_to_write = self.get_specific_settings_value(str(setting)+"_measure")
            if settings_to_write:
                settings_dict.update({str(setting+"_measure"): settings_to_write})

        return settings_dict


    def get_specific_settings_value(self, data_storage):
        '''This returns the values of a specific setting'''
        return self.variables.default_values_dict["settings"].get(str(data_storage),[False, 0, 0, 0])

    def load_new_settings(self, args=None):
        '''This function loads the new settings from the gui into the state machine'''

        # IV
        self.load_new_values("IV_measure",
                       self.settings.doIV_checkBox, self.settings.max_voltage_IV,
                       self.settings.complience_IV, self.settings.voltage_steps_IV)

        # CV
        self.load_new_values("CV_measure", self.settings.doCV_checkBox,
                       self.settings.max_voltage_CV, self.settings.complience_CV, self.settings.voltage_steps_CV)

        # stripscan
        self.load_new_values("Stripscan_measure",
                       self.settings.dostripscans_checkBox,
                       self.settings.max_voltage_strip, self.settings.complience_strip,
                       self.settings.voltage_steps_strip)

        # istrip
        self.load_new_values("Istrip_measure",
                       self.settings.doIstrip_checkBox,
                       self.settings.Istrip_every, self.settings.Istrip_Start_strip, self.settings.Istrip_End_strip)

        # idiel
        self.load_new_values("Idiel_measure", self.settings.doIdiel_checkBox,
                       self.settings.Idiel_every, self.settings.Idiel_Start_strip, self.settings.Idiel_End_strip)

        # Rint
        self.load_new_values("Rint_measure",
                       self.settings.doRint_checkBox,
                       self.settings.Rint_every, self.settings.Rint_Start_strip,
                       self.settings.Rint_End_strip)

        # Cback
        self.load_new_values("Cback_measure",
                             self.settings.doCback_checkBox,
                             self.settings.Cback_every, self.settings.Cback_Start_strip,
                             self.settings.Cback_End_strip)

        # Cint
        self.load_new_values("Cint_measure",
                             self.settings.doCint_checkBox,
                             self.settings.Cint_every, self.settings.Cint_Start_strip,
                             self.settings.Cint_End_strip)

        # rpoly
        self.load_new_values("Rpoly_measure", self.settings.doRpoly_checkBox,
                       self.settings.Rploy_every, self.settings.Rpoly_Start_strip, self.settings.Rpoly_End_strip)

        # idark
        self.load_new_values("Idark_measure", self.settings.doIdark_checkBox,
                       self.settings.Idark_every, self.settings.Idark_Start_strip, self.settings.Idark_End_strip)

        # cac
        self.load_new_values("Cac_measure", self.settings.doCac_checkBox,
                       self.settings.C_ac_every, self.settings.C_ac_Start_strip, self.settings.C_ac_End_strip)
        # CintAC
        self.load_new_values("CintAC_measure", self.settings.doCintAC_checkBox,
                             self.settings.CintAC_every, self.settings.CintAC_Start_strip, self.settings.CintAC_End_strip)



    def load_new_values(self, data_storage, checkbox, first_value, second_value, third_value):
        '''This functions loads the  the values into the state machine'''
        list = [checkbox.isChecked(), first_value.value(), second_value.value(), third_value.value()]
        self.variables.default_values_dict["settings"][str(data_storage)] = list

    def configure_settings(self, args=None):
        '''This function initializes the new values for the state machine'''

        # IV
        self.configure(self.variables.default_values_dict["settings"]["IV_measure"],
                       self.settings.doIV_checkBox,  self.settings.max_voltage_IV,
                       self.settings.complience_IV,  self.settings.voltage_steps_IV)

        # CV
        self.configure(self.variables.default_values_dict["settings"]["CV_measure"], self.settings.doCV_checkBox,
                       self.settings.max_voltage_CV, self.settings.complience_CV, self.settings.voltage_steps_CV)

        # stripscan
        self.configure(self.variables.default_values_dict["settings"]["Stripscan_measure"], self.settings.dostripscans_checkBox,
                       self.settings.max_voltage_strip, self.settings.complience_strip, self.settings.voltage_steps_strip)

        # istrip
        self.configure(self.variables.default_values_dict["settings"]["Istrip_measure"], self.settings.doIstrip_checkBox,
                       self.settings.Istrip_every, self.settings.Istrip_Start_strip, self.settings.Istrip_End_strip)

        # idiel
        self.configure(self.variables.default_values_dict["settings"]["Idiel_measure"], self.settings.doIdiel_checkBox,
                       self.settings.Idiel_every, self.settings.Idiel_Start_strip, self.settings.Idiel_End_strip)

        # cint
        self.configure(self.variables.default_values_dict["settings"]["Cint_measure"], self.settings.doCint_checkBox,
                       self.settings.Cint_every, self.settings.Cint_Start_strip, self.settings.Cint_End_strip)

        # rpoly
        self.configure(self.variables.default_values_dict["settings"]["Rpoly_measure"], self.settings.doRpoly_checkBox,
                       self.settings.Rploy_every, self.settings.Rpoly_Start_strip, self.settings.Rpoly_End_strip)

        # idark
        self.configure(self.variables.default_values_dict["settings"]["Idark_measure"], self.settings.doIdark_checkBox,
                       self.settings.Idark_every, self.settings.Idark_Start_strip, self.settings.Idark_End_strip)

        # cac
        self.configure(self.variables.default_values_dict["settings"]["Cac_measure"], self.settings.doCac_checkBox,
                       self.settings.C_ac_every, self.settings.C_ac_Start_strip, self.settings.C_ac_End_strip)

        # cback
        self.configure(self.variables.default_values_dict["settings"]["Cback_measure"], self.settings.doCback_checkBox,
                       self.settings.Cback_every, self.settings.Cback_Start_strip, self.settings.Cback_End_strip)

        # Rint
        self.configure(self.variables.default_values_dict["settings"]["Rint_measure"], self.settings.doRint_checkBox,
                       self.settings.Rint_every, self.settings.Rint_Start_strip, self.settings.Rint_End_strip)

        # CintAC
        self.configure(self.variables.default_values_dict["settings"]["CintAC_measure"], self.settings.doCintAC_checkBox,
                       self.settings.CintAC_every, self.settings.CintAC_Start_strip, self.settings.CintAC_End_strip)


        l.info("Measurement settings are reconfigured...")

    def configure(self, data, checkbox, first_value, second_value, third_value):
        if data[0]:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)

        first_value.setValue(data[1])
        second_value.setValue(data[2])
        third_value.setValue(data[3])
