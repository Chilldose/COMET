import ast
import json
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
from time import sleep

from .. import utilities

l = logging.getLogger(__name__)

hf = utilities.help_functions()


class Alignment_window:

    def __init__(self, GUI, layout):

        self.previous_xloc = 0
        self.previous_yloc = 0
        self.previous_zloc = 0

        self.alignment_step = -1
        self.alignment_started = False
        self.check_strip = 1
        self.project = None
        self.sensor = None
        self.new_reference_pads = []
        self.reference_pads = []
        self.alignment_pads_changed = True
        self.reference_pads_positions = []
        self.sensor_pad_file = None

        self.variables = GUI
        self.transformation_matrix = self.variables.default_values_dict["Defaults"]["trans_matrix"]
        self.V0 = self.variables.default_values_dict["Defaults"]["V0"]
        self.layout = layout
        self.trans = utilities.transformation()

        # Settings tab
        alignment_widget = QWidget()
        self.alignment = self.variables.load_QtUi_file("./modules/QT_Designer_UI/Alignment.ui", alignment_widget)
        self.table_move_ui = self.alignment # this is for the table control so it can be a copy from the other ui
        self.layout.addWidget(alignment_widget)
        self.table_move = self.table_move()

        # Asign the buttons
        self.alignment.ref_1.valueChanged.connect(self.spin_box_action_1)
        self.alignment.ref_2.valueChanged.connect(self.spin_box_action_2)
        self.alignment.ref_3.valueChanged.connect(self.spin_box_action_3)
        self.alignment.StartAlignment_btn.clicked.connect(self.start_alignment_action)
        self.alignment.nextstep_btn.clicked.connect(lambda: self.next_step_action(None))
        self.alignment.abort_btn.clicked.connect(self.abort_action)
        self.alignment.move_to_strip_button.clicked.connect(self.move_to_strip_action)

        self.variables.add_update_function(self.current_strip_lcd)

        self.what_to_do_text(-1) # Initializes the text

    def current_strip_lcd(self):
        '''This function updtes the current strip lcd display'''
        current_lcd_value = self.alignment.current_strip_lcdNumber.intValue()
        current_strip = self.variables.default_values_dict["Defaults"].get("current_strip",-1)

        if current_lcd_value != current_strip:
            self.alignment.current_strip_lcdNumber.display(current_strip)


    def move_to_strip_action(self):
        '''This is the action when the move to strip button is pressed'''
        if not self.variables.default_values_dict["Defaults"]["table_is_moving"]:
            strip_to_move = self.alignment.move_to_strip_spin.value()

            if self.variables.default_values_dict["Defaults"]["Alignment"]:
                error = self.variables.table.move_to_strip(self.sensor_pad_file, (int(strip_to_move)-1),
                                                           self.trans,
                                                           self.transformation_matrix, self.V0,
                                                           self.variables.default_values_dict["Defaults"]["height_movement"])
                if error:
                    self.variables.message_to_main.put(error)
                    self.error_action(error)
                    return
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText("No alignment is done, please make the alignment and try again...")
                msg.setWindowTitle("Arrr, Pirate...")
                msg.exec_()
                return
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Table is currently moving, please wait until movement is finished...")
            msg.setWindowTitle("Arrr, Pirate...")
            msg.exec_()
            return


    @hf.raise_exception
    def start_alignment_action(self, kwargs = None):
        '''This function starts the whole alignement proceedure'''

        #First ask if you want to start the alignment
        if self.alignment_started:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("The alignment procedure is currently running.")
            msg.setWindowTitle("Alignment in progress")
            msg.exec_()
            return

        if not self.variables.default_values_dict["Defaults"]["Table_state"]:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("It seems that no table is connected to this machine...")
            msg.setWindowTitle("Sorry Bro...")
            msg.exec_()
            return

        reply = QMessageBox.question(None, 'Warning', "Are you sure to start the alignment proceedure? A previous alignement will be deleted", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Update the GUI
            self.alignment_started = True
            self.alignment_step = 0
            self.next_step_action(self.alignment_step)
        else:
            pass

    def next_step_action(self, step = None):
        '''This updates all gui elements for the next step'''

        if step == None:
            self.alignment_step += 1 # so the next step is executed
            step = self.alignment_step

        if step > 5 or not self.alignment_started:
            self.what_to_do_text(-1) # Resets the text
            if self.variables.default_values_dict["Defaults"]["Alignment"]:
                error = self.variables.table.move_to_strip(self.sensor_pad_file, 0,
                                                           self.trans,
                                                           self.transformation_matrix, self.V0,
                                                           self.variables.default_values_dict["Defaults"]["height_movement"])
                if error:
                    self.variables.message_to_main.put(error)
                    self.error_action(error)
                    return
            self.alignment_started = False

        if self.alignment_started:
            # First set the GUI
            self.what_to_do_text(step)
            self.do_alignment(step)

        if step == 5:
            self.alignment_started = False

    @hf.raise_exception
    def set_checkboxes(self, list):
        '''This function sets the checkboxes for the checklist'''
        for i, state in enumerate(list):
            getattr(self.alignment, "ali_" + str(i)).setChecked(state)

    def do_alignment(self, step):
        '''Does the steps for the alignment'''

        if step == -1:
            # reset all elements
            self.set_checkboxes([False, False, False, False, False])

        if step == 0:
            # Reset some elements and set new elements
            self.set_checkboxes([False, False, False, False, False])
            # Get sensor
            self.project = self.variables.default_values_dict["Defaults"]["Current_project"]
            self.sensor = str(self.variables.default_values_dict["Defaults"]["Current_sensor"])
            try:
                self.sensor_pad_file = self.variables.pad_files_dict[self.project][self.sensor].copy()
                self.reference_pads = self.sensor_pad_file["reference_pads"][:]
                self.update_reference_pad_positions()
                # self.adjust_alignment_points(2) should be here but the spin boxes get asignal and then they would change again- > therefore only spin boxes change this value
                self.number_of_pads = len(self.sensor_pad_file["data"])
                self.update_static()
            except :
                self.variables.message_to_main.put({"RequestError": "There was an error while accessing the pad file data. Is the pad file valid?"})
                l.error("An error while accessing the pad files with error.")
                self.error_action("An error while accessing the pad files with error.")


        if step == 1:
            # Get all changed values for alignment strips and move to first
            self.set_checkboxes([False, False, False, False, False])
            self.variables.table.set_axis([True, True, False])
            self.variables.table.set_joystick(True)

        if step == 2:
            # move to second alignment point
            self.set_checkboxes([True, False, False, False, False])
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True])
            self.first_pos = self.variables.table.get_current_position()
            sensor_first_pos = self.reference_pads_positions[0] # this gives me absolute positions
            sensor_second_pos = self.reference_pads_positions[1] # this gives me absolute positions
            relative_movepos = [x1 - x2 for (x1, x2) in zip(sensor_second_pos, sensor_first_pos)]
            #No add the strip length to the y axis for aliognement reasons
            #relative_movepos[1] = relative_movepos[1] + self.sensor_pad_file["strip_length"]
            error = self.variables.table.relative_move_to(relative_movepos, True, self.variables.default_values_dict["Defaults"].get("height_movement",800))
            if error:
                self.variables.message_to_main.put(error)
                self.error_action(error)
                return
            self.variables.table.set_axis([True, True, False])
            self.variables.table.set_joystick(True)


        if step == 3:
            # move to third alignment point
            self.set_checkboxes([True, True, False, False, False])
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True])
            self.second_pos = self.variables.table.get_current_position()
            sensor_first_pos = self.reference_pads_positions[1]  # this gives me absolute positions
            sensor_second_pos = self.reference_pads_positions[2]  # this gives me absolute positions
            relative_movepos = [x1 - x2 for (x1, x2) in zip(sensor_second_pos, sensor_first_pos)]
            error = self.variables.table.relative_move_to(relative_movepos, True,self.variables.default_values_dict["Defaults"].get("height_movement", 800))
            if error:
                self.variables.message_to_main.put(error)
                self.error_action(error)
                return
            self.variables.table.set_axis([True, True, False])
            self.variables.table.set_joystick(True)


        if step == 4:
            # choose random strip and move to
            self.set_checkboxes([True, True, True, False, False])
            self.third_pos = self.variables.table.get_current_position()

            self.variables.table.set_joystick(False)
            # Resets the axis to all open
            self.variables.table.set_axis([True, True, True])
            # Now make alignment and move absolute to the last position
            sensorx = self.reference_pads_positions[0]
            sensory = self.reference_pads_positions[1]
            sensorz = self.reference_pads_positions[2]
            T, V0 = self.trans.transformation_matrix(sensorx, sensory, sensorz, self.first_pos, self.second_pos, self.third_pos)
            if type(T) == type(int):
                self.variables.message_to_main.put(
                    {"RequestError": "There was an error while doing the transformation, please check error log."})
                self.error_action("There was an error while doing the transformation, please check error log.")
                return

            self.transformation_matrix = T
            self.V0 = V0
            relative_check_pos = self.sensor_pad_file["data"][self.check_strip - 1][1:4]

            table_abs_pos = self.trans.vector_trans(relative_check_pos, T, V0)

            error = self.variables.table.move_to(list(table_abs_pos), True, self.variables.default_values_dict["Defaults"].get("height_movement", 800))
            if error:
                self.variables.message_to_main.put(error)
                self.error_action(error)
                return


        if step == 5:
            # calculate the transformation and save it
            self.set_checkboxes([True, True, True, True, True]) # The last true only when alignemt was successful
            self.variables.default_values_dict["Defaults"]["trans_matrix"] = self.transformation_matrix
            self.variables.default_values_dict["Defaults"]["V0"] = self.V0
            self.variables.default_values_dict["Defaults"]["Alignment"] = True

    def abort_action(self):
        '''Aborts the alignement proceedure'''
        if self.alignment_started:
            reply = QMessageBox.question(None, 'Warning',
                                         "Are you sure to stop the alignment proceedure? Any progress will be deleted.",
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                # Update the GUI
                self.alignment_started = False
                self.next_step_action(-1)
                self.do_alignment(-1)
            else:
                pass
        else:

            return

    def error_action(self, error):
        '''Aborts the alignement proceedure, without question'''
        if self.alignment_started:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("An error occured while moving the table \n \n"
                        "Error: "+ str(error))
            msg.setWindowTitle("Really bad error occured")
            msg.exec_()

            # Update the GUI
            self.alignment_started = False
            self.next_step_action(-1)
            self.do_alignment(-1)

    def what_to_do_text(self, step):
        '''This renders just the new text what to do'''

        if step == -1:
            self.lock_spinboxes(False)
            self.alignment.what_to_do_text.setText("Press the start button to start the alignment process.")

        elif step == 0:
            self.lock_spinboxes(True)
            self.alignment.what_to_do_text.setText("Please check if all informations are right and or change parameters. \n\n "
                                                   "In the next step, the table will move directly to the first alignment point. "
                                                   "Therefore, make sure that all obstacles are removed. \n \n"
                                                   "When ready click on 'Next Step' button.")

        elif step == 1:
            self.lock_spinboxes(False)
            self.alignment.what_to_do_text.setText("Please contact the needles on the FIRST alignment point.  \n \n"
                                                    "The Joystick has been activated, you can use it if you want, or just use the positioner, that is cool too.\n \n"
                                                   "Uncontact the needles from the sensor before you hit the 'Next Step' button.")

        elif step == 2:
            self.alignment.what_to_do_text.setText("Please contact the needles on the SECOND alignment point.  \n \n"
                                                   "Please DO NOT move the positioner in the xy-plane. The Joystick has been activated, use it!\n \n"
                                                   "Uncontact the needles from the sensor before you hit the 'Next Step' button.")

        elif step == 3:
            self.alignment.what_to_do_text.setText("Please contact the needles on the THIRD alignment point.  \n \n"
                                                   "Please DO NOT move the positioner in the xy-plane. The Joystick has been activated, use it!\n \n"
                                                   "Please do not uncontact the needles from the sensor before you hit the 'Next Step' button. \n \n"
                                                   "Warning: In the next step the table will move to a random strip to check the alignment")

        elif step == 4:
            self.alignment.what_to_do_text.setText("Please validate that the contact on strip: " + str(self.check_strip) + " is correct. "
                                                    "Please hit the 'Next step' button if everything looks ok.")

        elif step == 5:
            self.alignment.what_to_do_text.setText("The alignment proceedure is now finished. \n \n"
                                         "If you are interested: The transformation matrix is: " + str(self.transformation_matrix) + "."
                                                    "\n \n "
                                        "Another hit on the 'Next button' will move the table to the first strip")

    def adjust_alignment_points(self, adjust_point = 2, axis = 2, variable="implant_length"):
        '''This function adjusts the position of the alignment points so that a 3D alignment is possible'''
        to_adjust = self.reference_pads_positions[adjust_point -1][axis -1]
        to_adjust += float(self.sensor_pad_file["additional_params"].get(variable, 0))
        self.reference_pads_positions[adjust_point - 1][axis -1] = to_adjust

    def lock_spinboxes(self, state):
        '''Locks the spin boxes'''
        self.alignment.ref_1.setEnabled(state)
        self.alignment.ref_2.setEnabled(state)
        self.alignment.ref_3.setEnabled(state)


    def spin_box_action_1(self): # it has to be that way unfortunately (race conditions)
        '''If the alignment point are changed'''
        if self.alignment_started:
            ref = int(self.alignment.ref_1.value())
            self.reference_pads[0] = int(ref)
            self.update_reference_pad_positions()
        self.update_static()

    def spin_box_action_2(self):
        '''If the alignment point are changed'''
        if self.alignment_started:
            ref = int(self.alignment.ref_2.value())
            self.reference_pads[1] = int(ref)
            self.update_reference_pad_positions()
            #self.adjust_alignment_points(2)
        self.update_static()

    def spin_box_action_3(self):
        '''If the alignment point are changed'''
        if self.alignment_started:
            ref = int(self.alignment.ref_3.value())
            self.update_reference_pad_positions()
            self.reference_pads[2] = int(ref)
        self.update_static()

    def update_reference_pad_positions(self):
        self.reference_pads_positions = [self.sensor_pad_file["data"][item - 1][1:4] for item in self.reference_pads]
        self.adjust_alignment_points(2,1) #not so good

    def update_static(self, kwargs= None):
        '''This updates the static text of the gui, like sensor type'''

        # Set maxima and minima and value
        # Rare bug in spin boxes when a variable is assigned to the value and the range changes in a way that
        # it wont match with the range, the value in the variable get changed. Therefore, always increase the range
        # first and then change value, and then change range again.
        self.alignment.ref_1.setRange(1, 10000)
        self.alignment.ref_2.setRange(1, 10000)
        self.alignment.ref_3.setRange(1, 10000)

        self.alignment.ref_1.setValue(int(self.reference_pads[0]))
        self.alignment.ref_2.setValue(int(self.reference_pads[1]))
        self.alignment.ref_3.setValue(int(self.reference_pads[2]))

        self.alignment.ref_1.setRange(1, int(self.number_of_pads))
        self.alignment.ref_2.setRange(1, int(self.number_of_pads))
        self.alignment.ref_3.setRange(1, int(self.number_of_pads))

        self.first_ref = self.reference_pads_positions[0]
        self.secon_ref = self.reference_pads_positions[1]
        self.third_ref = self.reference_pads_positions[2]

        self.alignment.sensortype.setText("Sensor type: " + str(self.sensor))
        self.alignment.project.setText("Project: " + str(self.project))

        self.check_strip = randint(2, int(self.number_of_pads)-1)

        self.alignment.first_co_label.setText("First alignment coord: " + str(self.first_ref))
        self.alignment.second_co_label.setText("Second alignment coord: " + str(self.secon_ref))
        self.alignment.third_co_label.setText("Third alignment coord: " + str(self.third_ref))
        self.alignment.check_co_label.setText("Check alignment coord: " + str(self.sensor_pad_file["data"][self.check_strip-1][1:4]))


    def table_move(self):
        # Table control

        def table_move_indi():
            '''This function updates the table indicator'''
            if self.variables.default_values_dict["Defaults"]["table_is_moving"]:
                self.table_move_ui.table_ind.setStyleSheet("background : rgb(255,0,0); border-radius: 25px;border: 1px solid black;border-radius: 5px")
            else:
                self.table_move_ui.table_ind.setStyleSheet("background : grey; border-radius: 25px;border: 1px solid black;border-radius: 5px")


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
                    self.table_move_ui.frame_12.setEnabled(bool)
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
                        self.table_move_ui.frame_12.setDisabled(True)
                        self.table_move_ui.Enable_table.setChecked(False)
                        self.variables.table.set_joystick(False)
                        self.variables.default_values_dict["Defaults"]["zlock"] = True
                        self.variables.default_values_dict["Defaults"]["joystick"] = False
                        self.table_move_ui.unlock_Z.setChecked(False)
                        self.variables.table.set_axis([True, True, True])  # This is necessary so all axis can be adresses while move
                        return


                    self.variables.table.set_joystick(True)
                    self.variables.default_values_dict["Defaults"]["joystick"] = True
                    adjust_table_speed()
                    self.variables.table.set_axis([True, True, False]) # This is necessary so by default the joystick can adresses xy axis


                else:
                    self.table_move_ui.frame_12.setDisabled(bool)
                    self.table_move_ui.Enable_table.setChecked(False)
                    self.variables.table.set_joystick(False)
                    self.variables.default_values_dict["Defaults"]["zlock"] = True
                    self.variables.default_values_dict["Defaults"]["joystick"] = False
                    self.table_move_ui.unlock_Z.setChecked(False)
                    self.variables.table.set_axis([True, True, True]) # This is necessary so all axis can be adresses while move
            else:
                # This will be done when the table control will be dissabled
                self.table_move_ui.frame_12.setEnabled(bool)
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
                    self.variables.table.set_axis([True, True, True])
                    self.table_move_ui.unlock_Z.setChecked(True)
                    self.variables.default_values_dict["Defaults"]["zlock"] = False
                else:
                    self.table_move_ui.unlock_Z.setChecked(False)
            else:
                self.variables.table.set_axis([True, True, False])
                self.variables.default_values_dict["Defaults"]["zlock"] = True
                self.table_move_ui.unlock_Z.setChecked(False)


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




