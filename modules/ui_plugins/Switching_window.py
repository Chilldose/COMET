import ast
import json
import os
import os.path as osp
import sys, importlib, logging
from time import sleep

import numpy as np
import pyqtgraph as pq
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


from .. import utilities
from .. import VisaConnectWizard

l = logging.getLogger(__name__)

hf = utilities.help_functions()
vcw = VisaConnectWizard.VisaConnectWizard()

class Switching_window:

    def __init__(self, GUI_classes, layout):
        self.settings = GUI_classes
        self.layout = layout
        self.switching_control = GUI_classes.switching
        self.manual_switching = False

        #self.switching_control.check_switching_action()

        # Settings tab
        switching_widget = QWidget()
        self.switching = self.settings.load_QtUi_file("./modules/QT_Designer_UI/Switching.ui", switching_widget)
        self.layout.addWidget(switching_widget)

        self.set_radio_buttons_checkable(False)

        self.switching.apply_button.clicked.connect(self.apply_switching_button_action)
        self.switching.check_switching_Button.clicked.connect(self.update_GUI_switching_scheme)
        self.switching.reset_button.clicked.connect(self.reset_switching)
        self.switching.Override.clicked['bool'].connect(self.manual_override_action)

        # Check first switching
        #self.check_switching_action()

        # Add cmd option
        self.settings.shell.add_cmd_command(self.reset_switching)

    def manual_override_action(self, bool):
        '''Manual switching enabling'''
        self.set_radio_buttons_checkable(bool)
        if bool:
            self.manual_switching = True
        else:
            self.manual_switching = False

    def set_radio_buttons_checkable(self, checkable = False):
        '''Set all radio buttons uncheckable/checkable'''
        switching = self.settings.devices_dict
        for device in switching.values():  # loop over all switching systems
            if "Switching relay" in device["Device_type"]:
                if device["Display_name"] == "Brand Box":
                    getattr(self.switching, "A1").setEnabled(checkable)
                    getattr(self.switching, "A2").setEnabled(checkable)
                    getattr(self.switching, "B1").setEnabled(checkable)
                    getattr(self.switching, "B2").setEnabled(checkable)
                    getattr(self.switching, "C1").setEnabled(checkable)
                    getattr(self.switching, "C2").setEnabled(checkable)

                if device["Display_name"] == "Switching":
                    # First reset all previous checked radio buttons
                    for i in range(1, 3):  # matrices
                        for j in range(1, 5):  # Zeilen
                            for k in range(1, 6):  # Spalten
                                getattr(self.switching, "m" + str(i) + str(j) + str(k)).setEnabled(checkable)
    @hf.raise_exception
    def update_GUI_switching_scheme(self, kwargs= None):
        '''This function updates the GUI switching scheme'''
        switching = self.switching_control.check_switching_action()
        for name, scheme in switching.items(): # loop over all switching systems
            if name == "Brand Box":
                # First reset all previous checked radio buttons
                self.switching.A1.setChecked(False)
                self.switching.A2.setChecked(False)
                self.switching.B1.setChecked(False)
                self.switching.B2.setChecked(False)
                self.switching.C1.setChecked(False)
                self.switching.C2.setChecked(False)

                # Now set all which need to be set

                for item in scheme:
                    if item:
                        getattr(self.switching, item).setChecked(True)

            if name == "Switching":
                #First reset all previous checked radio buttons

                for i in range(1,3): #matrices
                    for j in range(1,5): #Zeilen
                        for k in range(1,6): # Spalten
                            getattr(self.switching, "m" + str(i) + str(j) + str(k)).setChecked(False)

                for item in scheme: # these must be of type 1!1!1 etc.
                    if item:
                        new_item = item.replace("!", "").replace("!", "") # removes the !
                        getattr(self.switching, "m" + new_item).setChecked(True)
        #self.manual_override_action(False) # so nobody can change a thing
        #self.switching.Override.setChecked(False)  # so the button is in the right state

    def reset_switching(self, args=None):
        for device in self.settings.devices_dict.values():
            if "Switching relay" in device["Device_type"]:
                self.switching_control.change_switching(device, []) # Opens all closed switches
                self.update_GUI_switching_scheme()


    @hf.raise_exception
    def apply_switching_button_action(self, *kwargs):
        if self.switching.IV_radio.isChecked():
            self.switching_control.switch_to_measurement("IV")

        if self.switching.CV_radio.isChecked():
            self.switching_control.switch_to_measurement("CV")

        if self.switching.Idark_radio.isChecked():
            self.switching_control.switch_to_measurement("Idark")

        if self.switching.Istrip_radio.isChecked():
            self.switching_control.switch_to_measurement("Istrip")

        if self.switching.Idiel_radio.isChecked():
            self.switching_control.switch_to_measurement("Idiel")

        if self.switching.Rpoly_radio.isChecked():
            self.switching_control.switch_to_measurement("Rpoly")

        if self.switching.Cint_radio.isChecked():
            self.switching_control.switch_to_measurement("Cint")

        if self.switching.Rint_radio.isChecked():
            self.switching_control.switch_to_measurement("Rint")

        if self.switching.Cac_radio.isChecked():
            self.switching_control.switch_to_measurement("Cac")

        #if self.switching.Cback_radio.isChecked():
        #    self.switching_control.switch_to_measurement("Cback")


        if self.manual_switching:
            self.apply_manual_switching()

        self.update_GUI_switching_scheme()

    def apply_manual_switching(self):
        """This function switches to the current selected GUI switching settings"""
        # First get all pressed check boxes for the switching

        to_switch = {}
        # Brandbox
        to_switch.update({"Brandbox": []})
        # Now get all nodes which need to be set
        for relay in ["A1", "A2", "B1", "B2", "C1", "C2"]: # This is GUI specific!!!!
            if getattr(self.switching, relay).isChecked(): # find out if the button is checked
                to_switch["Brandbox"].append(relay)


        # Switching matrix
        to_switch.update({"Switching": []})
        # Now get all nodes which need to be set
        for i in range(1,3): #matrices
            for j in range(1,5): #Zeilen
                for k in range(1,6): # Spalten
                    if getattr(self.switching, "m" + str(i) + str(j) + str(k)).isChecked():
                        to_switch["Switching"].append(str(i)+ "!" + str(j) + "!" + str(k))


        # No apply the switching
        self.switching_control.apply_specific_switching(to_switch)

