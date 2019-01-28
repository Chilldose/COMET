
import ast
import json
import os
import os.path as osp
import sys, importlib, logging

import numpy as np
import pyqtgraph as pq
from PyQt5.QtCore import Qt
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from .. import engineering_notation as en

from .. import utilities

l = logging.getLogger(__name__)

hf = utilities.help_functions()

class Main_window:

    def __init__(self, GUI_classes, layout):

        self.variables = GUI_classes
        #self.widgets = widgets
        self.layout = layout

        # Orientation and placement
        # 15 times 15 tiles

        self.previous_xloc = 0
        self.previous_yloc = 0
        self.previous_zloc = 0

        # POS: Project selector
        self.proj_posy = 0
        self.proj_posx = 0
        self.proj_xsize = 1
        self.proj_ysize = 1

        #Table pos
        self.table_xpos = 0
        self.table_ypos = 1
        self.table_xsize = 1
        self.table_ysize = 1

        # Start stop buttons
        self.Start_posx = 0
        self.Start_posy = 4
        self.Start_xsize = 2
        self.Start_ysize = 2

        # IV plot
        self.IV_posx = 3
        self.IV_posy = 0
        self.IV_xsize = 2
        self.IV_ysize = 2

        # CV plot
        self.CV_posx = 3
        self.CV_posy = 3
        self.CV_xsize = 2
        self.CV_ysize = 2

        # Temphum plot
        self.temp_xpos = 3
        self.temp_ypos = 5
        self.temp_xsize = 2
        self.temp_ysize = 1

        # Font size
        self.font = QtGui.QFont()
        self.font.setPointSize(10)

        # Additional Widgets for UI
        self.table_widget = QWidget()
        self.table_move_ui = self.variables.load_QtUi_file("./modules/QT_Designer_UI/table_control.ui", self.table_widget)
        #self.table_move_ui = Ui_table_control(self.table_widget)


        # Important buttons like start stop etc.
        self.settings()
        self.start_menu()
        self.temphum_plot()
        self.table_control_obj = self.table_control()
        self.table_move = self.table_move()

        # Plots
        self.IV_plot()
        self.CV_plot()


    def table_move(self):
        # Add table control from UI
        # Table control

        #table = helpfull_functions.table_control_class(self.variables.default_values_dict, self.variables.devices_dict["Table_control"], self.variables.message_to_main) # initiates all from the table

        self.layout.addWidget(self.table_widget, self.table_ypos + self.table_ysize + 1, self.table_xpos, 1, 1)

        def table_move_indi():
            '''This function updates the table indicator'''
            if self.variables.default_values_dict["Defaults"]["table_is_moving"]:
                self.table_move_ui.table_ind.setStyleSheet("background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px")
            else:
                self.table_move_ui.table_ind.setStyleSheet("background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px")
            pass

        @hf.raise_exception
        def adjust_table_speed(kwargs = None): # must be here because of reasons
            '''This function adjusts the speed of the table'''
            speed = int(float(self.variables.devices_dict["Table_control"]["default_joy_speed"])/100. * float(self.table_move_ui.Table_speed.value()))
            self.variables.table.set_joystick_speed(float(speed))

        if "Table_control" in self.variables.devices_dict:
            self.table_move_ui.x_move.setMinimum(float(self.variables.devices_dict["Table_control"]["table_xmin"]))
            self.table_move_ui.x_move.setMaximum(float(self.variables.devices_dict["Table_control"]["table_xmax"]))

            self.table_move_ui.y_move.setMinimum(float(self.variables.devices_dict["Table_control"]["table_ymin"]))
            self.table_move_ui.y_move.setMaximum(float(self.variables.devices_dict["Table_control"]["table_ymax"]))

            self.table_move_ui.z_move.setMinimum(float(self.variables.devices_dict["Table_control"]["table_zmin"]))
            self.table_move_ui.z_move.setMaximum(float(self.variables.devices_dict["Table_control"]["table_zmax"]))

            if "current_speed" in self.variables.devices_dict["Table_control"]:
                speed = int(float(self.variables.devices_dict["Table_control"]["current_speed"]) / float(self.variables.devices_dict["Table_control"]["default_speed"])* 100)
                self.table_move_ui.Table_speed.setValue(speed)
                #adjust_table_speed()
            else:
                self.table_move_ui.Table_speed.setValue(100)
                self.variables.devices_dict["Table_control"].update({"current_speed" : float(self.variables.devices_dict["Table_control"]["default_speed"])})
                #adjust_table_speed()

        else:
            self.table_move_ui.x_move.setMinimum(float(0))
            self.table_move_ui.x_move.setMaximum(float(0))

            self.table_move_ui.y_move.setMinimum(float(0))
            self.table_move_ui.y_move.setMaximum(float(0))

            self.table_move_ui.z_move.setMinimum(float(0))
            self.table_move_ui.z_move.setMaximum(float(0))

            self.table_move_ui.Table_speed.setValue(10)


        def adjust_x_pos():
            '''This function adjusts the xpos of the table'''
            pos = self.variables.table.get_current_position()
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
            xpos = self.table_move_ui.x_move.value()
            error = self.variables.table.move_to([xpos, pos[1], pos[2]], True, self.variables.default_values_dict["Defaults"]["height_movement"])
            if error:
                self.variables.message_to_main.put(error)
            self.variables.table.set_joystick(True)
            self.variables.table.set_axis([True, True, False])  # so z axis cannot be adressed


        def adjust_y_pos():
            '''This function adjusts the xpos of the table'''
            pos = self.variables.table.get_current_position()
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
            ypos = self.table_move_ui.y_move.value()
            error = self.variables.table.move_to([pos[0], ypos, pos[2]], self.variables.default_values_dict["Defaults"]["height_movement"])
            if error:
                self.variables.message_to_main.put(error)
            self.variables.table.set_joystick(True)
            self.variables.table.set_axis([True, True, False])  # so z axis cannot be adressed

        def adjust_z_pos():
            '''This function adjusts the xpos of the table'''
            pos = self.variables.table.get_current_position()
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
            zpos = self.table_move_ui.z_move.value()
            error = self.variables.table.move_to([pos[0], pos[1], zpos], self.variables.default_values_dict["Defaults"]["height_movement"])
            if error:
                self.variables.message_to_main.put(error)
            self.variables.table.set_joystick(True)
            self.variables.table.set_axis([True, True, False])  # so z axis cannot be adressed

        @hf.raise_exception
        def enable_table_control(bool):
            '''This function enables the table and the joystick frame'''
            if bool:
                #This will be called, when the table control is enabled
                reply = QMessageBox.question(None, 'Warning', "Are you sure move the table? \n Warning: If measurement is running table movement ist not possible", QMessageBox.Yes, QMessageBox.No)
                if reply == QMessageBox.Yes and not self.variables.default_values_dict["Defaults"]["Measurement_running"]:
                    self.table_move_ui.frame.setEnabled(bool)
                    if self.table_move_ui.z_move.isEnabled():
                        self.table_move_ui.z_move.setEnabled(False)
                        self.table_move_ui.unlock_Z.toggle()
                    pos = self.variables.table.get_current_position()
                    if pos:
                        self.previous_xloc = pos[0]
                        self.previous_yloc = pos[1]
                        self.previous_zloc = pos[2]
                    else:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Information)
                        msg.setText(
                            "There seems to be a bad error with the table. Is it connected to the PC?")
                        # msg.setInformativeText("This is additional information")
                        msg.setWindowTitle("Really bad error occured.")
                        # msg.setDetailedText("The details are as follows:")
                        msg.exec_()
                        self.table_move_ui.frame.setDisabled(True)
                        self.table_move_ui.Enable_table.setChecked(False)
                        self.variables.table.set_joystick(False)
                        self.variables.default_values_dict["Defaults"]["zlock"] = True
                        self.variables.default_values_dict["Defaults"]["joystick"] = False
                        self.table_move_ui.unlock_Z.setChecked(False)
                        self.variables.table.set_axis([True, True, True])  # This is necessary so all axis can be adresses while move
                        return


                    self.variables.table.set_axis([True, True, False])  # This is necessary so by default the joystick can adresses xy axis
                    self.variables.table.set_joystick(True)
                    self.variables.default_values_dict["Defaults"]["joystick"] = True
                    adjust_table_speed()



                else:
                    self.table_move_ui.frame.setDisabled(bool)
                    self.table_move_ui.Enable_table.setChecked(False)
                    self.variables.table.set_joystick(False)
                    self.variables.default_values_dict["Defaults"]["zlock"] = True
                    self.variables.default_values_dict["Defaults"]["joystick"] = False
                    self.table_move_ui.unlock_Z.setChecked(False)
                    self.variables.table.set_axis([True, True, True]) # This is necessary so all axis can be adresses while move
            else:
                # This will be done when the table control will be dissabled
                self.table_move_ui.frame.setEnabled(bool)
                self.variables.table.set_joystick(False)
                self.variables.table.set_axis([True, True, True])

        def move_previous():
            '''This function moves the table back to the previous position'''
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True]) # so all axis can be adressed
            errorcode = self.variables.table.move_to([self.previous_xloc, self.previous_yloc, self.previous_zloc], True, self.variables.default_values_dict["Defaults"]["height_movement"])
            if errorcode:
                self.variables.message_to_main.put(errorcode)
            self.variables.table.set_axis([True, True, False])  # so z axis is off again
            self.variables.table.set_joystick(True)

        def z_pos_warning():
            if self.variables.default_values_dict["Defaults"]["zlock"]:
                move_z = QMessageBox.question(None, 'Warning',"Moving the table in Z, can cause serious demage on the setup and sensor.", QMessageBox.Ok)
                if move_z:
                    self.variables.table.set_axis([False, False, True])
                    self.table_move_ui.unlock_Z.setChecked(True)
                    self.variables.default_values_dict["Defaults"]["zlock"] = False
                    self.variables.table.set_joystick(True)

                else:
                    self.table_move_ui.unlock_Z.setChecked(False)
            else:
                self.variables.table.set_axis([True, True, False])
                self.variables.default_values_dict["Defaults"]["zlock"] = True
                self.table_move_ui.unlock_Z.setChecked(False)
                self.variables.table.set_joystick(True)


        self.table_move_ui.x_move.sliderReleased.connect(adjust_x_pos)
        self.table_move_ui.y_move.sliderReleased.connect(adjust_y_pos)
        self.table_move_ui.z_move.sliderReleased.connect(adjust_z_pos)
        self.table_move_ui.got_to_previous.clicked.connect(move_previous)
        self.table_move_ui.Table_speed.valueChanged.connect(adjust_table_speed)
        self.table_move_ui.unlock_Z.clicked.connect(z_pos_warning)

        self.table_move_ui.Enable_table.clicked['bool'].connect(enable_table_control)

        self.variables.add_update_function(table_move_indi)

        #self.adjust_table_speed()


        # Update and control functions of the table control

        def table_move_update():
            '''Here all functions concerning the table move update are handled'''
            pos = self.variables.table.get_current_position()
            self.table_move_ui.x_move.setProperty("value", int(pos[0]))
            self.table_move_ui.y_move.setProperty("value", int(pos[1]))
            self.table_move_ui.z_move.setProperty("value", int(pos[2]))

        # Not sure if this function should be called all the time
        #self.variables.add_update_function(table_move_update)

    @hf.raise_exception
    def settings(self, kwargs=None):
            '''Here the settings for project operator etc is included'''
            # Create sublayout
            setting_layout = QGridLayout()

            # Frame over the objects
            frame = QLabel()
            frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            frame.setLineWidth(0)
            frame.setMidLineWidth(2)

            self.layout.addWidget(frame, self.Start_posy, self.Start_posx, self.Start_ysize, self.Start_xsize)

            self.layout.addWidget(frame, self.proj_posy, self.proj_posx, self.proj_ysize, self.proj_xsize)

            # Order functions
            def change_name(filename):
                self.variables.default_values_dict["Defaults"]["Current_filename"] = str(filename)

            def project_selector_action(project):
                load_valid_sensors_for_project(str(project))
                self.variables.default_values_dict["Defaults"]["Current_project"] = str(project)

            def sensor_selector_action(sensor):
                self.variables.default_values_dict["Defaults"]["Current_sensor"] = str(sensor)

            def operator_selector_action(operator):
                self.variables.default_values_dict["Defaults"]["Current_operator"] = str(operator)

            def dir_selector_action():
                fileDialog = QFileDialog()
                directory = fileDialog.getExistingDirectory()
                dir_textbox.setText(directory)
                self.variables.default_values_dict["Defaults"]["Current_directory"] = str(directory)

            def load_measurement_settings_file():
                ''' This function loads a mesuerment settings file'''

                # First update the settings that the state machine is up to date
                self.variables.ui_plugins["Settings_window"].load_new_settings()

                fileDialog = QFileDialog()
                file = fileDialog.getOpenFileName()

                if file[0]:
                    json_file = open(str(file[0]), "r")
                    dict = json.load(json_file)
                    json_file.close()

                    l.info("Loaded new measurement settings file: " + str(file[0]))
                    self.variables.default_values_dict["Defaults"].update(dict) # Updates the values of the dict, it either updates the values or adds them if not incluced
                    self.variables.ui_plugins["Settings_window"].configure_settings()

            @hf.raise_exception
            def save_measurement_settings_file(kwargs = None):
                ''' This function saves a mesuerment settings file'''

                #First update the settings that the state machine is up to date
                self.variables.ui_plugins["Settings_window"].load_new_settings()

                fileDialog = QFileDialog()
                file = fileDialog.getSaveFileName()


                if file[0]:
                    # gets me all settings which are to be saved
                    hf.write_init_file(file[0], self.variables.ui_plugins["Settings_window"].get_all_settings())
                    l.info("Settings file successfully written to: " + str(file))

            def load_valid_sensors_for_project(project_name):
                '''This function loads the valid sensors for each project'''
                #Warning sensor_comboBox must be accessable for this function to work
                sensor_comboBox.clear()
                try:
                    # self.variables.default_values_dict["Defaults"]["Sensor_types"][project_name]
                    for sen in self.variables.default_values_dict["Defaults"]["Sensor_types"][project_name]:
                        sensor_comboBox.addItem(str(sen))  # Adds all items to the combo box
                    # Select the first element to be right, if possible
                    self.variables.default_values_dict["Defaults"]["Current_sensor"] = sensor_comboBox.currentText()

                except:
                    l.error("No sensors defined for project: " + str(sen))
                    self.variables.default_values_dict["Defaults"]["Current_sensor"] = "None"
                    self.variables.message_to_main({"RequestError": "No sensors defined for project: " + str(sen)})







            # Project selector

            # Label of the Error Log
            proj_label = QLabel()
            proj_label.setText("Select project")
            proj_label.setFont(self.font)

            proj_comboBox = QComboBox() # Creates a combo box

            for projects in self.variables.default_values_dict["Defaults"]["Projects"]:
                proj_comboBox.addItem(str(projects)) # Adds all projects to the combo box
            proj_comboBox.activated[str].connect(project_selector_action)

            if "Current_project" in self.variables.default_values_dict["Defaults"]:
                self.variables.default_values_dict["Defaults"]["Current_project"] = self.variables.default_values_dict["Defaults"]["Projects"][0] # That one project is definetly choosen
            else:
                self.variables.default_values_dict["Defaults"].update({"Current_project": self.variables.default_values_dict["Defaults"]["Projects"][0]})


            # Sensore selection

            # Label of the sensor selector
            sensor_label = QLabel()
            sensor_label.setText("Select sensor")
            sensor_label.setFont(self.font)

            sensor_comboBox = QComboBox() # Creates a combo box

            for projects in self.variables.default_values_dict["Defaults"]["Sensor_types"][self.variables.default_values_dict["Defaults"]["Current_project"]]:
                sensor_comboBox.addItem(str(projects)) # Adds all items to the combo box
            sensor_comboBox.activated[str].connect(sensor_selector_action)

            if "Current_sensor" in self.variables.default_values_dict["Defaults"]:
                try:
                    self.variables.default_values_dict["Defaults"]["Current_sensor"] = self.variables.default_values_dict["Defaults"]["Sensor_types"][self.variables.default_values_dict["Defaults"]["Current_project"]][0] # That one project is definetly choosen
                except:
                    self.variables.default_values_dict["Defaults"]["Current_sensor"] = "None"
            else:
                self.variables.default_values_dict["Defaults"].update({"Current_sensor": self.variables.default_values_dict["Defaults"]["Sensor_types"][self.variables.default_values_dict["Defaults"]["Current_project"]][0]})


            # Measurement name selection

            # Label of the input file

            inp_label = QLabel()
            inp_label.setText("Output filename")
            inp_label.setFont(self.font)

            inp_input_name = QLineEdit()
            inp_input_name.textChanged.connect(change_name)
            #inp_input_name.setMaximumWidth(300)

            if "Current_filename" in self.variables.default_values_dict["Defaults"]:
                inp_input_name.setText(str(self.variables.default_values_dict["Defaults"]["Current_filename"]))
            else:
                self.variables.default_values_dict["Defaults"].update({"Current_filename": "enter_filename_here"})
                inp_input_name.setText(str(self.variables.default_values_dict["Defaults"]["Current_filename"]))


            # Operator selector

            # Label of the Operator
            op_label = QLabel()
            op_label.setText("Select Operator")
            op_label.setFont(self.font)

            op_comboBox = QComboBox() # Creates a combo box

            for projects in self.variables.default_values_dict["Defaults"]["Operator"]:
                op_comboBox.addItem(str(projects)) # Adds all items to the combo box

            op_comboBox.activated[str].connect(operator_selector_action)

            if "Current_operator" in self.variables.default_values_dict["Defaults"]:
                self.variables.default_values_dict["Defaults"]["Current_operator"] = self.variables.default_values_dict["Defaults"]["Operator"][0] # That one project is definetly choosen
            else:
                self.variables.default_values_dict["Defaults"].update({"Current_operator": self.variables.default_values_dict["Defaults"]["Operator"][0]})

            # Save path selector

            # Save button
            save_to_btn = QPushButton('Save to')
            save_to_btn.clicked.connect(dir_selector_action)
            save_to_btn.resize(save_to_btn.sizeHint())

            # Appearance of the Error Log
            dir_textbox = QLabel()
            dir_textbox.setStyleSheet("background : rgb(245,245,245)")
            dir_textbox.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            dir_textbox.setMinimumHeight(25)
            dir_textbox.setMinimumWidth(700)
            #dir_textbox.setMaximumHeight(25)
            #dir_textbox.setMaximumWidth(700)

            if "Current_directory" in self.variables.default_values_dict["Defaults"]:             # TODO check if directory exists
                dir_textbox.setText(str(self.variables.default_values_dict["Defaults"]["Current_directory"]))
            else:
                self.variables.default_values_dict["Defaults"].update({"Current_directory": str(osp.join(osp.dirname(sys.modules[__name__].__file__)))})
                dir_textbox.setText(str(osp.join(osp.dirname(sys.modules[__name__].__file__))))


            # Default file loader
            file_load_btn = QPushButton('Load settings file')
            file_load_btn.clicked.connect(load_measurement_settings_file)
            file_load_btn.resize(file_load_btn.sizeHint())


            #Save default file
            save_file_btn = QPushButton('Save settings file')
            save_file_btn.clicked.connect(save_measurement_settings_file)
            save_file_btn.resize(save_file_btn.sizeHint())


            # Adding all widgets to the sublayout
            #setting_layout.addWidget(frame,0,0,4,4)
            setting_layout.addWidget(proj_label, 0, 0)
            setting_layout.addWidget(proj_comboBox, 1, 0)
            setting_layout.addWidget(sensor_label, 0, 1)
            setting_layout.addWidget(sensor_comboBox, 1, 1)
            setting_layout.addWidget(inp_label, 0, 2)
            setting_layout.addWidget(inp_input_name, 1, 2)
            setting_layout.addWidget(op_label, 0, 3)
            setting_layout.addWidget(op_comboBox, 1, 3)
            setting_layout.addWidget(save_to_btn, 2, 0)
            setting_layout.addWidget(dir_textbox,  2, 1, 0, 3)
            setting_layout.addWidget(file_load_btn, 3, 0)
            setting_layout.addWidget(save_file_btn, 3, 1)

            setting_layout.setContentsMargins(8,8,8,8) # Makes a margin to the layout


            # Add the layout to the main layout
            self.layout.addLayout(setting_layout, self.proj_posy, self.proj_posx, self.proj_ysize, self.proj_xsize)

    @hf.raise_exception
    def start_menu(self,kwargs = None):
            '''Here all start stop buttons are included'''

            # Create sublayout
            start_layout = QGridLayout()

            # Frame over the objects
            frame = QLabel()
            frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            frame.setLineWidth(0)
            frame.setMidLineWidth(2)

            self.layout.addWidget(frame, self.Start_posy, self.Start_posx, self.Start_ysize, self.Start_xsize)

            # Adding variables to the default dict
            #self.variables.default_values_dict["Defaults"].update({"End_time": "NaN", "Start_time": "NaN", "Bad_strips": 0})
            #self.variables.default_values_dict["Defaults"].update({"Measurement_running": False, "Alignment": True, "Environment_status": True})


            # Orders
            @hf.raise_exception
            def exit_order(kwargs = None):
                reply = QMessageBox.question(None, 'Warning', "Are you sure to quit?", QMessageBox.Yes, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.variables.message_to_main.put({"CLOSE_PROGRAM": True})
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Information)
                    msg.setText("The program is shuting down, depending on the amount of instruments attached to the PC this can take a while...")
                    # msg.setInformativeText("This is additional information")
                    msg.setWindowTitle("Shutdown in progress")
                    # msg.setDetailedText("The details are as follows:")
                    msg.exec_()


            @hf.raise_exception
            def Start_order(kwargs = None):
                if self.variables.default_values_dict["Defaults"]["Current_filename"] and os.path.isdir(self.variables.default_values_dict["Defaults"]["Current_directory"]):
                    if not self.variables.default_values_dict["Defaults"]["Measurement_running"]:
                        self.variables.reset_plot_data()

                    # Ensures that the new values are in the state machine
                    self.variables.ui_plugins["Settings_window"].load_new_settings()

                    additional_settings = {"Save_data": True,
                                           "Filepath": self.variables.default_values_dict["Defaults"]["Current_directory"],
                                           "Filename": self.variables.default_values_dict["Defaults"]["Current_filename"],
                                           "Project": self.variables.default_values_dict["Defaults"]["Current_project"],
                                           "Sensor": self.variables.default_values_dict["Defaults"]["Current_sensor"],
                                           "enviroment": True, # if enviroment surveillance should be done
                                           "skip_init": False} #warning this prevents the device init

                    self.variables.job.generate_job(additional_settings)

                    #order = {"Measurement": {"Save_data": True,"Filepath": self.variables.default_values_dict["Defaults"]["Current_directory"],"Filename": self.variables.default_values_dict["Defaults"]["Current_filename"], "Longterm_IV": {"StartVolt": self.variables.default_values_dict["Defaults"]["Longterm_IV"][0],"EndVolt": self.variables.default_values_dict["Defaults"]["Longterm_IV"][1],"Longterm_IV_time": self.variables.default_values_dict["Defaults"]["Longterm_IV_time"],"Steps": 10}}}  # just for now
                    #self.variables.message_from_main.put(order)

                else:
                    reply = QMessageBox.information(None, 'Warning', "Please enter a valid filepath and filename.", QMessageBox.Ok)

            @hf.raise_exception
            def Stop_order(kwargs = None):
                order = {"ABORT_MEASUREMENT": True} # just for now
                self.variables.message_to_main.put(order)

            @hf.raise_exception
            def Load_order(kwargs = None):
                '''This function loads an old measurement file and displays it if no measurement is curently conducted'''

                if not self.variables.default_values_dict["Defaults"]["Measurement_running"]:
                    fileDialog = QFileDialog()
                    file = fileDialog.getOpenFileName()

                    if file[0]:
                        pass
                else:
                    reply = QMessageBox.information(None, 'Warning', "You cannot load a measurement files while data taking is in progress.", QMessageBox.Ok)

            @hf.raise_exception
            def create_statistic_text(kwargs = None):
                try:
                    bias = "Bias Voltage: " + str(en.EngNumber(float(self.variables.default_values_dict["Defaults"]["bias_voltage"]))) + "V" + "\n\n"
                except:
                    bias = "Bias Voltage: NONE V" + "\n\n"
                starttime = "Start time: " + str(self.variables.default_values_dict["Defaults"]["Start_time"]) + "\n\n"
                eastend = "East. end time: " + str(self.variables.default_values_dict["Defaults"]["End_time"]) + "\n\n"
                striptime = "Strip meas. time: " + str(round(float(self.variables.default_values_dict["Defaults"]["strip_scan_time"]),2)) + " sec" +  "\n\n"
                badstrips = "Bad strips: " + str(self.variables.default_values_dict["Defaults"]["Bad_strips"]) + "\n\n"
                currentstrip = "Current strip: " + str(self.variables.default_values_dict["Defaults"]["current_strip"]) + "\n\n"

                return str( starttime + eastend + striptime + currentstrip + badstrips + bias)



            # Exit button

            qbtn = QPushButton('Quit')
            qbtn.clicked.connect(exit_order)
            qbtn.resize(qbtn.sizeHint())
            start_layout.addWidget(qbtn, 1, 1)


            # Start button

            qbtn = QPushButton('Start')
            qbtn.clicked.connect(Start_order)
            qbtn.resize(qbtn.sizeHint())
            start_layout.addWidget(qbtn, 0, 0)

            # Stop button

            qbtn = QPushButton('Stop')
            qbtn.clicked.connect(Stop_order)
            qbtn.resize(qbtn.sizeHint())
            start_layout.addWidget(qbtn, 1, 0)

            # Load button

            qbtn = QPushButton('Load')
            qbtn.clicked.connect(Load_order)
            qbtn.resize(qbtn.sizeHint())
            start_layout.addWidget(qbtn, 0 , 1)

            # Error log

            textbox_label = QLabel()
            textbox_label.setText("Event Log")
            textbox_label.setFont(self.font)

            # Appearance of the Error Log
            self.errors = QLabel()
            self.errors.setStyleSheet("background : rgb(245,245,245)")
            self.errors.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            self.errors.setText("No errors =)")
            self.errors.setMinimumHeight(80)

            start_layout.addWidget(textbox_label, 2, 0)
            start_layout.addWidget(self.errors, 3, 0, 4, 2)

            #Stats text

            # Label of the Error Log
            textbox_label = QLabel()
            textbox_label.setText("Statistics")
            textbox_label.setFont(self.font)

            # Appearance of the stats
            textbox = QLabel()
            textbox.setStyleSheet("background : rgb(245,245,245)")
            textbox.setFrameStyle(QFrame.Panel | QFrame.Raised)
            textbox.setFont(self.font)
            textbox.setText(create_statistic_text())
            textbox.setAlignment(QtCore.Qt.AlignVCenter)
            #textbox.setMinimumHeight(80)
            #textbox.setMinimumWidth(250)
            #textbox.setMaximumHeight(210)
            #textbox.setMaximumWidth(250)

            #start_layout.addWidget(textbox_label, 0, 2)
            start_layout.addWidget(textbox, 0, 2, 6, 1)

            # Stats textbox

            # Appearance of the stats led
            textbox_led = QLabel()
            textbox_led.setMidLineWidth(4)
            textbox_led.setStyleSheet("background : rgb(128,128,128); border-radius: 25px")
            font = QtGui.QFont()
            font.setPointSize(10)
            textbox_led.setFont(font)
            textbox_led.setAlignment(QtCore.Qt.AlignCenter)
            #textbox.setMinimumHeight(70)
            #textbox.setMaximumHeight(70)

            start_layout.addWidget(textbox_led, 6, 2)

            # Update functions

            def error_update():
                error_text = ""
                last_errors = self.variables.error_log[-16:]
                for errors in last_errors:
                    error_text += errors + "\n"

                if self.errors.text() != error_text:
                    self.errors.setText(error_text)

            def stat_update():
                new_text = create_statistic_text()
                if textbox.text() != new_text:
                    textbox.setText(new_text)

            def led_update():

                current_state = self.variables.default_values_dict["Defaults"]["current_led_state"]
                alignment = self.variables.default_values_dict["Defaults"]["Alignment"]
                running = self.variables.default_values_dict["Defaults"]["Measurement_running"]
                enviroment = self.variables.default_values_dict["Defaults"]["Environment_status"]

                if current_state != "running" and running:
                    self.variables.default_values_dict["Defaults"]["current_led_state"] = "running"
                    textbox_led.setStyleSheet("background : rgb(0,0,255); border-radius: 25px")
                    textbox_led.setText("Measurement running")
                    return


                elif current_state != "Alignment" and not alignment and not running:
                    self.variables.default_values_dict["Defaults"]["current_led_state"] = "Alignment"
                    textbox_led.setStyleSheet("background : rgb(255,0,0); border-radius: 25px")
                    textbox_led.setText("Alignement missing")
                    return


                elif current_state != "enviroment" and not enviroment and alignment and not running:
                    self.variables.default_values_dict["Defaults"]["current_led_state"] = "enviroment"
                    textbox_led.setStyleSheet("background : rgb(255,153,51); border-radius: 25px")
                    textbox_led.setText("Environment status not ok")
                    return

                if current_state != "ready" and alignment and not running and enviroment:
                    self.variables.default_values_dict["Defaults"]["current_led_state"] = "ready"
                    textbox_led.setStyleSheet("background : rgb(0,255,0); border-radius: 25px")
                    textbox_led.setText("Ready to go")
                    return

            # Adding update functions
            self.variables.add_update_function(error_update)
            self.variables.add_update_function(stat_update)
            self.variables.add_update_function(led_update)

            start_layout.setContentsMargins(8, 8, 8, 8)  # Makes a margin to the layout

            # Add the layout to the main layout
            self.layout.addLayout(start_layout, self.Start_posy, self.Start_posx, self.Start_ysize, self.Start_xsize)

    def IV_plot(self):
        x = np.zeros(1)
        y = np.zeros(1)

        iv_plot = pq.PlotWidget(title = "IV curve")

        iv_plot.setLabel('left', "current", units='A')
        iv_plot.setLabel('bottom', "voltage", units='V')
        iv_plot.showAxis('top', show=True)
        iv_plot.showAxis('right', show=True)
        iv_plot.getPlotItem().invertX(True)
        iv_plot.getPlotItem().invertY(True)

        iv_plot.setMinimumHeight(350)
        iv_plot.setMaximumHeight(350)

        iv_plot.plot(pen="y")

        self.layout.addWidget(iv_plot, self.IV_posy, self.IV_posx, self.IV_ysize, self.IV_ysize)

        #self.variables.plots.append(iv_plot) #Appeds the plot to the list of all plots
        @hf.raise_exception
        def update(kwargs = None):
            # This clear here erases all data from the viewbox each time this function is called and draws all points again!
            #Without this old plot data will still be visible and redrawn again! High memory usage and cpu usage
            # With the clear statement medium cpu und low memory usage
            if self.variables.default_values_dict["Defaults"]["new_data"]:
                if len(self.variables.meas_data["IV"][0]) == len(self.variables.meas_data["IV"][1]): #sometimes it happens that the values are not yet ready
                    iv_plot.plot(self.variables.meas_data["IV"][0], self.variables.meas_data["IV"][1], pen="y", clear = True, )

        self.variables.add_update_function(update)



    def CV_plot(self):

        x = np.zeros(1)
        y = np.zeros(1)

        cv_plot = pq.PlotWidget(title = "CV curve")

        cv_plot.setLabel('left', "1/c^2", units='arb. units')
        cv_plot.setLabel('bottom', "voltage", units='V')
        cv_plot.showAxis('top', show=True)
        cv_plot.showAxis('right', show=True)
        cv_plot.getPlotItem().invertX(True)

        cv_plot.setMinimumHeight(350)
        cv_plot.setMaximumHeight(350)


        cv_plot.plot(x,y, pen="b")
        self.layout.addWidget(cv_plot, self.CV_posy, self.CV_posx, self.CV_ysize, self.CV_ysize)

        def depletion_volt(value):
            if value != 0:
                return 1./(value*value)
            else:
                return value

        def update():
            if self.variables.default_values_dict["Defaults"]["new_data"]:
                if len(self.variables.meas_data["CV"][0]) == len(self.variables.meas_data["CV"][1]): #sometimes it happens that the values are not yet ready
                    cv_plot.plot(self.variables.meas_data["CV"][0], map(depletion_volt, self.variables.meas_data["CV"][1]), pen="y", clear = True)
                    #cv_plot.plot(self.variables.meas_data["CV"][0],self.variables.meas_data["CV"][1], pen="y", clear=True)

        self.variables.add_update_function(update)

    @hf.raise_exception
    def temphum_plot(self, kwargs = None):
        '''Also button corresponding to temphum plot included'''

        def valuechange():
            '''This is the function which is called, when a value is changed in the spin boxes'''

            tempmin.setMaximum(tempmax.value())
            tempmax.setMinimum(tempmin.value())
            hummin.setMaximum(hummax.value())
            hummax.setMinimum(hummin.value())

            self.variables.default_values_dict["Defaults"]["current_tempmin"] = tempmin.value()
            self.variables.default_values_dict["Defaults"]["current_tempmax"] = tempmax.value()
            self.variables.default_values_dict["Defaults"]["current_hummin"] = hummin.value()
            self.variables.default_values_dict["Defaults"]["current_hummax"] = hummax.value()

            max = hf.build_command(self.variables.devices_dict["temphum_controller"], ("set_hummax", hummax.value()))
            min = hf.build_command(self.variables.devices_dict["temphum_controller"], ("set_hummin", hummin.value()))

            self.variables.vcw.write(self.variables.devices_dict["temphum_controller"], max)
            self.variables.vcw.write(self.variables.devices_dict["temphum_controller"], min)


        def dry_air_action():
            if dry_air_btn.isChecked():
                device_dict = self.variables.devices_dict["temphum_controller"]
                try:
                    command = hf.build_command(device_dict, ("set_environement_control", "ON"))
                    answer = self.variables.vcw.write(device_dict, command)
                    if answer == -1:
                        l.error("The environement controller did not responsed accordingly. Answer: " +str(answer).strip())
                        self.variables.message_to_main.put({"RequestError": "The environement controller did not responsed accordingly. Answer: " + str(answer).strip()})
                        return 0
                except:
                    l.error("An error occured while changing the environement control")
                    self.variables.message_to_main.put({"RequestError": "An error occured while changing the environement control"})
                    return 0
                dry_air_btn.setText("Humidity ctl. on")
                self.variables.default_values_dict["Defaults"]["humidity_control"] = True

            else:
                device_dict = self.variables.devices_dict["temphum_controller"]
                try:
                    command = hf.build_command(device_dict, ("set_environement_control", "OFF"))
                    answer = self.variables.vcw.write(device_dict, command)
                    if answer == -1:
                        l.error("The environement controller did not responsed accordingly. Answer: " + str(answer).strip())
                        self.variables.message_to_main.put({"RequestError": "The environement controller did not responsed accordingly. Answer: " + str(answer).strip()})
                        return 0
                except:
                    l.error("An error occured while changing the environement control")
                    self.variables.message_to_main.put({"RequestError": "An error occured while changing the environement control"})
                    return 0
                dry_air_btn.setText("Humidity ctl. off")
                self.variables.default_values_dict["Defaults"]["humidity_control"] = False


        def light_action():
            """This function is debricated"""
            if light_btn.isChecked():
                self.variables.default_values_dict["Defaults"]["external_lights"] = True
            else:
                self.variables.default_values_dict["Defaults"]["external_lights"] = False

        def check_light_state():
            if self.variables.default_values_dict["Defaults"]["internal_lights"] and not light_btn.text() == "Lights on": # Checks if the lights are on and the button is off
                light_btn.setText("Lights on")
                light_btn.setStyleSheet("background : rgb(0,255,0); border-radius: 5px")
            elif not self.variables.default_values_dict["Defaults"]["internal_lights"] and not light_btn.text() == "Lights off":
                light_btn.setText("Lights off")
                light_btn.setStyleSheet("background : rgb(255,0,0); border-radius: 5px")

        def config_plot(plot, plot2, pg):
            plot = plot.plotItem
            plot.setLabel('right', "humidity", units='%')
            plot.setLabel('bottom', "time")
            plot.setLabel('left', "temperature", units='Celsius')
            plot.getAxis('left').setPen(pg.mkPen(color='#c4380d', width=3))
            plot.getAxis('right').setPen(pg.mkPen(color='#025b94', width=3))
            plot.showAxis('top', show=True)
            plot.getAxis('top').setTicks([])
            plot.getAxis('bottom').setScale(1e-9)
            #plot.setRange(yRange=[15, 35])

            # For second plot
            plot.scene().addItem(plot2)  # inserts the second plot into the scene of the first
            plot2.setGeometry(plot.vb.sceneBoundingRect())
            plot.getAxis('right').linkToView(plot2)  # links the second y axis to the second plot
            plot2.setXLink(plot)  # sync the x axis of both plots
            #plot2.setRange(yRange=[0, 50])


        def __cut_arrays(data_array, maximum_time, arrays_to_cut):
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
                    array_elm_to_drop = int(over_time/delta_time)
                    for arrays in arrays_to_cut:
                        data_array[arrays][0] = data_array[arrays][0][array_elm_to_drop:]
                        data_array[arrays][1] = data_array[arrays][1][array_elm_to_drop:]
            except:
                pass

        def update_temphum_plots(kwargs = None):
            # for rooms in self.rooms:
            if self.variables.default_values_dict["Defaults"]["new_data"]:
                temphum_plot.clear() # clears the plot and prevents a memory leak
                hum_plot_obj.clear()
                p1 = temphum_plot.plotItem

                ax = p1.getAxis('bottom')  # This is the trick
                __cut_arrays(self.variables.meas_data, float(self.variables.default_values_dict["Defaults"].get("temp_history", 3600)), ["temperature", "humidity"])
                ax.setTicks([hf.get_thicks_for_timestamp_plot(self.variables.meas_data["temperature"][0], 5, self.variables.default_values_dict["Defaults"]["time_format"])])

                try:
                    if len(self.variables.meas_data["temperature"][0]) == len(self.variables.meas_data["humidity"][1]):  # sometimes it happens that the values are not yet ready
                        p1.plot(self.variables.meas_data["temperature"][0], self.variables.meas_data["temperature"][1],pen={'color': "r", 'width': 2}, clear=True)
                        plot_item = setpg.PlotCurveItem(self.variables.meas_data["humidity"][0],
                                            self.variables.meas_data["humidity"][1], pen={'color': "b", 'width': 2},
                                            clear=True)
                        hum_plot_obj.addItem(plot_item)
                        del plot_item # the plot class needs a plot item which can be rendered, to avoid a mem leak delete the created plot item or 20k ram will be used
                        #hum_plot_obj.addItem(setpg.plot(self.variables.meas_data["humidity"][0],self.variables.meas_data["humidity"][1],pen={'color': "b", 'width': 2}, clear=True))
                        hum_plot_obj.setGeometry(p1.vb.sceneBoundingRect())  # resize the second plot!
                except:
                    pass

        # Create sublayout
        temphum_layout = QGridLayout()

        # Frame over the objects
        frame = QLabel()
        frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        frame.setLineWidth(0)
        frame.setMidLineWidth(2)

        self.layout.addWidget(frame, self.temp_ypos, self.temp_xpos, self.temp_ysize, self.temp_xsize)

        x = np.zeros(1)
        y = np.zeros(1)

        setpg = pq
        #date_axis = hf.CAxisTime(orientation='bottom')  # Correctly generates the time axis
        hum_plot_obj = setpg.ViewBox()  # generate new plot item
        temphum_plot = pq.PlotWidget()
        config_plot(temphum_plot, hum_plot_obj, setpg)  # config the plot items

        self.variables.add_update_function(update_temphum_plots)

        # Additional Variables will be generated for temp and hum
        #self.variables.default_values_dict["Defaults"].update({"lights": False, "humidity_control": True, "current_tempmin": 20, "current_tempmax": 25, "current_hummin": 20,"current_hummax": 25})


        # Spin Boxes for temp and humidity

        tempmin = QSpinBox()
        tempmax = QSpinBox()
        hummin = QSpinBox()
        hummax = QSpinBox()

        # Spinbox label
        textbox_temp = QLabel()
        textbox_temp.setText("Min temp.           Max temp.")
        textbox_temp.setFont(self.font)
        textbox_hum = QLabel()
        textbox_hum.setText("Min hum.          Max hum.")
        textbox_hum.setFont(self.font)


        # Config

        tempmin.setRange(15,35)
        tempmin.setValue(float(self.variables.default_values_dict["Defaults"]["current_tempmin"]))
        tempmax.setRange(15, 35)
        tempmax.setValue(float(self.variables.default_values_dict["Defaults"]["current_tempmax"]))
        tempmin.valueChanged.connect(valuechange)
        tempmax.valueChanged.connect(valuechange)

        hummin.setRange(0, 70)
        hummin.setValue(float(self.variables.default_values_dict["Defaults"]["current_hummin"]))
        hummax.setRange(0, 70)
        hummax.setValue(float(self.variables.default_values_dict["Defaults"]["current_hummax"]))
        hummin.valueChanged.connect(valuechange)
        hummax.valueChanged.connect(valuechange)


        # Push buttons on the right for humidity control and light control

        dry_air_btn = QPushButton("Humidity ctl. off")
        self.variables.default_values_dict["Defaults"]["humidity_control"] = False
        dry_air_btn.setCheckable(True)
        dry_air_btn.toggle()
        dry_air_btn.clicked.connect(dry_air_action)
        dry_air_btn.setChecked(False)

        light_btn = QLabel()
        light_btn.setText("State not defined")
        light_btn.setAlignment(QtCore.Qt.AlignVCenter |  QtCore.Qt.AlignHCenter)
        light_btn.setStyleSheet("background : rgb(255,0,0); border-radius: 5px")

        #light_btn.setCheckable(True)
        #light_btn.clicked.connect(light_action)

        # Humidity
        #temphum_plot.plot(x,y, pen="b")

        # Widgets add
        temphum_layout.addWidget(textbox_temp, 0, 0, 1, 2)
        temphum_layout.addWidget(tempmin, 1, 0)
        temphum_layout.addWidget(tempmax, 1, 1)

        temphum_layout.addWidget(textbox_hum, 2, 0, 1, 2)
        temphum_layout.addWidget(hummin, 3, 0)
        temphum_layout.addWidget(hummax, 3, 1)

        temphum_layout.addWidget(dry_air_btn, 4, 0, 1, 2)
        temphum_layout.addWidget(light_btn, 5, 0, 3, 2)

        temphum_layout.addWidget(temphum_plot, 0, 3, 10, 2)

        temphum_layout.setContentsMargins(8, 8, 0, 8)  # Makes a margin to the layout

        # Add the layout to the main layout
        self.layout.addLayout(temphum_layout, self.temp_ypos, self.temp_xpos, self.temp_ysize, self.temp_xsize)



        def update():
            pass


        self.variables.add_update_function(update)
        self.variables.add_update_function(check_light_state)



    def table_control(self):
        ''' Functions and buttons for the table controls'''

        # Create sublayout
        table_layout = QGridLayout()

        # Frame over the objects
        frame = QLabel()
        frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        frame.setLineWidth(0)
        frame.setMidLineWidth(2)

        self.layout.addWidget(frame, self.table_ypos, self.table_xpos, self.table_ysize, self.table_xsize)

        # Generate all QT objects needed
        label = QLabel("Table control")
        position = QLabel()
        move_zero_btn = QPushButton("Initiate table")
        table_up_btn = QPushButton("UP")
        table_down_btn = QPushButton("DOWN")
        table_indicator = QLabel()

        # Set textsize etc.
        font = QtGui.QFont()
        font.setPointSize(13)
        label.setFont(font)
        label.setFrameStyle(QFrame.Panel)
        label.setAlignment(Qt.AlignCenter)
        position.setFont(self.font)
        table_indicator.setFont(self.font)


        def check_position():
            '''This function checks the position of the table and updates the gui elemtents'''
            if self.variables.table:
                pos = self.variables.table.get_current_position()
                position_update()

        def position_update():
            '''Updates the position'''
            if self.variables.table:
                pos = [self.variables.devices_dict["Table_control"].get("x_pos", 0), self.variables.devices_dict["Table_control"].get("y_pos", 0),self.variables.devices_dict["Table_control"].get("z_pos", 0)]

                position.setText("X - Position: " + str(pos[0]) + "\n \n" + "Y - Position: " + str(pos[1]) + "\n \n" + "Z - Position: " + str(pos[2]))

                #Update the scrollbars things
                self.table_move_ui.x_move.setValue(pos[0])
                self.table_move_ui.y_move.setValue(pos[1])
                self.table_move_ui.z_move.setValue(pos[2])

        def state_update():
            '''Updates the state of the table up down etc.'''
            if self.variables.table:
                if self.variables.default_values_dict["Defaults"]["Table_state"] and not table_indicator.text() == "UP":
                    table_indicator.setStyleSheet("background : rgb(0,255,0); border-radius: 25px")
                    table_indicator.setText("UP")

                elif not self.variables.default_values_dict["Defaults"]["Table_state"] and not table_indicator.text() == "DOWN":
                    table_indicator.setStyleSheet("background : rgb(255,0,0); border-radius: 25px")
                    table_indicator.setText("DOWN")


        # Position text
        check_position() # after boot up the values can be not correct due to boot up and init proceedures

        # Tabe indicator
        table_indicator.setStyleSheet("background : rgb(0,255,0); border-radius: 25px")
        table_indicator.setText("UP")
        table_indicator.setMidLineWidth(4)
        table_indicator.setAlignment(QtCore.Qt.AlignCenter)


        # Action orders

        def up_order():
            ''' This function moves the table up'''
            if self.variables.table:
                if self.variables.default_values_dict["Defaults"]["Table_state"]:
                    self.variables.message_to_main.put({"Warning": "Table is in the up position."})

                else:
                    self.variables.table.set_joystick(False)
                    self.variables.table.set_axis([True, True, True])
                    errorcode = self.variables.table.move_up(self.variables.default_values_dict["Defaults"]["height_movement"])
                    if errorcode:
                        self.variables.message_to_main.put(errorcode)
                        return
                    #self.variables.default_values_dict["Defaults"]["Table_state"] = True  # True means table is up
                    self.variables.default_values_dict["Defaults"]["Table_stay_down"] = False
                position_update()
                #self.table_move.table_move_update()

        def down_order():
            ''' This functions moves the table down'''
            if self.variables.table:
                if not self.variables.default_values_dict["Defaults"]["Table_state"]:
                    self.variables.message_to_main.put({"Warning": "Table is in the down position."})

                else:
                    self.variables.table.set_joystick(False)
                    self.variables.table.set_axis([True, True, True])
                    errorcode = self.variables.table.move_down(self.variables.default_values_dict["Defaults"]["height_movement"])
                    if errorcode:
                        self.variables.message_to_main.put(errorcode)
                        return
                    #self.variables.default_values_dict["Defaults"]["Table_state"] = False # False means table is down
                    self.variables.default_values_dict["Defaults"]["Table_stay_down"] = True
                position_update()
                #self.table_move.table_move_update()


        @hf.raise_exception
        def move_zero_order(kwargs = None):
            '''Moves the table to the zero position '''
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True])
            xpos = (float(self.variables.devices_dict["Table_control"]["table_xmax"]) - float(self.variables.devices_dict["Table_control"]["table_xmin"])) /2.
            ypos = (float(self.variables.devices_dict["Table_control"]["table_ymax"]) -
                          float(self.variables.devices_dict["Table_control"]["table_ymin"])) / 2.
            zpos = (float(self.variables.devices_dict["Table_control"]["table_zmax"]) -
                          float(self.variables.devices_dict["Table_control"]["table_zmin"])) / 2.
            errorcode = self.variables.table.move_to([xpos,ypos,zpos], False, self.variables.default_values_dict["Defaults"]["height_movement"])
            if errorcode:
                self.variables.message_to_main.put(errorcode)

        def initiate_table():
            # First Ask to do so
            reply = QMessageBox.question(None, 'Warning',
                                         "Are you sure to initiate the table? This can cause serious damage!",
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.variables.message_to_main.put({"Info": "Table will now be initialized..."})
                errorcode = self.variables.table.initiate_table()
                if errorcode:
                    self.variables.message_to_main.put(errorcode)
                move_zero_order()
                self.variables.message_to_main.put({"Info": "Table initialization done, table goes back to zero position."})
            else:
                # Do nothing
                pass



        # Generate Buttons

        # Table up button
        table_up_btn.clicked.connect(up_order)
        table_up_btn.resize(table_up_btn.sizeHint())

        # Table down button
        table_down_btn.clicked.connect(down_order)
        table_down_btn.resize(table_down_btn.sizeHint())

        # Check position button
        self.table_move_ui.check_position.clicked.connect(check_position)
        table_down_btn.resize(table_down_btn.sizeHint())
        self.table_move_ui.Enable_table.clicked.connect(check_position) # Warning this function belongs to another gui element!

        # Move table to 0 position
        move_zero_btn.clicked.connect(initiate_table)
        move_zero_btn.resize(move_zero_btn.sizeHint())

        # Draw everything
        table_layout.addWidget(label,0,0,1,2)
        table_layout.addWidget(position,1,0,3,1)
        table_layout.addWidget(move_zero_btn, 4, 0)
        table_layout.addWidget(table_up_btn, 1, 1)
        table_layout.addWidget(table_down_btn, 2, 1)
        table_layout.addWidget(table_indicator, 3, 1, 2,1)

        table_layout.setContentsMargins(8, 8, 8, 8)  # Makes a margin to the layout

        # Add functions to update
        #self.variables.add_update_function(position_update)
        self.variables.add_update_function(state_update)

        # Add the layout to the main layout
        self.layout.addLayout(table_layout, self.table_ypos, self.table_xpos, self.table_ysize, self.table_xsize)
