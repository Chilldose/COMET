import os
import os.path as osp
import sys, importlib, logging

import numpy as np
import pyqtgraph as pq
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from random import randint
import time

from .. import utilities

l = logging.getLogger(__name__)
hf = utilities.help_functions()

class DynamicWaiting_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout

        self.setpg = pq
        self.voltage_step = 0
        # Generate Colormap for plots
        self.cmap = self.setpg.ColorMap([1.0, 2.0, 3.0], [[0, 0, 255, 255], [0, 255, 0, 255], [255, 0, 0, 255]])
        self.cmapLookup = self.cmap.getLookupTable(0.0,1.0,1)

        # Dynamic waiting time detection tab
        dynamic = QWidget()
        self.dynamic = self.variables.load_QtUi_file("./modules/QT_Designer_UI/dynamicwaiting.ui", dynamic)
        self.layout.addWidget(dynamic)

        # Config the plots and init everything
        self.plot_config()
        self.update_stats()

        # Connect the buttons etc to actual functions
        self.dynamic.change_directory.clicked.connect(self.output_dir_change_action)
        self.dynamic.StartButton.clicked.connect(self.start_button_action)
        self.dynamic.StopButton.clicked.connect(self.stop_button_action)

        # Give the Output a default value
        self.dynamic.output_directory.setText("C:\\Users\\dbloech\\PycharmProjects\\Doktorat\\QTC-Software\\UniDAQ\\rubbish")
        self.dynamic.output_file.setText("test.txt")

        # Add the plot function to the framework
        self.variables.add_update_function(self.update)


        # Add tooltip functionality
        self.tooltip = utilities.show_cursor_position(self.dynamic.current_plot)
        #self.proxy = self.setpg.SignalProxy(self.dynamic.current_plot.scene().sigMouseMoved, rateLimit=60, slot=self.tooltip.onMove)


    def plot_config(self):
        '''This function configurates the plot'''
        self.dynamic.current_plot.setTitle("Dynamic IV waiting time analysis")
        self.dynamic.current_plot.setLabel('left', "current", units='A')
        self.dynamic.current_plot.setLabel('bottom', "time", units='s')
        self.dynamic.current_plot.showAxis('top', show=True)
        self.dynamic.current_plot.showAxis('right', show=True)
        self.dynamic.current_plot.plotItem.showGrid(x=True, y=True)
        self.dynamic.current_plot.getPlotItem().invertY(True)

    def update_stats(self):
        """This function updates the progress bar"""
        self.dynamic.progressBar.setValue(float(self.voltage_step)/float(self.dynamic.max_voltage_IV.value()))

    def output_dir_change_action(self):
        """Writes the outputfilename to the corresponding box"""
        fileDialog = QFileDialog()
        directory = fileDialog.getExistingDirectory()
        self.dynamic.output_directory.setText(directory)

    def start_button_action(self):
        """Starts the measurement for dynamic waiting time"""
        if self.dynamic.output_file.text() and os.path.isdir(self.dynamic.output_directory.text()):

            additional_settings = {"Save_data": True,
                                   "Filepath": self.dynamic.output_directory.text(),
                                   "Filename": self.dynamic.output_file.text(),
                                   "skip_init": False}

            # Generate a Lookuptable for the plots
            steps = int(abs(float(self.dynamic.max_voltage_IV.value())/float(self.dynamic.voltage_steps_IV.value())))+1
            self.cmapLookup = self.cmap.getLookupTable(1.0,3.0, steps)
            self.variables.reset_plot_data()

            self.generate_dynamicwaiting_job(additional_settings)
            #self.variables.reset_plot_data()

        else:
            reply = QMessageBox.information(None, 'Warning', "Please enter a valid filepath and filename.", QMessageBox.Ok)



    def stop_button_action(self):
        """Stops the measurement"""
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.variables.message_to_main.put(order)

    def generate_dynamicwaiting_job(self, additional_settings_dict):

        self.final_job = additional_settings_dict

        header = "# Measurement file: \n " \
                 "# Campaign: " + self.variables.default_values_dict["Defaults"]["Current_project"] + "\n " \
                 "# Sensor Type: " + self.variables.default_values_dict["Defaults"]["Current_sensor"] + "\n " \
                 "# ID: " + self.variables.default_values_dict["Defaults"]["Current_filename"] + "\n " +\
                 "# Operator: " + self.variables.default_values_dict["Defaults"]["Current_operator"] + "\n " \
                 "# Date: " + str(time.asctime()) + "\n\n"



        self.final_job.update({"dynamicwaiting": {"StartVolt": 0,
                                                  "EndVolt": float(self.dynamic.max_voltage_IV.value()),
                                                  "Steps": float(self.dynamic.voltage_steps_IV.value()),
                                                  "Compliance": float(self.dynamic.compliance_IV.value()),
                                                  "Samples": float(self.dynamic.samples_spinBox.value()),
                                                  "Interval": float(self.dynamic.interval_spinbox.value()),
                                                  "NPLC": float(self.dynamic.NPLC_spinbox.value()),
                                                  "Delay": float(self.dynamic.delay_spinbox.value()),
                                                  "Save_data": True,
                                                  }
                                   }
                                  )
        self.final_job.update({"Header": header})
        self.variables.message_from_main.put({"Measurement": self.final_job})
        l.info("Sendet job: " + str({"Measurement": self.final_job}))
        print "Sendet job: " + str({"Measurement": self.final_job})

    @hf.raise_exception
    def update(self, kwargs=None):
        if self.variables.default_values_dict["Defaults"]["new_data"]:
            try:
                self.dynamic.current_plot.clear()
                for i, vstepdata in enumerate(self.variables.meas_data["dynamicwaiting"][0]):
                    if vstepdata.any(): # To exclude exception spawning when measurement is not conducted
                        self.dynamic.current_plot.plot(vstepdata, self.variables.meas_data["dynamicwaiting"][1][i], pen=self.setpg.mkPen(tuple(self.cmapLookup[i])))
                        # Todo: Update the progress bar


            except Exception as e:
                l.warning("An exception in the Dynamic waiting time plot occured, with error {error!s}".format(error=e))



