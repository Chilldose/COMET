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


from ..utilities import change_axis_ticks, show_cursor_position, raise_exception

l = logging.getLogger(__name__)

class StripAnalysis_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
                                # Label: X-Axis, Y-Axis, Logx, Logy, InvertY
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
        self.ticksStyle = {"pixelsize": 10}
        self.labelStyle = {'color': '#FFF', 'font-size': '24px'}
        self.titleStyle = {'color': '#FFF', 'size': '15pt'}
        #self.pdf_viewbox = self.setpg.ViewBox()

        # Badstrip detection tab
        badstrip = QWidget()
        self.badstrip = self.variables.load_QtUi_file("badstrip.ui", badstrip)
        self.layout.addWidget(badstrip)

        # Config the plots and init everything
        self.plot_config()
        self.update_stats()

        # Set margins of things
        self.badstrip.scrollArea.setContentsMargins(0, 0, 0, 0)
        self.badstrip.report_label.setContentsMargins(0, 0, 0, 0)

        # Asign the buttons
        self.badstrip.Button_changeload.clicked.connect(self.load_measurement_action)
        self.badstrip.Button_changeload.clicked.connect(self.update_stats)
        self.badstrip.Button_changeload.clicked.connect(self.update_meas_selector)

        self.badstrip.Button_changeoutput.clicked.connect(self.output_dir_action)
        self.badstrip.Button_changeoutput.clicked.connect(self.update_stats)

        self.badstrip.which_plot.activated[str].connect(self.update_analysis_plots)
        self.badstrip.Slider_bins.valueChanged.connect(self.update_bins)
        self.badstrip.which_measurement.activated[str].connect(self.update_plot)
        #self.badstrip.cb_Save_results.clicked.connect(self.export_action)
        #self.badstrip.cb_Save_plots.clicked.connect(self.export_action)
        self.badstrip.analyse_button.clicked.connect(self.analyse_action)
        #self.badstrip.save_plots_button.clicked.connect(self.export_plots)


    def update_specs_bars(self, data_label, data):
        """Adds specs bars for the absolute values and median +- values"""
        # Add a ViewBox below with two rectangles
        vb = self.badstrip.strip_plot
        ax = vb.getAxis('bottom').range
        ay = vb.getAxis('left').range

        settings = self.variables.default_values_dict["Badstrip"]
        median = np.median(data[np.logical_not(np.isnan(data))])



        if self.measurement_dict[data_label][3]:
            # If y axis is flipped
            # Absolute values cut
            r1 = self.setpg.QtGui.QGraphicsRectItem(ax[0], float(settings[data_label][1][1]),
                                                    abs(ax[0]-ax[1]), # width
                                            -abs(float(settings[data_label][1][1])-float(settings[data_label][1][0])))
            # Median +- box
            r2 = self.setpg.QtGui.QGraphicsRectItem(ax[0], median * (1 - float(settings[data_label][2]) / 100),
                                                    abs(ax[0] - ax[1]),
                                                    -abs(median * (1 - float(settings[data_label][2]) / 100)-
                                                        median * (1 + float(settings[data_label][2]) / 100)))
        else:
            # If y axis is NOT flipped
            r1 = self.setpg.QtGui.QGraphicsRectItem(ax[0], float(settings[data_label][1][0]),
                                                    abs(ax[0] - ax[1]),  # width
                                                    abs(float(settings[data_label][1][1]) - float(
                                                        settings[data_label][1][0])))
            # Median +- box
            r2 = self.setpg.QtGui.QGraphicsRectItem(ax[0], median * (1 + float(settings[data_label][2]) / 100),
                                                    abs(ax[0] - ax[1]),
                                                    -abs(median * (1 - float(settings[data_label][2]) / 100) -
                                                        median * (1 + float(settings[data_label][2]) / 100)))
        r1.setPen(self.setpg.mkPen(None))
        r1.setOpacity(0.2)
        r1.setBrush(self.setpg.mkBrush('g'))
        vb.addItem(r1)

        r2.setPen(self.setpg.mkPen(None))
        r2.setOpacity(0.2)
        r2.setBrush(self.setpg.mkBrush('y'))
        vb.addItem(r2)

        # Make the ViewBox flat
        #vb.setMaximumHeight(70)

        # Force x-axis to match the plot above
        vb.setXLink(vb)


    def analyse_action(self):
        """This starts the analysis of the loaded measurements"""
        if self.badstrip.which_plot.currentText():

            self.variables.analysis.do_analysis()
            measurement = self.badstrip.which_measurement.currentText()
            self.update_plot(measurement)
            self.update_results_text()


    def export_action(self):
        self.variables.default_values_dict["Badstrip"]["export_results"] = self.badstrip.cb_Save_results.isChecked()
        self.variables.default_values_dict["Badstrip"]["export_plot"] = self.badstrip.cb_Save_plots.isChecked()

    @raise_exception
    def update_results_text(self):
        """Updates the result text for a measurement"""

        # Get selected measurement
        measurement = self.badstrip.which_plot.currentText()
        if "Analysis_conclusion" in self.variables.analysis.all_data[measurement]:
            self.badstrip.report_label.setText(self.variables.analysis.all_data[measurement]["Analysis_conclusion"])
            #self.badstrip.radioData.setChecked(True)
        else:
            self.badstrip.report_label.setText("")
            #self.badstrip.radioData.setChecked(False)
    @raise_exception
    def update_stats(self, kwargs = None):
        """Updates the text of the loaded files and such shit"""
        self.badstrip.label_output.setText(self.output_directory)
        meas = ""
        for keys in self.plot_data.keys():
            meas += str(keys) + ","

        #self.badstrip.cb_Save_plots.setChecked(self.variables.default_values_dict["Badstrip"]["export_plot"])
        #self.badstrip.cb_Save_results.setChecked(self.variables.default_values_dict["Badstrip"]["export_results"])

    def update_meas_selector(self):
        """This function updates the combo box selectors for the measurements"""
        self.badstrip.which_plot.clear()
        try:
            self.badstrip.which_plot.addItems(self.plot_data.keys())
            self.update_analysis_plots(list(self.plot_data.keys())[0])
            self.update_results_text()
        except Exception as e:
            l.error("An error occured during updating measurement selector: " + str(e))

    def update_analysis_plots(self, current_item):
        """This function updats the combo box for the specific measurement which should be shown"""
        # First delete all items
        self.badstrip.which_measurement.clear()
        # Then add all new ones
        try:
            # Get the current selected measurement
            self.badstrip.which_measurement.addItems(self.plot_data[current_item]["measurements"][1:])
            self.update_plot(self.badstrip.which_measurement.currentText())
            self.update_results_text()
        except Exception as e:
            l.error("An error occured while accessing data from the bad strip detection: " + str(e))

    def update_bins(self):
        """Updates the bins for the histogram"""
        self.bins = self.badstrip.Slider_bins.value()
        measurement = self.badstrip.which_measurement.currentText()
        self.update_plot(measurement)

    def plot_config(self):
        '''This function configurates the strip plot'''
        self.badstrip.strip_plot.setTitle("Strip results on: No measurement selected", **self.titleStyle)
        self.badstrip.strip_plot.setLabel('left', "current", units='A', **self.labelStyle)
        self.badstrip.strip_plot.setLabel('bottom', "voltage", units='V', **self.labelStyle)
        self.badstrip.strip_plot.showAxis('top', show=True)
        self.badstrip.strip_plot.showAxis('right', show=True)
        self.badstrip.strip_plot.plotItem.showGrid(x=True, y=True)

        #self.badstrip.badstrip_plot.plotItem.setLogMode(False, True)
        # Force x-axis to be always auto-scaled
        self.badstrip.strip_plot.setMouseEnabled(x=False)
        self.badstrip.strip_plot.enableAutoRange(x=True)
        self.badstrip.strip_plot.enableAutoRange(y=True)

        # Add tooltip functionality
        self.tooltip = show_cursor_position(self.badstrip.strip_plot)

        self.badstrip.strip_plot_histogram.setTitle("Histogram results on: No measurement selected", **self.titleStyle)
        self.badstrip.strip_plot_histogram.setLabel('left', "count", units='#', **self.labelStyle)
        self.badstrip.strip_plot_histogram.setLabel('bottom', "current", units='A', **self.labelStyle)
        self.badstrip.strip_plot_histogram.showAxis('top', show=True)
        self.badstrip.strip_plot_histogram.showAxis('right', show=True)
        self.badstrip.strip_plot_histogram.plotItem.showGrid(x=True, y=True)

        # For second plot item on histogram plot (the pdf of the gauss)
        #plot = self.badstrip.strip_plot_histogram.plotItem
        #plot.scene().addItem(self.pdf_viewbox)  # inserts the second plot into the scene of the first
        #self.pdf_viewbox.setGeometry(plot.vb.sceneBoundingRect())
        #plot.getAxis('right').linkToView(self.pdf_viewbox)  # links the second y axis to the second plot
        #self.pdf_viewbox.setXLink(plot)  # sync the x axis of both plots

        change_axis_ticks(self.badstrip.strip_plot,self.ticksStyle)
        change_axis_ticks(self.badstrip.strip_plot_histogram,self.ticksStyle)


    def reconfig_plot(self, Title, plot_settings):
        '''Reconfigs the plot for the different plots
        :param - Title must be string, containing the name of the plot (title)
        :param - plot_settings must be a tuple consisting elements like it is in the config defined
                        "Idark": (["Pad", "#"], ["Current", "A"], [False, False], True)
        '''
        self.badstrip.strip_plot.setTitle("Strip results on: " + str(Title), **self.titleStyle)
        self.badstrip.strip_plot.setLabel('bottom', str(plot_settings[0][0]), units=str(plot_settings[0][1]), **self.labelStyle)
        self.badstrip.strip_plot.setLabel('left', str(plot_settings[1][0]), units=str(plot_settings[1][1]), **self.labelStyle)
        self.badstrip.strip_plot.plotItem.setLogMode(x=plot_settings[2][0], y=plot_settings[2][1])
        self.badstrip.strip_plot.getPlotItem().invertY(plot_settings[3])

        self.badstrip.strip_plot_histogram.setTitle("Histogram results on: " + str(Title), **self.titleStyle)
        self.badstrip.strip_plot_histogram.setLabel('left', "Count", units="#", **self.labelStyle)
        self.badstrip.strip_plot_histogram.setLabel('bottom', str(plot_settings[1][0]), units=str(plot_settings[1][1]), **self.labelStyle)
        self.badstrip.strip_plot_histogram.plotItem.setLogMode(x=plot_settings[2][0], y=plot_settings[2][1])
        self.badstrip.strip_plot_histogram.getPlotItem().invertX(plot_settings[3])
        #self.pdf_viewbox.invertX(plot_settings[3])

    def update_plot(self, measurement_name):
        '''This handles the update of the plot'''
        # This clear here erases all data from the viewbox each time this function is called and draws all points again!
        # Without this old plot data will still be visible and redrawn again! High memory usage and cpu usage
        # With the clear statement medium cpu und low memory usage
        measurement = self.badstrip.which_plot.currentText()
        if measurement:
            ydata = self.plot_data[measurement]["data"][measurement_name]
            xdata = np.arange(len(self.plot_data[measurement]["data"]["Pad"]))
            self.reconfig_plot(measurement_name, self.measurement_dict[measurement_name])
            if ydata.any(): # Checks if data is available or if all is empty
                if len(xdata) == len(ydata):  # sometimes it happens that the values are not yet ready (fucking multithreading)

                    # Make the normal line Plot
                    self.badstrip.strip_plot.plot(xdata, ydata, pen="r", clear=True, width=8, connect="finite")

                    # Make the histogram of the data
                    # y, x = np.histogram(np.array(ydata), bins=int(self.bins))
                    yout, ind = self.variables.analysis.remove_outliner(ydata)
                    x, y = self.variables.analysis.do_histogram(yout, self.bins)
                    self.badstrip.strip_plot_histogram.plot(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80), clear=True, connect="finite")

                    self.update_specs_bars(measurement_name, ydata)

                    if self.plot_data[measurement]["analysed"] and False:
                        # Todo: plot the lms piecewise here as well
                        anadata = self.plot_data[measurement]

                        # Plot Lms line
                        # containst first and last point for the slope y = kx+d
                        k = float(anadata["lms_fit"][measurement_name][0])
                        d = float(anadata["lms_fit"][measurement_name][1])
                        lmsdata = [[0, len(xdata)],[d, k*len(xdata)+d]]
                        self.badstrip.strip_plot.plot(lmsdata[0], lmsdata[1], pen="g")

                        # Plot pdf in the histogram plot
                        #pdfdata = anadata["pdf"][measurement_name]
                        #self.pdf_viewbox.clear()
                        #plot_item = self.setpg.PlotCurveItem(pdfdata[2], pdfdata[3],
                        #                                pen={'color': "g", 'width': 2},
                        #                                clear=True)
                        #self.pdf_viewbox.addItem(plot_item)
                        #del plot_item  # the plot class needs a plot item which can be rendered, to avoid a mem leak delete the created plot item or 20k ram will be used
                        # hum_plot_obj.addItem(setpg.plot(self.variables.meas_data["humidity"][0],self.variables.meas_data["humidity"][1],pen={'color': "b", 'width': 2}, clear=True))
                          # resize the second plot!
                        #self.eq_text = self.setpg.TextItem(text="Some text", border='#000000', fill='#ccffff')
                        #self.eq_text.setParentItem(self.pdf_viewbox)
                        #self.eq_text.setPos(pdfdata[2][np.argmax(pdfdata[3])], y.max() * 0.9)
                        #self.pdf_viewbox.setGeometry(self.badstrip.strip_plot_histogram.plotItem.vb.sceneBoundingRect())

                        # Update report text
                        self.badstrip.report_label.setText(anadata["report"][measurement_name])

            self.badstrip.strip_plot.enableAutoRange(y=True)
            self.tooltip = show_cursor_position(self.badstrip.strip_plot)
            return self.badstrip.strip_plot, self.badstrip.strip_plot_histogram

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

    def export_plots(self):
        """Exports all current plots to the output directory, as well as the Analysis results text"""
        # create an exporter instance, as an argument give it
        # the item you wish to export
        # Todo: some bug is here with the exporting
        import pyqtgraph as pg
        import pyqtgraph.exporters.SVGExporter

        old_measurement = self.badstrip.which_measurement.currentText()
        old_plot = self.badstrip.which_plot.currentText()
        for meas in self.plot_data[old_plot]["data"].keys(): # Loop over all possible plots
            if meas != "Pad":
                plot, hist = self.update_plot(meas)
                win = pg.GraphicsLayoutWidget()
                for i, pl in enumerate([plot, hist]):
                    plt = win.addPlot(row=i, col=0)
                    plt.addItem(pl.plotItem)
                exporter = pg.exporters.ImageExporter(win.scene())
                # set export parameters if needed
                exporter.params['width'] = 1000
                # save to file
                exporter.export('fileName.png')