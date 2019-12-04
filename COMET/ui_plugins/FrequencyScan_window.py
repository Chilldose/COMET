import logging
from PyQt5.QtWidgets import *
from .SettingsControl_widget import SettingsControl_widget
from .Controls_widget import Controls_widget
from ..utilities import change_axis_ticks
from time import sleep


class FrequencyScan_window(Controls_widget,SettingsControl_widget):

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)

        # Style for the pyqtgraph plots
        self.ticksStyle = {"pixelsize": 10}
        self.labelStyle = {'color': '#FFF', 'font-size': '15px'}
        self.titleStyle = {'color': '#FFF', 'size': '18px'}

        # Settings Main tab
        self.FreqWidget = QWidget()
        self.SettingsGui = self.variables.load_QtUi_file("Frequencyscan.ui", self.FreqWidget)
        self.layout.addWidget(self.FreqWidget)

        self.generate_job = self.get_measurement_job_generation_function  # for the gui element with the start button

        # Define the layouts for the individual plugins
        self.child_layouts = {"Settings": self.SettingsGui.Settings_verticalLayout,
                              "Start": self.SettingsGui.Start_Stop_verticalLayout}
        super(FrequencyScan_window, self).__init__(self)

        self.settings_widget.select_settings_comboBox.currentTextChanged.connect(self.check_configs)
        self.settings_widget.select_settings_comboBox.currentTextChanged.connect(self.config_plot)
        self.SettingsGui.Plot_comboBox.currentTextChanged.connect(self.config_plot)
        self.config_plot()

    def update_plot(self):
        # This clear here erases all data from the viewbox each time this function is called and draws all points again!
        # Without this old plot data will still be visible and redrawn again! High memory usage and cpu usage
        # With the clear statement medium cpu und low memory usage
        if self.variables.default_values_dict["settings"]["new_data"]:
            plottitle = self.SettingsGui.Plot_comboBox.currentText()
            if len(self.variables.meas_data["{}_freq".format(plottitle)][0]) == len(
                    self.variables.meas_data["{}_freq".format(plottitle)][1]):  # sometimes it happens that the values are not yet ready
                self.iv_plot.plot(self.variables.meas_data["IV"][0], self.variables.meas_data["IV"][1], pen="y",
                                clear=True)

    def check_configs(self):
        """Looks for a MeasurementConfig tab and renders the Frequencyscan group,
         if stated otherwise warning will be raised"""
        self.SettingsGui.Plot_comboBox.clear()
        if not "MeasurementConfig_window" in self.variables.ui_plugins:
            self.log.error("Could not find MeasurementConfigs widget, please reload...")
            return False

        if "Frequency Scan" in self.variables.ui_plugins["MeasurementConfig_window"].ui_groups:
            keys = list(self.variables.ui_plugins["MeasurementConfig_window"].ui_groups["Frequency Scan"].keys())
            for key in keys:
                if key != "Group_Ui" and key != "General":
                    self.SettingsGui.Plot_comboBox.addItem(key)
        return True

    def get_measurement_job_generation_function(self):
        """Gets the measurement job generation function.

        The MeasurementConfig UI has an function which returns a dict containing all information for IVCV and stripscan
        measurements. This GUI has to be rendered, otherwise this will fail after some time"""
        try:
            fun =  self.variables.ui_plugins["MeasurementConfig_window"].generate_job_for_group
            Freq = fun("Frequency Scan")
            if Freq:
                return Freq
            else:
                self.log.critical("Frequency scan job generation failed, please make sure the settings are correct...")
        except KeyError:
            self.log.error("The GUI MesaurementConfig must be present and redered. Otherwise no job generation possible.")
            return {}

    def config_plot(self):
        plot = self.SettingsGui.freqPlot_graphicsView
        self.plot = plot
        plottitle = self.SettingsGui.Plot_comboBox.currentText()
        plot.setTitle("Frequency Scan Plot: {}".format(plottitle), **self.titleStyle)
        plot.setLabel('left', "Capacitance", units='F', **self.labelStyle)
        plot.setLabel('bottom', "Frequency", units='Hz', **self.labelStyle)
        plot.showAxis('right', show=True)
        plot.showGrid(x=True, y=True)
        plot.plotItem.setLogMode(x=True)

        change_axis_ticks(plot, self.ticksStyle)
        plot.plot(pen="#cddb32")

