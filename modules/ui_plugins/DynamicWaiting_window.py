import logging
import os
import time

import pyqtgraph as pq
from PyQt5.QtWidgets import *

from .. import utilities

l = logging.getLogger(__name__)
hf = utilities.help_functions()

class DynamicWaiting_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout

        self.setpg = pq
        self.voltage_step = 0

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

    def plot_config(self):
        '''This function configurates the plot'''
        self.dynamic.current_plot.setTitle("Dynamic IV waiting time analysis")
        self.dynamic.current_plot.setLabel('left', "current", units='A')
        self.dynamic.current_plot.setLabel('bottom', "voltage", units='V')
        self.dynamic.current_plot.showAxis('top', show=True)
        self.dynamic.current_plot.showAxis('right', show=True)
        self.dynamic.current_plot.plotItem.showGrid(x=True, y=True)

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
                                                  "EndVolt": float(self.dynamic.complience_IV.value()),
                                                  "Steps": float(self.dynamic.complience_IV.value()),
                                                  "Complience": float(self.dynamic.complience_IV.value()),
                                                  "num_of_points": 30,
                                                  "Save_data": True,
                                                  }
                                   }
                                  )
        self.final_job.update({"Header": header})
        self.variables.message_from_main.put({"Measurement": self.final_job})
        l.info("Sendet job: " + str({"Measurement": self.final_job}))
        print "Sendet job: " + str({"Measurement": self.final_job})



