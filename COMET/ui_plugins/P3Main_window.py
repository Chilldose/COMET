import logging
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from time import asctime
import os
from .Environement_widget import Environement_widget
from .Table_widget import Table_widget
from .Controls_widget import Controls_widget
from .SettingsControl_widget import SettingsControl_widget
from ..utilities import change_axis_ticks#, KeyPress
from .settings_widget import settings_widget

class P3Main_window(Environement_widget, SettingsControl_widget, Controls_widget, settings_widget):

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.job = measurement_job_generation(self, self.variables.default_values_dict, self.variables.message_from_main)
        #self.keyPressEvent = KeyPress(self.variables.framework_variables["App"], self.on_key_press, [QtCore.Qt.Key_Q])

        self.iv_plot = None
        self.cv_plot = None

        # Style for the pyqtgraph plots
        self.ticksStyle = {"pixelsize": 10}
        self.labelStyle = {'color': '#FFF', 'font-size': '15px'}
        self.titleStyle = {'color': '#FFF', 'size': '18px'}

        # Dynamic waiting time detection tab
        self.Widget = QWidget()
        self.gui = self.variables.load_QtUi_file("P3Main.ui",  self.Widget)
        self.layout.addWidget(self.Widget)

        # Define the layouts for the indicidual plugins
        self.child_layouts = {"Environment": self.gui.environement_control_layout,
                              "Table": self.gui.Table_Layout,
                              "Start": self.gui.controls_layout,
                              "Settings": self.gui.settings_layout}

        self.config_IV_plot()
        self.config_CV_plot()

        super(P3Main_window, self).__init__(self.gui)

        self.variables.add_update_function(self.update_IVplot)
        self.variables.add_update_function(self.update_CVplot)

        # Upadte the settings when a change is made
        self.gui.max_voltage_2.valueChanged.connect(self.update_settings)
        self.gui.compliance_2.valueChanged.connect(self.update_settings)
        self.gui.voltage_steps_2.valueChanged.connect(self.update_settings)
        self.gui.min_refine_spin_2.valueChanged.connect(self.update_settings)
        self.gui.max_refine_spin_2.valueChanged.connect(self.update_settings)
        self.gui.refine_step_spin_2.valueChanged.connect(self.update_settings)
        self.gui.doIV_checkBox_2.clicked.connect(self.update_settings)
        self.gui.doCV_checkBox_2.clicked.connect(self.update_settings)
        self.gui.doRef_checkBox_2.clicked.connect(self.update_settings)


    def update_settings(self):
        """
        Updates the settings for IV and CV measurements
        :return: None
        """

        # Load the IVCV and refinement settings into the statemachine
        # IV
        self.load_new_values("IV_measure",
                                                                         self.gui.doIV_checkBox_2, self.gui.max_voltage_2,
                                                                         self.gui.compliance_2, self.gui.voltage_steps_2)

        # CV
        self.load_new_values("CV_measure", self.gui.doCV_checkBox_2,
                                                                         self.gui.max_voltage_CV,
                                                                         self.gui.compliance_2,
                                                                         self.gui.voltage_steps_2)

        # Refinement
        self.load_new_values("IVCV_refinement", self.gui.doRef_checkBox_2,
                                                                         self.gui.min_refine_spin_2,
                                                                         self.gui.max_refine_spin_2,
                                                                         self.gui.refine_step_spin_2)

    def on_key_press(self, key):
        print("here")

    def config_IV_plot(self):

        iv_plot = self.gui.IV_plot
        self.iv_plot = iv_plot
        iv_plot.setTitle("IV curve (top) and CV curve (bottom)", **self.titleStyle)
        iv_plot.setLabel('left', "current", units='A', **self.labelStyle)
        #iv_plot.setLabel('bottom', "voltage", units='V', **self.labelStyle)
        #iv_plot.showAxis('top', show=True)
        iv_plot.showAxis('right', show=True)
        iv_plot.showAxis('bottom', show=False)
        iv_plot.getPlotItem().invertX(True)
        iv_plot.getPlotItem().invertY(True)
        iv_plot.showGrid(x=True, y=True)

        change_axis_ticks(iv_plot, self.ticksStyle)
        iv_plot.plot(pen="#cddb32")

    def update_IVplot(self):
        # This clear here erases all data from the viewbox each time this function is called and draws all points again!
        # Without this old plot data will still be visible and redrawn again! High memory usage and cpu usage
        # With the clear statement medium cpu und low memory usage
        if self.variables.default_values_dict["settings"]["new_data"]:
            if len(self.variables.meas_data["IV"][0]) == len(
                    self.variables.meas_data["IV"][1]):  # sometimes it happens that the values are not yet ready
                self.iv_plot.plot(self.variables.meas_data["IV"][0], self.variables.meas_data["IV"][1], pen="y",
                                clear=True)

    def config_CV_plot(self):
        cv_plot = self.gui.CV_plot
        self.cv_plot = cv_plot
        #cv_plot.setTitle("IV curve", **self.titleStyle)
        cv_plot.setLabel('left', "1/c^2", units='arb. units', **self.labelStyle)
        cv_plot.setLabel('bottom', "voltage", units='V', **self.labelStyle)
        #cv_plot.showAxis('top', show=True)
        cv_plot.showAxis('right', show=True)
        cv_plot.getPlotItem().invertX(True)
        cv_plot.showGrid(True, True)

        #cv_plot.setMinimumHeight(350)
        #cv_plot.setMaximumHeight(350)

        change_axis_ticks(cv_plot, self.ticksStyle)

    def depletion_volt(self, value):
        if value != 0:
            return 1. / (value * value)
        else:
            return value

    def update_CVplot(self):
        if self.variables.default_values_dict["settings"]["new_data"]:
            if len(self.variables.meas_data["CV"][0]) == len(
                    self.variables.meas_data["CV"][1]):  # sometimes it happens that the values are not yet ready
                self.cv_plot.plot(self.variables.meas_data["CV"][0],
                                list(map(self.depletion_volt, self.variables.meas_data["CV"][1])), pen="y", clear=True)



