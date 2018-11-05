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

from .. import utilities

l = logging.getLogger(__name__)
hf = utilities.help_functions()

class StripAnalysis_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.measurement_dict = {"Idark": (["Pad", "#"], ["Current", "A"], [False, False], True),
                                 "Idiel": (["Pad", "#"], ["Current", "A"], [False, False], True),
                                 "Istrip": (["Pad", "#"], ["Current", "A"], [False, False], True),
                                 "Rpoly": (["Pad", "#"], ["Resistance", "Ohm"], [False, False], False),
                                 "Rint": (["Pad", "#"], ["Resistance", "Ohm"], [False, False], False),
                                 "Cac": (["Pad", "#"], ["Capacitance", "F"], [False, False], False),
                                 "Cint": (["Pad", "#"], ["Capacitance", "F"], [False, False], False),
                                 "Cback": (["Pad", "#"], ["Capacitance", "F"], [False, False], False),
                                 "Humidity": (["Pad", "#"], ["Humidity", "relH"], [False, False], False),
                                 "Temperature": (["Pad", "#"], ["Termperature", "C"], [False, False], False)
                                 }

        #self.plot_data = {"QTC":{"data": {"ab": 2}},
        #                  "QTC2": {"data": {"ab": 2, "c": 2, "b": 2}}} # should be a tree structure of dictionaries containig all data loaded, this must be the object from the bad strip detection!!!
        self.plot_data = self.variables.analysis.all_data
        self.output_directory = self.variables.default_values_dict["Badstrip"].get("output_folder", str(os.getcwd()))
        self.bins = 100
        self.setpg = pq
        self.pdf_viewbox = self.setpg.ViewBox()

        # Badstrip detection tab
        badstrip = QWidget()
        self.badstrip = self.variables.load_QtUi_file("./modules/QT_Designer_UI/Badstrip.ui", badstrip)
        self.layout.addWidget(badstrip)

        # Config the plots and init everything
        self.plot_config()
        self.update_stats()

        # Asign the buttons
        self.badstrip.Button_changeload.clicked.connect(self.load_measurement_action)
        self.badstrip.Button_changeload.clicked.connect(self.update_stats)
        self.badstrip.Button_changeload.clicked.connect(self.update_meas_selector)

        self.badstrip.Button_changeoutput.clicked.connect(self.output_dir_action)
        self.badstrip.Button_changeoutput.clicked.connect(self.update_stats)

        self.badstrip.which_plot.activated[str].connect(self.update_analysis_plots)
        self.badstrip.Slider_bins.valueChanged.connect(self.update_bins)
        self.badstrip.which_measurement.activated[str].connect(self.update_plot)
        self.badstrip.cb_Save_results.clicked.connect(self.export_action)
        self.badstrip.cb_Save_plots.clicked.connect(self.export_action)
        self.badstrip.analyse_button.clicked.connect(self.analyse_action)


    def analyse_action(self):
        """This starts the analysis of the loaded measurements"""
        self.variables.analysis.do_analysis()
        measurement = self.badstrip.which_measurement.currentText()
        self.update_plot(measurement)


    def export_action(self):
        self.variables.default_values_dict["Badstrip"]["export_results"] = self.badstrip.cb_Save_results.isChecked()
        self.variables.default_values_dict["Badstrip"]["export_plot"] = self.badstrip.cb_Save_plots.isChecked()


    @hf.raise_exception
    def update_stats(self, kwargs = None):
        """Updates the text of the loaded files and such shit"""
        self.badstrip.label_output.setText(self.output_directory)
        meas = ""
        for keys in self.plot_data.keys():
            meas += str(keys) + ","

        self.badstrip.cb_Save_plots.setChecked(self.variables.default_values_dict["Badstrip"]["export_plot"])
        self.badstrip.cb_Save_results.setChecked(self.variables.default_values_dict["Badstrip"]["export_results"])

    def update_meas_selector(self):
        """This function updates the combo box selectors for the measurements"""
        self.badstrip.which_plot.clear()
        try:
            self.badstrip.which_plot.addItems(self.plot_data.keys())
            self.update_analysis_plots(self.plot_data.keys()[0])
        except Exception as e:
            l.error("An error occured while accessing data from the bad strip detection: " + str(e))
            print "An error occured while accessing data from the bad strip detection: " + str(e)

    def update_analysis_plots(self, current_item):
        """This function updats the combo box for the specific measurement which should be shown"""
        # First delete all items
        self.badstrip.which_measurement.clear()
        # Then add all new ones
        try:
            # Get the current selected measurement
            self.badstrip.which_measurement.addItems(self.plot_data[current_item]["measurements"][1:])
            self.update_plot(self.badstrip.which_measurement.currentText())
        except Exception as e:
            l.error("An error occured while accessing data from the bad strip detection: " + str(e))
            print "An error occured while accessing data from the bad strip detection: " + str(e)

    def update_bins(self):
        """Updates the bins for the histogram"""
        self.bins = self.badstrip.Slider_bins.value()
        measurement = self.badstrip.which_measurement.currentText()
        self.update_plot(measurement)

    def plot_config(self):
        '''This function configurates the strip plot'''
        self.badstrip.strip_plot.setTitle("Strip results on: No measurement selected")
        self.badstrip.strip_plot.setLabel('left', "current", units='A')
        self.badstrip.strip_plot.setLabel('bottom', "voltage", units='V')
        self.badstrip.strip_plot.showAxis('top', show=True)
        self.badstrip.strip_plot.showAxis('right', show=True)
        self.badstrip.strip_plot.plotItem.showGrid(x=True, y=True)
        #self.badstrip.badstrip_plot.plotItem.setLogMode(False, True)

        self.badstrip.strip_plot_histogram.setTitle("Histogram results on: No measurement selected")
        self.badstrip.strip_plot_histogram.setLabel('left', "count", units='#')
        self.badstrip.strip_plot_histogram.setLabel('bottom', "current", units='A')
        self.badstrip.strip_plot_histogram.showAxis('top', show=True)
        self.badstrip.strip_plot_histogram.showAxis('right', show=True)
        self.badstrip.strip_plot_histogram.plotItem.showGrid(x=True, y=True)

        # For sencond plot item on histogram plot
        plot = self.badstrip.strip_plot_histogram.plotItem
        plot.scene().addItem(self.pdf_viewbox)  # inserts the second plot into the scene of the first
        self.pdf_viewbox.setGeometry(plot.vb.sceneBoundingRect())
        plot.getAxis('right').linkToView(self.pdf_viewbox)  # links the second y axis to the second plot
        self.pdf_viewbox.setXLink(plot)  # sync the x axis of both plots


    def reconfig_plot(self, Title, plot_settings):
        '''Reconfigs the plot for the different plots
        :param - Title must be string, containing the name of the plot (title)
        :param - plot_settings must be a tuple consisting elements like it is in the init defined
                        "Idark": (["Pad", "#"], ["Current", "A"], [False, False], True)
        '''
        self.badstrip.strip_plot.setTitle("Strip results on: " + str(Title))
        self.badstrip.strip_plot.setLabel('bottom', str(plot_settings[0][0]), units=str(plot_settings[0][1]))
        self.badstrip.strip_plot.setLabel('left', str(plot_settings[1][0]), units=str(plot_settings[1][1]))
        self.badstrip.strip_plot.plotItem.setLogMode(x=plot_settings[2][0], y=plot_settings[2][1])
        self.badstrip.strip_plot.getPlotItem().invertY(plot_settings[3])

        self.badstrip.strip_plot_histogram.setTitle("Histogram results on: " + str(Title))
        self.badstrip.strip_plot_histogram.setLabel('left', "Count", units="#")
        self.badstrip.strip_plot_histogram.setLabel('bottom', str(plot_settings[1][0]), units=str(plot_settings[1][1]))
        self.badstrip.strip_plot_histogram.plotItem.setLogMode(x=plot_settings[2][0], y=plot_settings[2][1])
        self.badstrip.strip_plot_histogram.getPlotItem().invertX(plot_settings[3])
        self.pdf_viewbox.invertX(plot_settings[3])

    def update_plot(self, measurement_name):
        '''This handles the update of the plot'''
        # This clear here erases all data from the viewbox each time this function is called and draws all points again!
        # Without this old plot data will still be visible and redrawn again! High memory usage and cpu usage
        # With the clear statement medium cpu und low memory usage
        self.reconfig_plot(measurement_name, self.measurement_dict[measurement_name])
        measurement = self.badstrip.which_plot.currentText()
        ydata = self.plot_data[measurement]["data"][measurement_name]
        xdata = range(len(self.plot_data[measurement]["data"]["Pad"]))
        if ydata: # Checks if data is available or if all is empty
            if len(xdata) == len(ydata):  # sometimes it happens that the values are not yet ready (fucking multithreading)

                # Make the normal line Plot
                self.badstrip.strip_plot.plot(xdata, ydata, pen="r", clear=True, width=8)

                # Make the histogram of the data
                # y, x = np.histogram(np.array(ydata), bins=int(self.bins))
                yout =self.variables.analysis.remove_outliner(ydata)
                x, y = self.variables.analysis.do_histogram(yout, self.bins)
                self.badstrip.strip_plot_histogram.plot(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80), clear=True)

                if self.plot_data[measurement]["analysed"]:
                    anadata = self.plot_data[measurement]["analysis_results"]

                    # Plot Lms line
                    # containst first and last point for the slope y = kx+d
                    k = float(anadata["lms_fit"][measurement_name][0])
                    d = float(anadata["lms_fit"][measurement_name][1])
                    lmsdata = [[0, len(xdata)],[d, k*len(xdata)+d]]
                    self.badstrip.strip_plot.plot(lmsdata[0], lmsdata[1], pen="g")

                    # Plot pdf in the histogram plot
                    pdfdata = anadata["pdf"][measurement_name]
                    self.pdf_viewbox.clear()
                    plot_item = self.setpg.PlotCurveItem(pdfdata[2], pdfdata[3],
                                                    pen={'color': "g", 'width': 2},
                                                    clear=True)
                    self.pdf_viewbox.addItem(plot_item)
                    del plot_item  # the plot class needs a plot item which can be rendered, to avoid a mem leak delete the created plot item or 20k ram will be used
                    # hum_plot_obj.addItem(setpg.plot(self.variables.meas_data["humidity"][0],self.variables.meas_data["humidity"][1],pen={'color': "b", 'width': 2}, clear=True))
                      # resize the second plot!
                    #self.eq_text = self.setpg.TextItem(text="Some text", border='#000000', fill='#ccffff')
                    #self.eq_text.setParentItem(self.pdf_viewbox)
                    #self.eq_text.setPos(pdfdata[2][np.argmax(pdfdata[3])], y.max() * 0.9)
                    self.pdf_viewbox.setGeometry(self.badstrip.strip_plot_histogram.plotItem.vb.sceneBoundingRect())

                    # Update report text
                    self.badstrip.report_lable.setText(anadata["report"][measurement_name])



    def files_selector_action(self):
        """Select files and return the filepointer"""
        fileDialog = QFileDialog()
        fileDialog.setFileMode(QFileDialog.ExistingFiles)
        file = fileDialog.getOpenFileNames()
        return file

    def load_measurement_action(self):
        """Loading measurement files, not analysed"""
        files = self.files_selector_action()
        text = ""
        for i in files[0]:
            text += str(i) + ","
        self.badstrip.label_load.setText(text)
        l.info(str(len(files[0])) + " measurement files have been selected.")

        self.variables.analysis.read_in_measurement_file(files[0])
        self.update_meas_selector()

    def output_dir_action(self):
        """Changing the output directory file"""
        fileDialog = QFileDialog()
        directory = fileDialog.getExistingDirectory()
        self.output_directory = str(directory)
        self.badstrip.label_output.setText(str(directory))
        l.info("Changed analysis output file to: " + str(directory))
