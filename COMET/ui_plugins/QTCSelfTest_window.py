import logging
from PyQt5.QtWidgets import QWidget, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QUrl, Qt
from PyQt5 import QtGui
from PyQt5 import QtCore

import pyqtgraph as pq
from ..utilities import change_axis_ticks, show_cursor_position
import numpy as np
import time


class QTCSelfTest_window:
    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.settings = self.variables.framework["Configs"]["config"]["settings"]
        self.bins = 10

        # Device communication widget
        self.testWidget = QWidget()
        self.widget = self.variables.load_QtUi_file("SQCTest.ui", self.testWidget)
        self.layout.addWidget(self.testWidget)

        # Raw init of pyqtplots
        self.setpg = pq
        self.ticksStyle = {"pixelsize": 10}
        self.labelStyle = {"color": "#FFF", "font-size": "24px"}
        self.titleStyle = {"color": "#FFF", "size": "15pt"}

        # Asign the buttons
        self.widget.reload_pushButton.clicked.connect(self.update_plot_selection)
        self.widget.Button_changeoutput.clicked.connect(self.output_dir_action)
        self.widget.Slider_bins.valueChanged.connect(self.update_bins)
        self.widget.which_measurement.activated[str].connect(self.update_plot)
        self.widget.start_button.clicked.connect(self.Start_action)

        self.update_stats()
        self.update_bins()
        self.plot_config()
        self.variables.add_update_function(self.update_plot)
        self.variables.add_update_function(self.update_stats)

        # Set progressbar maximum
        self.widget.Overall_progressBar.setMaximum(100)
        self.widget.partial_progressBar.setMaximum(100)

    def update_stats(self):
        """Updates the stats"""
        if "QTC_test" in self.settings and self.settings.get(
            "Measurement_running", False
        ):
            # Set text label
            self.widget.report_label.setText(self.settings["QTC_test"]["text"])

            # Set progress bars
            self.widget.Overall_progressBar.setValue(
                self.settings["QTC_test"]["overallprogress"] * 100
            )
            self.widget.partial_progressBar.setValue(
                self.settings["QTC_test"]["partialprogress"] * 100
            )
            self.widget.label_partial.setText(
                "Progress: {}".format(self.settings["QTC_test"]["currenttest"])
            )

    def plot_config(self):
        """This function configurates the strip plot"""
        self.widget.strip_plot.setTitle("No measurement selected", **self.titleStyle)
        self.widget.strip_plot.showAxis("top", show=True)
        self.widget.strip_plot.showAxis("right", show=True)
        self.widget.strip_plot.plotItem.showGrid(x=True, y=True)

        # self.badstrip.badstrip_plot.plotItem.setLogMode(False, True)
        # Force x-axis to be always auto-scaled
        self.widget.strip_plot.setMouseEnabled(x=False)
        self.widget.strip_plot.enableAutoRange(x=True)
        self.widget.strip_plot.enableAutoRange(y=True)

        # Add tooltip functionality
        self.tooltip = show_cursor_position(self.widget.strip_plot)

        self.widget.strip_plot_histogram.setTitle(
            "Histogram on: No measurement selected", **self.titleStyle
        )
        self.widget.strip_plot_histogram.showAxis("top", show=True)
        self.widget.strip_plot_histogram.showAxis("right", show=True)
        self.widget.strip_plot_histogram.plotItem.showGrid(x=True, y=True)

        change_axis_ticks(self.widget.strip_plot, self.ticksStyle)
        change_axis_ticks(self.widget.strip_plot_histogram, self.ticksStyle)

    def output_dir_action(self):
        """Changing the output directory file"""
        fileDialog = QFileDialog()
        directory = fileDialog.getExistingDirectory()
        self.output_directory = str(directory)
        self.widget.label_output.setText(str(directory))
        self.log.info("Changed analysis output file to: " + str(directory))

    def update_bins(self):
        """Updates the bins for the histogram"""
        self.bins = self.widget.Slider_bins.value()
        self.update_plot()

    def update_plot_selection(self):
        """Updates the possible plot selection"""
        if "QTC_test" in self.settings:
            # Set text label
            self.widget.which_measurement.clear()
            data = self.settings["QTC_test"]["data"]
            self.widget.which_measurement.addItems(data.get("Empty", {}).keys())
            self.widget.which_measurement.addItems(data.get("TestCard", {}).keys())
            self.update_plot()

    def update_plot(self):
        """This handles the update of the plot"""
        # This clear here erases all data from the viewbox each time this function is called and draws all points again!
        # Without this old plot data will still be visible and redrawn again! High memory usage and cpu usage
        # With the clear statement medium cpu und low memory usage
        measurement = self.widget.which_measurement.currentText()
        if measurement and self.variables.default_values_dict["settings"]["new_data"]:
            branch = "Empty" if measurement in self.settings["QTC_test"]["data"]["Empty"] else "TestCard"
            if not branch or not measurement:
                return

            ydata = self.settings["QTC_test"]["data"][branch][measurement][
                np.nonzero(self.settings["QTC_test"]["data"][branch][measurement])[0]
            ]
            xdata = np.array(range(len(ydata)))

            self.reconfig_plot(
                measurement,
                measurement,
                unit=self.settings["QTC_test"]["data"]["units"][measurement],
            )
            if ydata.any():  # Checks if data is available or if all is empty
                if len(xdata) == len(
                    ydata
                ):  # sometimes it happens that the values are not yet ready (fucking multithreading)

                    # Make the normal line Plot
                    self.widget.strip_plot.plot(
                        xdata, ydata, pen="r", clear=True, width=8, connect="finite"
                    )

                    # Make the histogram of the data
                    x, y = np.histogram(ydata, bins=self.bins)
                    self.widget.strip_plot_histogram.plot(
                        y,
                        x,
                        stepMode=True,
                        fillLevel=0,
                        brush=(0, 0, 255, 80),
                        clear=True,
                        connect="finite",
                    )
            else:
                self.widget.strip_plot.clear()
                self.widget.strip_plot_histogram.clear()

            # self.widget.strip_plot.enableAutoRange(y=True)
            # self.tooltip = show_cursor_position(self.widget.strip_plot)
            return  # self.widget.strip_plot, self.widget.strip_plot_histogram

    def reconfig_plot(self, Title, ylabel, unit):
        """Reconfigs the plot for the different plots
        :param - Title must be string, containing the name of the plot (title)
        :param - plot_settings must be a tuple consisting elements like it is in the config defined
                        "Idark": (["Strip", "#"], ["Current", "A"], [False, False], True)
        """
        self.widget.strip_plot.setTitle(str(Title), **self.titleStyle)
        self.widget.strip_plot.setLabel(
            "bottom", "Number", units="#", **self.labelStyle
        )
        self.widget.strip_plot.setLabel("left", ylabel, units=unit, **self.labelStyle)

        self.widget.strip_plot_histogram.setTitle(
            "Histogram on: " + str(Title), **self.titleStyle
        )
        self.widget.strip_plot_histogram.setLabel(
            "left", "Count", units="#", **self.labelStyle
        )
        self.widget.strip_plot_histogram.setLabel(
            "bottom", ylabel, units=unit, **self.labelStyle
        )

    def Start_action(self):
        """Starts the QTC test"""
        self.final_job = {}
        header = (
            "# Measurement file: \n "
            "# Operator: "
            + self.variables.default_values_dict["settings"]["Current_operator"]
            + "\n "
            "# Date: " + str(time.asctime()) + "\n\n"
        )

        self.final_job.update({"QTCTESTSYSTEM": {"Samples": 1000,}})
        self.final_job.update({"Header": header, "Save_data": True, "Filename": "SELFTEST", "Filepath": self.widget.label_output.text()})
        self.variables.message_from_main.put({"Measurement": self.final_job})
        self.log.info("Sendet job: " + str({"Measurement": self.final_job}))
