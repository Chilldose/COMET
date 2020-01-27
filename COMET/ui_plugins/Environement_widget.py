# This is the config for the environement widget.
# This is not intended to be used as stand alone Tab in the framework
# Use it as a simple configurer for the Environement widget

import pyqtgraph
from .. utilities import get_thicks_for_timestamp_plot, build_command
import logging
from PyQt5.QtWidgets import *

class Environement_widget(object):

    def __init__(self, gui):

        self.envlog = logging.getLogger(__name__)

        # Environment widget
        if not "Environment" in gui.child_layouts:
            self.envlog.error("No layout found to render environment widget in. Skipping...")
            return
        Env_Qwidget = QWidget()
        self.env_layout = gui.child_layouts["Environment"]
        self.Env_Widget = self.variables.load_QtUi_file("environement_control.ui", Env_Qwidget)
        self.env_layout.addWidget(Env_Qwidget)

        # Continue with the other plugins
        super(Environement_widget, self).__init__(gui)

        # Variables
        if "temp_history" not in self.variables.default_values_dict["settings"]:
            self.variables.default_values_dict["settings"]["temp_history"] = 3600
            self.envlog.warning("No temp_history defined, defaulting to 3600s")

        if "temphum_update_intervall" not in self.variables.default_values_dict["settings"]:
            self.variables.default_values_dict["settings"]["temphum_update_intervall"] = 5000
            self.envlog.warning("No temp_history defined, defaulting to 5000ms")

        if "time_format" not in self.variables.default_values_dict["settings"]:
            self.variables.default_values_dict["settings"]["time_format"] = "%H:%M:%S"
            self.envlog.warning("No time_format defined, defaulting to %H:%M:%S")

        # Config the Spin boxes for min and max
        self.Env_Widget.max_hum_spin.setRange(21,100)
        self.Env_Widget.min_hum_spin.setRange(0,100)
        self.Env_Widget.min_hum_spin.setValue(20)
        self.Env_Widget.max_hum_spin.setValue(25)

        self.Env_Widget.max_temp_spin.setRange(21, 100)
        self.Env_Widget.min_temp_spin.setRange(0, 100)
        self.Env_Widget.min_temp_spin.setValue(20)
        self.Env_Widget.max_temp_spin.setValue(25)

        self.update_bars_and_spinboxes()

        # Config the progress bars
        self.Env_Widget.temperature_bar.setStyleSheet("QProgressBar::chunk{background-color: #cc1414;}")
        self.Env_Widget.temperature_bar.setValue(self.Env_Widget.min_temp_spin.value())

        self.Env_Widget.humidity_bar.setStyleSheet("QProgressBar::chunk{background-color: #2662e2;}")
        self.Env_Widget.humidity_bar.setValue(self.Env_Widget.min_hum_spin.value())

        self.variables.default_values_dict["settings"]["control_environment"] = False
        self.variables.default_values_dict["settings"]["Log_environment"] = False
        self.Env_Widget.env_control_check.setChecked(True)
        self.Env_Widget.log_env_check.setChecked(True)

        # Create plot and config it
        self.hum_plot_obj = pyqtgraph.ViewBox()  # generate new plot item
        self.temphum_plot = self.Env_Widget.pyqtPlotItem
        self.variables.plot_objs["Env"] = self.temphum_plot
        self.config_plot(self.temphum_plot, self.hum_plot_obj)  # config the plot items

        # Go through all to set the value a the device as well
        if "temphum_controller" in self.variables.devices_dict:
            # Connect everything
            self.Env_Widget.min_temp_spin.valueChanged.connect(self.valuechange)
            self.Env_Widget.max_temp_spin.valueChanged.connect(self.valuechange)
            self.Env_Widget.max_hum_spin.valueChanged.connect(self.valuechange)
            self.Env_Widget.min_hum_spin.valueChanged.connect(self.valuechange)
            self.Env_Widget.env_control_check.stateChanged.connect(self.valuechange)
            self.Env_Widget.log_env_check.stateChanged.connect(self.valuechange)

            self.variables.add_update_function(self.update_temphum_plots)
            self.valuechange()
            self.update_bars_and_spinboxes()
        else:
            self.envlog.error("No device found with name or alias 'temphum_controller'. No environement monitor can be started")

    def config_plot(self, plot, plot2):
        plot = plot.plotItem
        plot.setLabel('right', "humidity", units='%')
        plot.setLabel('bottom', "time")
        plot.setLabel('left', "temperature", units='Celsius')
        plot.getAxis('left').setPen(pyqtgraph.mkPen(color='#cc1414', width=3))
        plot.getAxis('right').setPen(pyqtgraph.mkPen(color='#2662e2', width=3))
        plot.showAxis('top', show=True)
        plot.getAxis('top').setTicks([])
        plot.getAxis('bottom').setScale(1e-9)
        # plot.showGrid(y=True, x=True)
        # plot.setRange(yRange=[15, 35])

        # For second plot
        plot.scene().addItem(plot2)  # inserts the second plot into the scene of the first
        plot2.setGeometry(plot.vb.sceneBoundingRect())
        plot.getAxis('right').linkToView(plot2)  # links the second y axis to the second plot
        plot2.setXLink(plot)  # sync the x axis of both plots
        # plot2.setRange(yRange=[0, 50])



    def __cut_arrays(self, data_array, maximum_time, arrays_to_cut):
        '''This function cuts an array to a maximum time difference
        This function is supposed to be used only for temp and humidity shaped arrays
        '''

        try:
            begin_time = data_array[arrays_to_cut[0]][0][0]
            end_time = data_array[arrays_to_cut[0]][0][-1]
            delta_time = data_array[arrays_to_cut[0]][0][1] - data_array[arrays_to_cut[0]][0][0]
            total_time = end_time - begin_time
            if total_time > maximum_time:
                over_time = total_time - maximum_time
                array_elm_to_drop = int(over_time / delta_time)
                for arrays in arrays_to_cut:
                    data_array[arrays][0] = data_array[arrays][0][array_elm_to_drop:]
                    data_array[arrays][1] = data_array[arrays][1][array_elm_to_drop:]
        except:
            pass

    def update_temphum_plots(self):
        # for rooms in self.rooms:
        if self.variables.default_values_dict["settings"]["new_data"]:

            # Change the LCD display objects as well
            if self.variables.meas_data["temperature"][1].any() and self.variables.meas_data["humidity"][1].any():
                temp = self.variables.meas_data["temperature"][1][-1]
                hum = self.variables.meas_data["humidity"][1][-1]
                self.Env_Widget.temp_lcd.display(temp)
                self.Env_Widget.hum_lcd.display(hum)

                # Set temp bar
                if temp <= self.Env_Widget.max_temp_spin.value() and temp >= self.Env_Widget.min_temp_spin.value():
                    self.Env_Widget.temperature_bar.setValue(temp)
                elif temp > self.Env_Widget.max_temp_spin.value():
                    self.Env_Widget.temperature_bar.setValue(self.Env_Widget.max_temp_spin.value())
                elif temp < self.Env_Widget.min_temp_spin.value():
                    self.Env_Widget.temperature_bar.setValue(self.Env_Widget.min_temp_spin.value())

                # Set temp bar
                if hum <= self.Env_Widget.max_hum_spin.value() and temp >= self.Env_Widget.min_hum_spin.value():
                    self.Env_Widget.humidity_bar.setValue(hum)
                elif hum > self.Env_Widget.max_hum_spin.value():
                    self.Env_Widget.humidity_bar.setValue(self.Env_Widget.max_hum_spin.value())
                elif hum < self.Env_Widget.min_hum_spin.value():
                    self.Env_Widget.humidity_bar.setValue(self.Env_Widget.min_hum_spin.value())

                # Very approyximate Dew point calc
                dew = temp-(100-hum)/5
                self.Env_Widget.dew_point_lcd.display(dew)

            self.temphum_plot.clear()  # clears the plot and prevents a memory leak
            self.hum_plot_obj.clear()
            p1 = self.temphum_plot.plotItem

            ax = p1.getAxis('bottom')  # This is the trick
            self.__cut_arrays(self.variables.meas_data,
                              float(self.variables.default_values_dict["settings"].get("temp_history",
                              3600)),
                              ["temperature", "humidity"])
            ax.setTicks([get_thicks_for_timestamp_plot(self.variables.meas_data["temperature"][0], 5,
                                                       self.variables.default_values_dict["settings"]["time_format"])])

            try:
                if len(self.variables.meas_data["temperature"][0]) == len(self.variables.meas_data["humidity"][1]):  # sometimes it happens that the values are not yet ready
                    p1.plot(self.variables.meas_data["temperature"][0], self.variables.meas_data["temperature"][1],
                            pen={'color': "#cc1414", 'width': 2}, clear=True)
                    plot_item = pyqtgraph.PlotCurveItem(self.variables.meas_data["humidity"][0],
                                                    self.variables.meas_data["humidity"][1],
                                                    pen={'color': "#2662e2", 'width': 2},
                                                    clear=True)
                    self.hum_plot_obj.addItem(plot_item)
                    del plot_item
                    self.hum_plot_obj.setGeometry(p1.vb.sceneBoundingRect())  # resize the second plot!
            except Exception as err:
                self.envlog.error("An error happened while updating the environement with error: {}".format(err))

    def valuechange(self):
        '''This is the function which is called, when a value is changed in the spin boxes'''

        self.update_bars_and_spinboxes()

        self.variables.default_values_dict["settings"]["control_environment"] = self.Env_Widget.env_control_check.isChecked()
        self.variables.default_values_dict["settings"]["Log_environment"] = self.Env_Widget.log_env_check.isChecked()

        max = build_command(self.variables.devices_dict["temphum_controller"], ("set_hummax", self.Env_Widget.max_hum_spin.value()))
        min = build_command(self.variables.devices_dict["temphum_controller"], ("set_hummin", self.Env_Widget.min_hum_spin.value()))

        self.variables.vcw.write(self.variables.devices_dict["temphum_controller"], max)
        self.variables.vcw.write(self.variables.devices_dict["temphum_controller"], min)

    def update_bars_and_spinboxes(self):
        """This function simply updates the spin bixes and bars to min max values etc."""
        self.Env_Widget.min_temp_spin.setMaximum(self.Env_Widget.max_temp_spin.value())
        self.Env_Widget.max_temp_spin.setMinimum(self.Env_Widget.min_temp_spin.value())
        self.Env_Widget.min_hum_spin.setMaximum(self.Env_Widget.max_hum_spin.value())
        self.Env_Widget.max_hum_spin.setMinimum(self.Env_Widget.min_hum_spin.value())

        self.Env_Widget.temperature_bar.setRange(self.Env_Widget.min_temp_spin.value(),self.Env_Widget.max_temp_spin.value())
        self.Env_Widget.humidity_bar.setRange(self.Env_Widget.min_hum_spin.value(),self.Env_Widget.max_hum_spin.value())

        self.variables.default_values_dict["settings"]["current_tempmin"] = self.Env_Widget.min_temp_spin.value()
        self.variables.default_values_dict["settings"]["current_tempmax"] = self.Env_Widget.max_temp_spin.value()
        self.variables.default_values_dict["settings"]["current_hummin"] = self.Env_Widget.min_hum_spin.value()
        self.variables.default_values_dict["settings"]["current_hummax"] = self.Env_Widget.max_hum_spin.value()
