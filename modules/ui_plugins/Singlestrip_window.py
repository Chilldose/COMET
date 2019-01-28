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
from .. import engineering_notation as en
import time


from .. import utilities
l = logging.getLogger(__name__)

hf = utilities.help_functions()



class Singlestrip_window:

    @hf.raise_exception
    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.HV_on = False

        # Settings tab
        singlestrip_widget = QWidget()
        self.single_strip = self.variables.load_QtUi_file("./modules/QT_Designer_UI/singlestrip.ui", singlestrip_widget)
        self.layout.addWidget(singlestrip_widget)

        self.capacitance_measurements = ["Cback", "Cint", "Cac"]
        self.resistance_measurements = ["Rint"]
        self.plot_data = None

        self.trans = utilities.transformation()

        # Config plot
        self.plot_config()

        # Add items to box
        self.single_strip.which_plot.addItems(self.capacitance_measurements)
        self.single_strip.which_plot.addItems(self.resistance_measurements)

        # Connect the buttons
        self.single_strip.start_button.clicked.connect(self.start_button_action)
        self.single_strip.which_plot.currentIndexChanged.connect(self.new_plot_selection)
        self.single_strip.move_to_button.clicked.connect(self.move_to_strip_action)
        self.single_strip.stop_button.clicked.connect(self.stop_button_action)
        self.single_strip.HV_button.clicked.connect(self.HV_on_action)
        self.new_plot_selection()

        # Add update functions
        self.variables.add_update_function(self.update_text)
        self.variables.add_update_function(self.update_plot)


    def HV_on_action(self):
        '''This simply turns on the voltage'''
        bias_voltage = self.variables.default_values_dict["Defaults"]["bias_voltage"]
        EndVolt = self.single_strip.max_voltage_strip.value()
        Steps = self.single_strip.voltage_steps_strip.value()
        Complience = self.single_strip.complience_strip.value()

        if not self.HV_on:
            hf.ramp_voltage_job(self.variables.message_from_main, self.variables.devices_dict["IVSMU"], bias_voltage,
                                EndVolt, Steps, 0.3, Complience)
        else:
            hf.ramp_voltage_job(self.variables.message_from_main, self.variables.devices_dict["IVSMU"], bias_voltage,
                                0, Steps, 0.3, Complience)


    @hf.raise_exception
    def move_to_strip_action(self, kwargs=None):
        '''Moves the table to the desired strip'''
        if self.variables.default_values_dict["Defaults"]["Alignement"]:
            self.project = self.variables.default_values_dict["Defaults"]["Current_project"]
            self.sensor = "Sensor" + str(self.variables.default_values_dict["Defaults"]["Current_sensor"])
            self.sensor_pad_file = self.variables.pad_files_dict[self.project][self.sensor].copy()
            strip_to_move = int(self.single_strip.which_strip.value())
            error = self.variables.table.move_to_strip(self.sensor_pad_file, strip_to_move, self.trans, self.variables.default_values_dict["Defaults"]["trans_matrix"],  self.variables.default_values_dict["Defaults"]["V0"], self.variables.default_values_dict["Defaults"].get("height_movement", 800))
            if error:
                self.variables.message_to_main.put(error)
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(
                    "An error occured tyring to move to a strip. For more details see event log or the log file")
                # msg.setInformativeText("This is additional information")
                msg.setWindowTitle("Oops.. an error occured")
                # msg.setDetailedText("The details are as follows:")
                msg.exec_()
                return

    @hf.raise_exception
    def update_text(self, kwargs = None):
        """This function updates the stext for the measurements"""
        if self.variables.default_values_dict["Defaults"]["new_data"]: # New data available ?
            self.single_strip.Idark_val.setText("I dark: " +str(en.EngNumber(self.variables.meas_data["Idark"][1][-1]) if len(self.variables.meas_data["Idark"][1]) > 0 else "NaN"))
            self.single_strip.Idiel_val.setText("I diel: " +str(en.EngNumber(self.variables.meas_data["Idiel"][1][-1]) if len(self.variables.meas_data["Idiel"][1]) > 0 else "NaN"))
            self.single_strip.Istrip_val.setText("I strip: " +str(en.EngNumber(self.variables.meas_data["Istrip"][1][-1]) if len(self.variables.meas_data["Istrip"][1]) > 0 else "NaN"))
            self.single_strip.Cac_val.setText("C ac: " +str(en.EngNumber(self.variables.meas_data["Cac"][1][-1]) if len(self.variables.meas_data["Cac"][1]) > 0 else "NaN"))
            self.single_strip.Rpoly_val.setText("R poly: " + str(en.EngNumber(self.variables.meas_data["Rpoly"][1][-1]) if len(self.variables.meas_data["Rpoly"][1]) > 0 else "NaN"))
            self.single_strip.Cint_val.setText("C int: " + str(en.EngNumber(self.variables.meas_data["Cint"][1][-1]) if len(self.variables.meas_data["Cint"][1]) > 0 else "NaN"))
            self.single_strip.Rint_val.setText("R int: " + str(en.EngNumber(self.variables.meas_data["Rint"][1][-1]) if len(self.variables.meas_data["Rint"][1]) > 0 else "NaN"))




    def new_plot_selection(self):
        self.plot_data = str(self.single_strip.which_plot.currentText())

        if self.plot_data == "Cac":
            self.reconfig_plot("Coupling capacitance", ["Capacitance", "F"], ["Frequency", "Hz"], [True, False])
        elif self.plot_data == "Cback":
            self.reconfig_plot("Strip-to-body capacitance", ["Capacitance", "F"], ["Frequency", "Hz"], [True, False])
        elif self.plot_data == "Cint":
            self.reconfig_plot("Interstrip capacitance", ["Capacitance", "F"], ["Frequency", "Hz"], [True, False])
        elif self.plot_data == "Rint":
            self.reconfig_plot("Interstrip resitance ramp", ["Current", "A"], ["Voltage", "V"], [False, False])

        self.update_plot()

    def plot_config(self):
        '''This function configurates the plot'''
        self.single_strip.single_strip_plot.setTitle("Single strip plot")
        self.single_strip.single_strip_plot.setLabel('left', "current", units='A')
        self.single_strip.single_strip_plot.setLabel('bottom', "voltage", units='V')
        self.single_strip.single_strip_plot.showAxis('top', show=True)
        self.single_strip.single_strip_plot.showAxis('right', show=True)
        self.single_strip.single_strip_plot.plotItem.showGrid(x=True, y=True)
        #self.single_strip.single_strip_plot.plotItem.setLogMode(False, True)

    def reconfig_plot(self, Title, xAxis, yAxis, logscale):
        '''Reconfigs the plot for the different plots'''
        self.single_strip.single_strip_plot.setTitle(str(Title))
        self.single_strip.single_strip_plot.setLabel('left', str(xAxis[0]), units=str(xAxis[1]))
        self.single_strip.single_strip_plot.setLabel('bottom', str(yAxis[0]), units=str(yAxis[1]))
        self.single_strip.single_strip_plot.plotItem.setLogMode(x=logscale[0], y=logscale[1])

    @hf.raise_exception
    def update_plot(self, kwargs = None):
        '''This handles the update of the plot'''
        # This clear here erases all data from the viewbox each time this function is called and draws all points again!
        # Without this old plot data will still be visible and redrawn again! High memory usage and cpu usage
        # With the clear statement medium cpu und low memory usage
        if self.variables.default_values_dict["Defaults"]["new_data"]:
            if len(self.variables.meas_data[self.plot_data + "_scan"][0]) == len(self.variables.meas_data[self.plot_data + "_scan"][1]):  # sometimes it happens that the values are not yet ready
                if self.variables.meas_data[self.plot_data + "_scan"]:
                    self.single_strip.single_strip_plot.plot(self.variables.meas_data[self.plot_data + "_scan"][0], self.variables.meas_data[self.plot_data + "_scan"][1], pen="y", clear=True)

    @hf.raise_exception
    def start_button_action(self,kwargs=None):
        '''Starts the single strip measuremnts'''
        if self.variables.default_values_dict["Defaults"]["Current_filename"] and os.path.isdir(self.variables.default_values_dict["Defaults"]["Current_directory"]):

            additional_settings = {"Save_data": True,
                                   "Filepath": self.variables.default_values_dict["Defaults"]["Current_directory"],
                                   "Filename": self.variables.default_values_dict["Defaults"]["Current_filename"],
                                   "Project": self.variables.default_values_dict["Defaults"]["Current_project"],
                                   "Sensor": self.variables.default_values_dict["Defaults"]["Current_sensor"],
                                   "skip_init": True} # Todo: make this variable accassable from the gui

            self.generate_singlestrip_job(additional_settings)
            self.variables.reset_plot_data()


        else:
            reply = QMessageBox.information(None, 'Warning', "Please enter a valid filepath and filename.", QMessageBox.Ok)


    def generate_singlestrip_job(self, additional_settings_dict):

        self.final_job = additional_settings_dict

        header = "# Measurement file: \n " \
                 "# Campaign: " + self.variables.default_values_dict["Defaults"]["Current_project"] + "\n " \
                 "# Sensor Type: " + self.variables.default_values_dict["Defaults"]["Current_sensor"] + "\n " \
                 "# ID: " + self.variables.default_values_dict["Defaults"]["Current_filename"] + "\n " +\
                 "# Operator: " + self.variables.default_values_dict["Defaults"]["Current_operator"] + "\n " \
                 "# Date: " + str(time.asctime()) + "\n\n"

        # if a freq measurement should be conducted
        if self.single_strip.do_freq.isChecked():
            #for cap in self.capacitance_measurements:
                #if getattr(getattr(self.single_strip, "do_" + str(cap)), "isChecked"):
                todo_dict = {}
                if self.single_strip.do_cac.isChecked():
                    todo_dict.update({"Cac": True})
                if self.single_strip.do_cback.isChecked():
                    todo_dict.update({"Cback": True})
                if self.single_strip.do_cint.isChecked():
                    todo_dict.update({"Cint": True})

                self.final_job.update({"stripscan":{"StartVolt": 0,
                                                    "EndVolt": self.single_strip.max_voltage_strip.value(),
                                                    "Steps": self.single_strip.voltage_steps_strip.value(),
                                                    "Complience": self.single_strip.complience_strip.value(),
                                                    "Save_data": True,
                                                    "frequencyscan": {"Measurements": todo_dict,
                                                         "StartFreq": self.single_strip.minimum_freq.value(),
                                                         "EndFreq": self.single_strip.maximum_freq.value(),
                                                         "MinVolt": float(self.single_strip.minimum_volt.value())*1e-3,
                                                         "MaxVolt": float(self.single_strip.maximum_volt.value())*1e-3,
                                                         "DoLog10": self.single_strip.do_log10.isChecked(),
                                                         "VoltSteps": self.single_strip.volt_steps.value(),
                                                         "FreqSteps": self.single_strip.freq_steps.value(),
                                                         "Strip": self.single_strip.which_strip.value()
                                                         }}})

        # if any other measuremnt should be conducted
        else:
            todo_dict = {}
            if self.single_strip.do_idark.isChecked():
                todo_dict.update({"Idark": True})
            if self.single_strip.do_rpoly.isChecked():
                todo_dict.update({"Rpoly": True})
            if self.single_strip.do_idiel.isChecked():
                todo_dict.update({"Idiel": True})
            if self.single_strip.do_istrip.isChecked():
                todo_dict.update({"Istrip": True})
            #if self.single_strip.do_istrip_over.isChecked():
            #    todo_dict.update({"Istrip_over": True})

            self.final_job.update({"stripscan": {"StartVolt": 0,
                                                  "EndVolt": self.single_strip.max_voltage_strip.value(),
                                                  "Steps": self.single_strip.voltage_steps_strip.value(),
                                                  "Complience": self.single_strip.complience_strip.value(),
                                                  "Save_data": True,
                                                  "singlestrip":{"Measurements": todo_dict, "Strip": self.single_strip.which_strip.value()}
                                                  }
                                   }
                                  )

        # Check if filepath is a valid path
        if self.variables.default_values_dict["Defaults"]["Current_filename"] and os.path.isdir(self.variables.default_values_dict["Defaults"]["Current_directory"]):
            self.final_job.update({"Header": header})
            self.variables.message_from_main.put({"Measurement": self.final_job})
            print "Sendet job: " + str({"Measurement": self.final_job})
        else:
            l.error("Please enter a valid path and name for the measurement file.")
            print "Please enter a valid path and name for the measurement file."

    def stop_button_action(self):
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.variables.message_to_main.put(order)
