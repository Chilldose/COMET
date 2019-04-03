import logging
from PyQt5.QtWidgets import *
from time import asctime
import os
from .Environement_widget import Environement_widget
from .Table_widget import Table_widget
from .Controls_widget import Controls_widget
from .SettingsControl_widget import SettingsControl_widget

class QTCMain_window(Environement_widget, SettingsControl_widget, Table_widget, Controls_widget):

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.job = measurement_job_generation(self.variables.default_values_dict, self.variables.message_from_main)

        # Style for the pyqtgraph plots
        self.ticksStyle = {"pixelsize": 10}
        self.labelStyle = {'color': '#FFF', 'font-size': '18px'}
        self.titleStyle = {'color': '#FFF', 'size': '15pt'}

        # Dynamic waiting time detection tab
        test = QWidget()
        self.dynamic = self.variables.load_QtUi_file("QTC_Main.ui", test)
        self.layout.addWidget(test)

        super(QTCMain_window, self).__init__(self.dynamic)

class measurement_job_generation:
    """This class handles all measurement generation items"""

    def __init__(self, main_variables, queue_to_measurement_event_loop):
        """

        :param main_variables: Simply the state machine variables ('defaults')
        :param queue_to_measurement_event_loop:
        """
        self.variables = main_variables["settings"]
        self.queue_to_measure = queue_to_measurement_event_loop
        self.final_job = {}
        self.log = logging.getLogger(__name__)

    def generate_job(self, additional_settings_dict):
        '''
        This function handles all the work need to be done in order to generate a job
        :param additional_settings_dict: If any additional settings are in place
        '''

        self.final_job = additional_settings_dict


        header = "# Measurement file: \n " \
                      "# Project: " + self.variables["Current_project"]  + "\n " \
                      "# Sensor Type: " + self.variables["Current_sensor"]  + "\n " \
                      "# ID: " + self.variables["Current_filename"] + "\n " \
                      "# Operator: " + self.variables["Current_operator"] + "\n " \
                      "# Date: " + str(asctime()) + "\n\n"

        IVCV_dict = self.generate_IVCV("") # here additional header can be added
        strip_dict = self.generate_strip("")

        if IVCV_dict:
            self.final_job.update({"IVCV": IVCV_dict})
        if strip_dict:
            self.final_job.update({"stripscan": strip_dict})

        # Check if filepath is a valid path
        if self.variables["Current_filename"] and os.path.isdir(self.variables["Current_directory"]):
            self.final_job.update({"Header": header})
            self.queue_to_measure.put({"Measurement": self.final_job})
            self.log.info("Sendet job: " + str({"Measurement": self.final_job}))
        else:
            self.log.error("Please enter a valid path and name for the measurement file.")

    def generate_IVCV(self, header):
        '''
        This function generates all that has to do with IV or CV
        :param header: An additional header
        :return: the job dictionary
        '''
        final_dict = {}
        file_header = header

        if self.variables["IV_measure"][0]:
            file_header += "voltage[V]".ljust(24) +  "current[A]".ljust(24)
        if self.variables["CV_measure"][0]:
            file_header += "voltage[V]".ljust(24) + "capacitance[F]".ljust(24)

        file_header += "temperature[deg]".ljust(24) + "humidity[rel%]".ljust(24)

        final_dict.update({"header": file_header})

        if self.variables["IV_measure"][0]:
            values = self.variables["IV_measure"]
            final_dict.update({"IV": {"StartVolt": 0, "EndVolt": values[1], "Complience": str(values[2])+ "e-6", "Steps": values[3]}})

        if self.variables["CV_measure"][0]:
            values = self.variables["CV_measure"]
            final_dict.update({"CV": {"StartVolt": 0, "EndVolt": values[1], "Complience": str(values[2])+ "e-6", "Steps": values[3]}})

        if len(final_dict) > 1:
            return final_dict
        else:
            return {} # If the dict consits only of one element (only the header)

    def generate_strip(self, header):
        '''
        This function generate all tha has to do with strip scans
        :param header: Additional header
        :return: strip job dictionary
        '''

        final_dict = {}
        all_measurements = ["Rint", "Istrip", "Idiel", "Rpoly","Cac", "Cint", "Idark", "Cback", "CintAC"] # warning if this is not included here no job will generated. is intentional

        def generate_dict(values):
            ''' Generates a simple dict for strip scan measurements'''
            if values[0]: # Checks if the checkbox is true or false, so if the measurement should be condcuted or not
                return {"measure_every": values[1], "start_strip": values[2], "end_strip": values[3]}
            else:
                return {}

        # First check if strip scan should be done or not
        if self.variables["Stripscan_measure"][0]:
            final_dict.update({"StartVolt": 0, "EndVolt": self.variables["Stripscan_measure"][1], "Complience": str(self.variables["Stripscan_measure"][2])+ "e-6", "Steps": self.variables["Stripscan_measure"][3]})

            for elemets in all_measurements:
                dict = generate_dict(self.variables[elemets + "_measure"])
                if dict:
                    final_dict.update({elemets: dict})

        final_dict.update({"Additional Header": header})

        if len(final_dict) > 2:
            return final_dict
        else:
            return {} # If the dict consits only of one element (only the header)









