import logging
from PyQt5.QtWidgets import *
from .SettingsControl_widget import SettingsControl_widget
from .Controls_widget import Controls_widget
from ..utilities import change_axis_ticks
from time import sleep
import pyqtgraph as pq
import numpy as np


class FrequencyScan_window(Controls_widget,SettingsControl_widget):

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.setpg = pq
        # Generate Colormap for plots
        self.cmap = self.setpg.ColorMap([1.0, 2.0, 3.0], [[0, 0, 255, 255], [0, 255, 0, 255], [255, 0, 0, 255]])
        self.cmapLookup = self.cmap.getLookupTable(0.0,1.0,1)

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
        #self.settings_widget.select_settings_comboBox.currentTextChanged.connect(self.update_plot)
        self.SettingsGui.Plot_comboBox.currentTextChanged.connect(self.config_plot)
        self.config_plot()

        # Add the plot function to the framework
        self.variables.add_update_function(self.update_plot)

    def update_plot(self, force=False):
        # This clear here erases all data from the viewbox each time this function is called and draws all points again!
        # Without this old plot data will still be visible and redrawn again! High memory usage and cpu usage
        # With the clear statement medium cpu und low memory usage
        if self.variables.default_values_dict["settings"]["new_data"] or force:
            plottitle = self.SettingsGui.Plot_comboBox.currentText()
            datalabel = "{}_freq".format(plottitle)
            try:
                if datalabel in self.variables.meas_data:
                    self.SettingsGui.freqPlot_graphicsView.clear()
                    if self.variables.meas_data[datalabel][0].any():
                        for i, vstepdata in enumerate(self.variables.meas_data[datalabel][0]):
                            if isinstance(vstepdata, np.ndarray):
                                if vstepdata.any():  # To exclude exception spawning when measurement is not conducted
                                    self.SettingsGui.freqPlot_graphicsView.plot(vstepdata, self.variables.meas_data[datalabel][1][i],
                                                                   pen=self.setpg.mkPen(tuple(self.cmapLookup[i])))
                            else:
                                self.SettingsGui.freqPlot_graphicsView.plot(self.variables.meas_data[datalabel][0],
                                                                                self.variables.meas_data[datalabel][1],
                                                                                pen=self.setpg.mkPen(tuple(self.cmapLookup[i])))
                                break

            except Exception as e:
                self.log.error("An exception in the frequency scan plot occured, with error {error!s}".format(error=e))

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

        self.update_plot(force=True)

