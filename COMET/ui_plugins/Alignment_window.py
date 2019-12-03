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
import re
from ..utilities import transformation, connection_test
from .Table_widget import Table_widget


class Alignment_window(Table_widget):

    def __init__(self, GUI, layout):

        self.log = logging.getLogger(__name__)

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
        self.connection_test_switchings = ["DC1Test", "DC2Test", "AC1Test", "AC2Test"]


        self.variables = GUI
        self.connection_test_device = self.variables.devices_dict.get("2410SMU", None)
        if not self.connection_test_device:
            self.log.warning("No connection test SMU could be loaded!!!")
        self.transformation_matrix = self.variables.default_values_dict["settings"].get("trans_matrix", None)
        self.V0 = self.variables.default_values_dict["settings"].get("V0", None)
        self.layout = layout
        self.child_layouts = {"Table": None}
        self.trans = transformation()

        # Alignment tab
        alignment_widget = QWidget()
        self.alignment = self.variables.load_QtUi_file("Alignment.ui", alignment_widget)
        self.layout.addWidget(alignment_widget)

        self.child_layouts["Table"] = self.alignment.Table_Layout

        # Init the other classes
        super(Alignment_window, self).__init__(self) # I need the main

        # Load camera
        try:
            from .Ueye_camera_main import Ueye_main
            #self.alignment.layout_camera.setAlignment(Qt.AlignVertical_Mask)
            self.camera = Ueye_main(self.alignment.layout_camera, roi_width=1280, roi_height=1024)
        except ImportError:
            self.log.warning("Could not import camera module")


        # Asign the buttons
        self.alignment.ref_1.valueChanged.connect(self.spin_box_action_1)
        self.alignment.ref_2.valueChanged.connect(self.spin_box_action_2)
        self.alignment.ref_3.valueChanged.connect(self.spin_box_action_3)
        self.alignment.StartAlignment_btn.clicked.connect(self.start_alignment_action)
        self.alignment.nextstep_btn.clicked.connect(lambda: self.next_step_action(None))
        self.alignment.abort_btn.clicked.connect(self.abort_action)
        self.alignment.move_to_strip_button.clicked.connect(self.move_to_strip_action)
        self.alignment.camera_on_Button.clicked.connect(self.camera.start)
        self.alignment.camera_off_Button.clicked.connect(self.camera.stop)
        self.alignment.test_needle_conn_pushButton.clicked.connect(self.test_needle_contact_action)

        self.variables.add_update_function(self.current_strip_lcd)

        # Find pad data in the additional files and parse them
        self.pad_files = self.variables.framework_variables["Configs"]["additional_files"].get("Pad_files",{})
        if self.pad_files:
            self.parse_pad_files(self.pad_files)
        else:
            self.log.error("No pad files found! Please check if they are correctly defined in the configs!")

        self.what_to_do_text(-1) # Initializes the text

    def set_needle_contact_lamp(self, state):
        states = {"contact unclear": "QFrame { background :rgb(255, 215, 0) }",
                  "contact": "QFrame { background :rgb(36, 216, 93) }",
                 "no contact": "QFrame { background :rgb(214, 40, 49) }"}
        self.alignment.Needle_connection_label.setStyleSheet(states.get(state.lower()))
        self.alignment.Needle_connection_label.setText(state.upper())

    def test_needle_contact_action(self):
        """Test the needle contact"""
        if self.variables.switching and self.connection_test_device:
            res = connection_test(self.connection_test_switchings, self.variables.switching,
                                  self.variables.vcw, self.connection_test_device,
                                  target_resistance=2.5, abs_err=5.)
            if isinstance(res, bool):
                self.set_needle_contact_lamp("contact")
            else:
                self.log.critical("Needles {} have no contact!".format(res))
                self.set_needle_contact_lamp("no contact")


    def parse_pad_files(self, parent_dict):
        """
        Parses the parent directory of pad files, data must be a str
        :param parent_dict:
        :return:
        """

        # Separate header and data via regex
        data_pattern = re.compile(r"(\w+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\n", re.MULTILINE) # Todo: Its possible to do all the work with regex
        for project, sensors in parent_dict.items():
            for sensor, raw_data in sensors.items():
                #parent_dict[project][sensor]["data"] = {k: v for d in [{str(line[0]): [float(x) for x in line[1:]]} for line in data_pattern.findall(raw_data["raw"])] for k, v in d.items()}
                Data = data_pattern.findall(raw_data["raw"])
                parent_dict[project][sensor]["data"]= dict(zip([line[0] for line in Data],
                                                               [tuple(float(x) for x in line[1:]) for line in Data]))

                # Find reference pads
                find_parameters = re.compile(r"^(\w+\s?\w+):\s+(.+)", re.MULTILINE)
                parent_dict[project][sensor]["additional_params"] = {str(x[1]).strip(): x[2].strip() for x in find_parameters.finditer(raw_data["raw"])}

                # Get reference pads alone
                reference_pad_pattern = re.compile(r"(reference.?pad.?\d?):\s+(\d+)", re.MULTILINE)
                parent_dict[project][sensor]["reference_pads"] = [x[2] for x in reference_pad_pattern.finditer(raw_data["raw"])]


    def current_strip_lcd(self):
        '''This function updtes the current strip lcd display'''
        current_lcd_value = self.alignment.current_strip_lcdNumber.intValue()
        current_strip = self.variables.default_values_dict["settings"].get("current_strip",-1)

        if current_lcd_value != current_strip:
            self.alignment.current_strip_lcdNumber.display(current_strip)

    def move_to_strip_action(self):
        '''This is the action when the move to strip button is pressed'''
        self.set_needle_contact_lamp("contact unclear")
        if not self.variables.default_values_dict["settings"]["table_is_moving"]:
            strip_to_move = str(self.alignment.move_to_strip_spin.value())

            if self.variables.default_values_dict["settings"]["Alignment"]:
                error = self.variables.table.move_to_strip(self.sensor_pad_file, strip_to_move,
                                                           self.trans,
                                                           self.transformation_matrix, self.V0,
                                                           self.variables.default_values_dict["settings"]["height_movement"])
                if error:
                    #self.variables.message_to_main.put(error)
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


    def start_alignment_action(self):
        '''This function starts the whole alignement proceedure'''

        self.set_needle_contact_lamp("contact unclear")

        #First ask if you want to start the alignment
        if self.alignment_started:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("The alignment procedure is currently running.")
            msg.setWindowTitle("Alignment in progress")
            msg.exec_()
            return

        if not self.variables.table.table_ready:
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

        maximum_step = 5
        self.set_needle_contact_lamp("contact unclear")

        if step == None:
            self.alignment_step += 1 # so the next step is executed
            step = self.alignment_step

        if step > maximum_step or not self.alignment_started:
            self.what_to_do_text(-1) # Resets the text
            if self.variables.default_values_dict["settings"]["Alignment"]:
                success = self.variables.table.move_to_strip(self.sensor_pad_file, self.reference_pads[0],
                                                           self.trans,
                                                           self.transformation_matrix, self.V0,
                                                           self.variables.default_values_dict["settings"]["height_movement"])
                if not success:
                    self.error_action(success)
                    return
            self.alignment_started = False

        if self.alignment_started:
            # First set the GUI
            self.what_to_do_text(step)
            self.do_alignment(step)

        if step == maximum_step:
            self.alignment_started = False

    def set_checkboxes(self, list):
        '''This function sets the checkboxes for the checklist'''
        for i, state in enumerate(list):
            getattr(self.alignment, "ali_" + str(i)).setChecked(state)

    def do_alignment(self, step):
        '''Does the steps for the alignment'''

        if step == -1:
            # reset all elements
            self.set_checkboxes([False, False, False, False, False])
            self.variables.default_values_dict["settings"]["Alignment"] = False # So I cannot do a measuremnt until the alignment is done

        if step == 0:
            # Reset some elements and set new elements
            self.set_checkboxes([False, False, False, False, False])
            # Get sensor
            self.project = self.variables.default_values_dict["settings"]["Current_project"]
            self.sensor = str(self.variables.default_values_dict["settings"]["Current_sensor"])
            try:
                self.sensor_pad_file = self.pad_files[self.project][self.sensor].copy()
                self.reference_pads = self.sensor_pad_file["reference_pads"][:]
                self.update_reference_pad_positions()
                # self.adjust_alignment_points(2) should be here but the spin boxes get asignal and then they would change again- > therefore only spin boxes change this value
                self.number_of_pads = len(self.sensor_pad_file["data"])
                self.update_static()
            except Exception as err:
                self.log.error("An error while accessing the pad files with error: {}".format(err))
                self.error_action("An error while accessing the pad files with error: {}".format(err))


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
            success = self.variables.table.relative_move_to(relative_movepos, True,
                                                            self.variables.default_values_dict["settings"]["height_movement"],
                                                            clearance=self.variables.default_values_dict["settings"]["clearance"])
            if not success:
                self.error_action(success)
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
            success = self.variables.table.relative_move_to(relative_movepos, True,
                                                            self.variables.default_values_dict["settings"]["height_movement"],
                                                            clearance=self.variables.default_values_dict["settings"]["clearance"])
            if not success:
                self.error_action(success)
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
                self.log.error("There was an error while doing the transformation, please check error log.")
                self.error_action("There was an error while doing the transformation, please check error log.")
                return

            self.transformation_matrix = T
            self.V0 = V0
            relative_check_pos = self.sensor_pad_file["data"][self.check_strip]
            table_abs_pos = self.trans.vector_trans(relative_check_pos, T, V0)

            success = self.variables.table.move_to(list(table_abs_pos), True, self.variables.default_values_dict["settings"]["height_movement"])
            if not success:
                self.error_action(success)
                return


        if step == 5:
            # calculate the transformation and save it
            self.set_checkboxes([True, True, True, True, True]) # The last true only when alignemt was successful
            self.variables.default_values_dict["settings"]["trans_matrix"] = self.transformation_matrix
            self.variables.default_values_dict["settings"]["V0"] = self.V0
            self.variables.default_values_dict["settings"]["Alignment"] = True

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
                self.set_needle_contact_lamp("contact unclear")
            else:
                pass
        else:

            return

    def error_action(self, error):
        '''Aborts the alignement proceedure, without question'''
        if self.alignment_started:
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
                                        "Another hit on the 'Next button' will move the table to the first reference strip")

    def adjust_alignment_points(self, adjust_point = 2, axis = 2, variable="implant_length"):
        '''This function adjusts the position of the alignment points so that a 3D alignment is possible'''
        to_adjust = self.reference_pads_positions[adjust_point -1][axis -1]
        to_adjust += float(self.sensor_pad_file["additional_params"].get(variable, 0))
        new_coord = list(self.reference_pads_positions[adjust_point - 1])
        new_coord[axis -1] = to_adjust
        self.reference_pads_positions[adjust_point - 1] = tuple(new_coord)


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
        self.reference_pads_positions = [self.sensor_pad_file["data"][str(item)] for item in self.reference_pads]
        self.adjust_alignment_points(2,1) #not so good

    def update_static(self):
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

        self.check_strip = str(randint(2, int(self.number_of_pads)-1))
        if self.check_strip not in self.sensor_pad_file:
            self.check_strip = "2"

        self.alignment.first_co_label.setText("First alignment coord: " + str(self.first_ref))
        self.alignment.second_co_label.setText("Second alignment coord: " + str(self.secon_ref))
        self.alignment.third_co_label.setText("Third alignment coord: " + str(self.third_ref))
        self.alignment.check_co_label.setText("Check alignment coord: " + str(self.sensor_pad_file["data"][self.check_strip]))