class measurement_job_generation:
    """This class handles all measurement generation items"""

    def __init__(self, IVCV_obj, main_variables, queue_to_measurement_event_loop):
        """

        :param main_variables: Simply the state machine variables ('defaults')
        :param queue_to_measurement_event_loop:
        """
        self.variables = main_variables["settings"]
        self.queue_to_measure = queue_to_measurement_event_loop
        self.final_job = {}
        self.log = logging.getLogger(__name__)
        self.IVCV_obj = IVCV_obj

    def generate_job(self, additional_settings_dict):
        '''
        This function handles all the work need to be done in order to generate a job
        :param additional_settings_dict: If any additional settings are in place
        '''

        self.final_job = additional_settings_dict
        self.IVCV_obj.update_settings()


        header = "# Measurement file: \n " \
                      "# Project: " + self.variables["Current_project"]  + "\n " \
                      "# Sensor Type: " + self.variables["Current_sensor"]  + "\n " \
                      "# ID: " + self.variables["Current_filename"] + "\n " \
                      "# Operator: " + self.variables["Current_operator"] + "\n " \
                      "# Date: " + str(asctime()) + "\n\n"

        IVCV_dict = self.generate_IVCV("") # here additional header can be added

        if IVCV_dict:
            self.final_job.update({"IVCV": IVCV_dict})

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
        final_dict["header"]= file_header

        if self.variables["IV_measure"][0]:
            values = self.variables["IV_measure"]
            final_dict.update({"IV": {"StartVolt": 0, "EndVolt": values[1], "compliance": str(values[2])+ "e-6", "Steps": values[3]}})

        if self.variables["CV_measure"][0]:
            values = self.variables["CV_measure"]
            final_dict.update({"CV": {"StartVolt": 0, "EndVolt": values[1], "compliance": str(values[2])+ "e-6", "Steps": values[3]}})

        if self.variables["IVCV_refinement"][0]:
            values = self.variables["IVCV_refinement"]
            final_dict.update({"IVCV_refinement": {"Min": values[1], "Max": values[2], "Step": values[3]}})

        if len(final_dict) > 1:
            return final_dict
        else:
            return {} # If the dict consits only of one element (only the header)
