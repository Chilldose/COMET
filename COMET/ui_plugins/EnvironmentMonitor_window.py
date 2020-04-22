import logging
from PyQt5.QtWidgets import *
import pyqtgraph
from .. utilities import get_thicks_for_timestamp_plot
import numpy as np
from time import sleep, asctime

class EnvironmentMonitor_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.settings = self.variables.default_values_dict["settings"]
        self.rooms = self.settings["Rooms"]
        self.roomsGui = {}
        self.hum_plot_obj = {}
        self.temphum_plot = {}
        self.env_task = self.variables.framework["background_Env_task"]
        self.last_change = 0
        self.history = self.settings.get("temp_history",3600)

        # Settings Main tab
        self.Settingwidget = QWidget() # The main settings tab, where all switches etc are
        self.SettingsGui = self.variables.load_QtUi_file("environment_monitor_settings.ui", self.Settingwidget)
        self.layout.addWidget(self.Settingwidget)

        # Add the env widgets as tabs
        for room in self.rooms:
            TabWidget, Tablayout = self.variables.get_tabWidget()
            widget = QWidget()  # The main settings tab, where all switches etc are
            self.roomsGui[room] = (self.variables.load_QtUi_file("environment_monitor.ui", widget), widget, TabWidget, Tablayout)
            Tablayout.addWidget(widget)
            self.variables.add_rendering_function(TabWidget, room)
            #Change the GUI render Order
            self.settings["GUI_render_order"].insert(0, room)
            
            # Config the room plot
            self.config_room(room)

        # Config all settings
        self.SettingsGui.env_updateInterval_slider.setRange(0, 500)
        self.SettingsGui.env_updateInterval_slider.setValue(self.settings["temphum_update_interval"] / 1000.)
        self.SettingsGui.env_history_slider.setRange(0, 200)
        self.SettingsGui.env_history_slider.setValue(self.settings.get("temp_history",3600) / 3600.)


        # Connect the slider to the update function
        self.SettingsGui.env_history_slider.sliderReleased.connect(self.valuechange)
        self.SettingsGui.env_updateInterval_slider.sliderReleased.connect(self.valuechange)
        self.SettingsGui.fade_red_slider.sliderReleased.connect(self.valuechange)
        self.SettingsGui.fade_blue_slider.sliderReleased.connect(self.valuechange)
        self.SettingsGui.fade_green_slider.sliderReleased.connect(self.valuechange)
        self.SettingsGui.fade_speed_slider.sliderReleased.connect(self.valuechange)

        # Update the slide for fancy graphics
        self.SettingsGui.env_history_slider.valueChanged.connect(self.update_lcd_displays)
        self.SettingsGui.env_updateInterval_slider.valueChanged.connect(self.update_lcd_displays)
        self.SettingsGui.fade_red_slider.valueChanged.connect(self.update_lcd_displays)
        self.SettingsGui.fade_blue_slider.valueChanged.connect(self.update_lcd_displays)
        self.SettingsGui.fade_green_slider.valueChanged.connect(self.update_lcd_displays)
        self.SettingsGui.fade_speed_slider.valueChanged.connect(self.update_lcd_displays)


        # Add the update function and run some inits
        self.variables.add_update_function(self.update_temphum_plots)
        self.valuechange()

    def update_lcd_displays(self):
        """Updates the displays"""
        self.SettingsGui.env_updateInterval_lcd.display(float(self.SettingsGui.env_updateInterval_slider.value()))
        self.SettingsGui.env_history_lcd.display(float(self.SettingsGui.env_history_slider.value()))

        self.SettingsGui.fade_blue_lcd.display(float(self.SettingsGui.fade_blue_slider.value()))
        self.SettingsGui.fade_green_lcd.display(float(self.SettingsGui.fade_green_slider.value()))
        self.SettingsGui.fade_red_lcd.display(float(self.SettingsGui.fade_red_slider.value()))
        self.SettingsGui.fade_speed_lcd.display(float(self.SettingsGui.fade_speed_slider.value()))

    def update_env_control(self):
        """Updates the env control"""
        if self.env_task:
            self.env_task.update_interval = float(self.SettingsGui.env_updateInterval_slider.value()*1000)
            self.history = float(self.SettingsGui.env_history_slider.value()*3600)
        else:
            self.log.error("No environment task found! Value change has no effect.")


    def config_room(self, room):
        """Configs the environment monitor instance"""
        # Create plot and config it
        self.roomsGui[room][0].room_label.setText(room)
        self.hum_plot_obj[room] = pyqtgraph.ViewBox()  # generate new plot item
        self.temphum_plot[room] = self.roomsGui[room][0].temphum_plot
        # Add the plot to the plot objects
        self.variables.plot_objs[room] = self.roomsGui[room][0].temphum_plot
        self.config_plot(self.temphum_plot[room], self.hum_plot_obj[room])  # config the plot items

        self.roomsGui[room][0].temperature_bar.setRange(self.settings["Ranges"][room]["temp_min"],
                                                     self.settings["Ranges"][room]["temp_max"])
        self.roomsGui[room][0].humidity_bar.setRange(self.settings["Ranges"][room]["hum_min"],
                                                  self.settings["Ranges"][room]["hum_max"])
        # Buttons
        self.roomsGui[room][0].reset_button.clicked.connect(self.reset_data)
        self.roomsGui[room][0].autofit_button.clicked.connect(self.refit_data_to_screen)


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
            for room in self.rooms:
                # Change the LCD display objects as well
                if self.variables.meas_data["Temp_"+room][1].any() and self.variables.meas_data["Hum_"+room][1].any():
                    temp = self.variables.meas_data["Temp_"+room][1][-1]
                    hum = self.variables.meas_data["Hum_"+room][1][-1]
                    self.roomsGui[room][0].temp_lcd.display(temp)
                    self.roomsGui[room][0].hum_lcd.display(hum)
                    self.roomsGui[room][0].last_update_label.setText("Last Update: {}".format(asctime(self.variables.meas_data["Temp_"+room][0][-1])))
    
                    # Set temp bar
                    max_temp = self.settings["Ranges"][room]["temp_max"]
                    min_temp = self.settings["Ranges"][room]["temp_min"]
                    if temp <= max_temp and temp >= min_temp:
                        self.roomsGui[room][0].temperature_bar.setValue(temp)
                    elif temp > max_temp:
                        self.roomsGui[room][0].temperature_bar.setValue(max_temp)
                    elif temp < min_temp:
                        self.roomsGui[room][0].temperature_bar.setValue(min_temp)
    
                    # Set hum bar
                    max_hum = self.settings["Ranges"][room]["hum_max"]
                    min_hum = self.settings["Ranges"][room]["hum_min"]
                    if hum <= max_hum and temp >= min_hum:
                        self.roomsGui[room][0].humidity_bar.setValue(hum)
                    elif hum > max_hum:
                        self.roomsGui[room][0].humidity_bar.setValue(max_hum)
                    elif hum < min_hum:
                        self.roomsGui[room][0].humidity_bar.setValue(min_hum)
    
                    # Very approyximate Dew point calc
                    dew = temp-(100-hum)/5
                    self.roomsGui[room][0].dew_point_lcd.display(dew)
    
                self.temphum_plot[room].clear()  # clears the plot and prevents a memory leak
                self.hum_plot_obj[room].clear()
                p1 = self.temphum_plot[room].plotItem
    
                ax = p1.getAxis('bottom')  # This is the trick
                #self.__cut_arrays(self.variables.meas_data,
                #                  float(self.history),
                #                  ["Temp_"+room, "hum_"+room])
                ax.setTicks([get_thicks_for_timestamp_plot(self.variables.meas_data["Temp_"+room][0], 5,
                                                           self.variables.default_values_dict["settings"]["time_format"])])
                try:
                    if len(self.variables.meas_data["Temp_"+room][0]) == len(self.variables.meas_data["Hum_"+room][1]):  # sometimes it happens that the values are not yet ready
                        p1.plot(self.variables.meas_data["Temp_"+room][0], self.variables.meas_data["Temp_"+room][1],
                                pen={'color': "#cc1414", 'width': 2}, clear=True)
                        plot_item = pyqtgraph.PlotCurveItem(self.variables.meas_data["Hum_"+room][0],
                                                        self.variables.meas_data["Hum_"+room][1],
                                                        pen={'color': "#2662e2", 'width': 2},
                                                        clear=True)
                        self.hum_plot_obj[room].addItem(plot_item)
                        del plot_item
                        self.hum_plot_obj[room].setGeometry(p1.vb.sceneBoundingRect())  # resize the second plot!
                except Exception as err:
                    self.log.error("An error happened while updating the environment plot with error: {}".format(err))

    def valuechange(self):
        '''This is the function which is called, when a value is changed in the spin boxes'''
        self.update_lcd_displays()
        self.update_env_control()

    def update_bars(self, room):
        """This function simply updates the spin bixes and bars to min max values etc."""
        self.roomsGui[room][0].temperature_bar.setValue(25)
        self.roomsGui[room][0].humidity_bar.setValue(25)

    def refit_data_to_screen(self):
        """Refits the data to screen"""
        for room in self.rooms:
            self.temphum_plot[room].plotItem.autoRange()

    def reset_data(self):
        """Resets data of plots"""
        for room in self.rooms:
            # Change the LCD display objects as well
            self.variables.meas_data["Temp_" + room] = [np.array([]), np.array([])]
            self.variables.meas_data["Hum_" + room] = [np.array([]), np.array([])]
            self.variables.default_values_dict["settings"]["new_data"] = True



