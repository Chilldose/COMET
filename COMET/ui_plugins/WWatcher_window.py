import logging
from PyQt5.QtWidgets import *
import pyqtgraph
from ..utilities import get_thicks_for_timestamp_plot
import numpy as np
from time import sleep, asctime, localtime


class WWatcher_window:
    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.settings = self.variables.default_values_dict["settings"]

        # Settings Main tab
        self.Wwidget = (
            QWidget()
        )  # The main settings tab, where all switches etc are
        self.WGui = self.variables.load_QtUi_file(
            "WWatcher.ui", self.Wwidget
        )
        self.layout.addWidget(self.Wwidget)

        self.fat_plot_obj = pyqtgraph.ViewBox()  # generate new plot item
        self.weightfat_plot = self.WGui.w_plot

        self.config_plot(
            self.weightfat_plot, self.fat_plot_obj
        )  # config the plot items

        # Add the update function and run some inits
        #self.variables.add_update_function(self.update_temphum_plots)

    def update_lcd_displays(self):
        """Updates the displays"""
        self.SettingsGui.env_updateInterval_lcd.display(
            float(self.SettingsGui.env_updateInterval_slider.value())
        )
        self.SettingsGui.env_history_lcd.display(
            float(self.SettingsGui.env_history_slider.value())
        )

        self.SettingsGui.fade_blue_lcd.display(
            float(self.SettingsGui.fade_blue_slider.value())
        )
        self.SettingsGui.fade_green_lcd.display(
            float(self.SettingsGui.fade_green_slider.value())
        )
        self.SettingsGui.fade_red_lcd.display(
            float(self.SettingsGui.fade_red_slider.value())
        )
        self.SettingsGui.fade_speed_lcd.display(
            float(self.SettingsGui.fade_speed_slider.value())
        )

    def config_room(self, room):
        """Configs the environment monitor instance"""
        # Create plot and config it
        self.roomsGui[room][0].room_label.setText(room)
        self.hum_plot_obj[room] = pyqtgraph.ViewBox()  # generate new plot item
        self.temphum_plot[room] = self.roomsGui[room][0].temphum_plot
        # Add the plot to the plot objects
        self.variables.plot_objs[room] = self.roomsGui[room][0].temphum_plot
        self.variables.plot_objs_axis["Temp_" + room] = ("time", "Temperature")
        self.variables.plot_objs_axis["Hum_" + room] = ("time", "Humidity")
        self.variables.plot_objs_axis[room] = ("time", "")
        self.config_plot(
            self.temphum_plot[room], self.hum_plot_obj[room]
        )  # config the plot items

        self.roomsGui[room][0].temperature_bar.setRange(
            self.settings["Ranges"][room]["temp_min"],
            self.settings["Ranges"][room]["temp_max"],
        )
        self.roomsGui[room][0].humidity_bar.setRange(
            self.settings["Ranges"][room]["hum_min"],
            self.settings["Ranges"][room]["hum_max"],
        )
        # Buttons
        self.roomsGui[room][0].reset_button.clicked.connect(self.reset_data)
        self.roomsGui[room][0].autofit_button.clicked.connect(self.refit_data_to_screen)

    def config_plot(self, plot, plot2):
        plot = plot.plotItem
        plot.setLabel("right", "body fat", units="%")
        plot.setLabel("bottom", "time")
        plot.setLabel("left", "Weight", units="kg")
        plot.getAxis("left").setPen(pyqtgraph.mkPen(color="#cc1414", width=3))
        plot.getAxis("right").setPen(pyqtgraph.mkPen(color="#2662e2", width=3))
        plot.showAxis("top", show=True)
        plot.getAxis("top").setTicks([])
        plot.getAxis("bottom").setScale(1e-9)
        # plot.showGrid(y=True, x=True)
        # plot.setRange(yRange=[15, 35])

        # For second plot
        plot.scene().addItem(
            plot2
        )  # inserts the second plot into the scene of the first
        plot2.setGeometry(plot.vb.sceneBoundingRect())
        plot.getAxis("right").linkToView(
            plot2
        )  # links the second y axis to the second plot
        plot2.setXLink(plot)  # sync the x axis of both plots
        # plot2.setRange(yRange=[0, 50])

    def update_plots(self):
        # for rooms in self.rooms:
        if self.variables.default_values_dict["settings"]["new_data"]:
            for room in self.rooms:
                # Change the LCD display objects as well
                if (
                    self.variables.meas_data["Temp_" + room][1].any()
                    and self.variables.meas_data["Hum_" + room][1].any()
                ):
                    temp = self.variables.meas_data["Temp_" + room][1][-1]
                    hum = self.variables.meas_data["Hum_" + room][1][-1]
                    self.roomsGui[room][0].temp_lcd.display(temp)
                    self.roomsGui[room][0].hum_lcd.display(hum)
                    self.roomsGui[room][0].last_update_label.setText(
                        "Last Update: {}".format(asctime(localtime()))
                    )

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
                    dew = temp - (100 - hum) / 5
                    self.roomsGui[room][0].dew_point_lcd.display(dew)

                self.temphum_plot[
                    room
                ].clear()  # clears the plot and prevents a memory leak
                self.hum_plot_obj[room].clear()
                p1 = self.temphum_plot[room].plotItem

                ax = p1.getAxis("bottom")  # This is the trick
                # self.__cut_arrays(self.variables.meas_data,
                #                  float(self.history),
                #                  ["Temp_"+room, "hum_"+room])
                ax.setTicks(
                    [
                        get_thicks_for_timestamp_plot(
                            self.variables.meas_data["Temp_" + room][0],
                            5,
                            self.variables.default_values_dict["settings"][
                                "time_format"
                            ],
                        )
                    ]
                )
                try:
                    if len(self.variables.meas_data["Temp_" + room][0]) == len(
                        self.variables.meas_data["Hum_" + room][1]
                    ):  # sometimes it happens that the values are not yet ready
                        p1.plot(
                            self.variables.meas_data["Temp_" + room][0],
                            self.variables.meas_data["Temp_" + room][1],
                            pen={"color": "#cc1414", "width": 2},
                            clear=True,
                        )
                        plot_item = pyqtgraph.PlotCurveItem(
                            self.variables.meas_data["Hum_" + room][0],
                            self.variables.meas_data["Hum_" + room][1],
                            pen={"color": "#2662e2", "width": 2},
                            clear=True,
                        )
                        self.hum_plot_obj[room].addItem(plot_item)
                        del plot_item
                        self.hum_plot_obj[room].setGeometry(
                            p1.vb.sceneBoundingRect()
                        )  # resize the second plot!
                except Exception as err:
                    self.log.error(
                        "An error happened while updating the environment plot with error: {}".format(
                            err
                        )
                    )

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
