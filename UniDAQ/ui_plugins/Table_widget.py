
import logging
from PyQt5.QtWidgets import QMessageBox


class Table_widget(object):

    def __init__(self, gui):
        """Configures the table widget"""
        try:
            super(Table_widget, self).__init__(gui)
        except:
            super(Table_widget, self).__init__()
        self.gui = gui
        self.Tablog = logging.getLogger(__name__)
        self.gui.table_frame.setDisabled(True)
        
        if "Table_control" in self.variables.devices_dict:
            self.gui.x_move.setMinimum(float(self.variables.devices_dict["Table_control"]["table_xmin"]))
            self.gui.x_move.setMaximum(float(self.variables.devices_dict["Table_control"]["table_xmax"]))

            self.gui.y_move.setMinimum(float(self.variables.devices_dict["Table_control"]["table_ymin"]))
            self.gui.y_move.setMaximum(float(self.variables.devices_dict["Table_control"]["table_ymax"]))

            self.gui.z_move.setMinimum(float(self.variables.devices_dict["Table_control"]["table_zmin"]))
            self.gui.z_move.setMaximum(float(self.variables.devices_dict["Table_control"]["table_zmax"]))

            if "current_speed" in self.variables.devices_dict["Table_control"]:
                speed = int(float(self.variables.devices_dict["Table_control"]["current_speed"]) / float(self.variables.devices_dict["Table_control"]["default_speed"])* 100)
                self.gui.Table_speed.setValue(speed)
            else:
                self.gui.Table_speed.setValue(100)
                self.variables.devices_dict["Table_control"].update({"current_speed" : float(self.variables.devices_dict["Table_control"]["default_speed"])})


        else:
            self.gui.x_move.setMinimum(float(0))
            self.gui.x_move.setMaximum(float(0))
            self.gui.y_move.setMinimum(float(0))
            self.gui.y_move.setMaximum(float(0))
            self.gui.z_move.setMinimum(float(0))
            self.gui.z_move.setMaximum(float(0))
            self.gui.Table_speed.setValue(10)

        self.gui.x_move.sliderReleased.connect(self.adjust_x_pos)
        self.gui.y_move.sliderReleased.connect(self.adjust_y_pos)
        self.gui.z_move.sliderReleased.connect(self.adjust_z_pos)
        self.gui.got_to_previous.clicked.connect(self.move_previous)
        self.gui.Table_speed.valueChanged.connect(self.adjust_table_speed)
        self.gui.unlock_Z.clicked.connect(self.z_pos_warning)
        self.gui.Enable_table.clicked['bool'].connect(self.enable_table_control)
        self.variables.add_update_function(self.table_move_indi)
        
    def table_move_indi(self):
        '''This function updates the table indicator'''
        if self.variables.default_values_dict["settings"]["table_is_moving"]:
            self.gui.table_ind.setStyleSheet("background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px")
        else:
            self.gui.table_ind.setStyleSheet("background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px")


    def adjust_table_speed(self): # must be here because of reasons
        '''This function adjusts the speed of the table'''
        speed = int(float(self.variables.devices_dict["Table_control"]["default_joy_speed"])/100. * float(self.gui.Table_speed.value()))
        self.variables.table.set_joystick_speed(float(speed))


    def adjust_x_pos(self):
        '''This function adjusts the xpos of the table'''
        pos = self.variables.table.get_current_position()
        self.variables.table.set_joystick(False)
        self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
        xpos = self.gui.x_move.value()
        error = self.variables.table.move_to([xpos, pos[1], pos[2]], True, self.variables.default_values_dict["settings"]["height_movement"])
        self.variables.table.set_joystick(True)
        self.variables.table.set_axis([True, True, False])  # so z axis cannot be adressed


    def adjust_y_pos(self):
        '''This function adjusts the xpos of the table'''
        pos = self.variables.table.get_current_position()
        self.variables.table.set_joystick(False)
        self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
        ypos = self.gui.y_move.value()
        error = self.variables.table.move_to([pos[0], ypos, pos[2]], self.variables.default_values_dict["settings"]["height_movement"])
        self.variables.table.set_joystick(True)
        self.variables.table.set_axis([True, True, False])  # so z axis cannot be adressed

    def adjust_z_pos(self):
        '''This function adjusts the xpos of the table'''
        pos = self.variables.table.get_current_position()
        self.variables.table.set_joystick(False)
        self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
        zpos = self.gui.z_move.value()
        error = self.variables.table.move_to([pos[0], pos[1], zpos], self.variables.default_values_dict["settings"]["height_movement"])
        self.variables.table.set_joystick(True)
        self.variables.table.set_axis([True, True, False])  # so z axis cannot be adressed

    def enable_table_control(self, bool):
        '''This function enables the table and the joystick frame'''
        if bool and self.variables.default_values_dict["settings"]["table_ready"]:
            #This will be called, when the table control is enabled
            reply = QMessageBox.question(None, 'Warning', "Are you sure move the table? \n Warning: If measurement is running table movement ist not possible", QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes and not self.variables.default_values_dict["settings"]["Measurement_running"]:
                self.gui.table_frame.setEnabled(bool)
                if self.gui.z_move.isEnabled():
                    self.gui.z_move.setEnabled(False)
                    self.gui.unlock_Z.toggle()
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
                    self.gui.table_frame.setDisabled(True)
                    self.gui.Enable_table.setChecked(False)
                    self.variables.table.set_joystick(False)
                    self.variables.default_values_dict["settings"]["zlock"] = True
                    self.variables.default_values_dict["settings"]["joystick"] = False
                    self.gui.unlock_Z.setChecked(False)
                    self.variables.table.set_axis([True, True, True])  # This is necessary so all axis can be adresses while move
                    return


                self.variables.table.set_axis([True, True, False])  # This is necessary so by default the joystick can adresses xy axis
                self.variables.table.set_joystick(True)
                self.variables.default_values_dict["settings"]["joystick"] = True
                self.adjust_table_speed()



            else:
                self.gui.table_frame.setDisabled(bool)
                self.gui.Enable_table.setChecked(False)
                self.variables.table.set_joystick(False)
                self.variables.default_values_dict["settings"]["zlock"] = True
                self.variables.default_values_dict["settings"]["joystick"] = False
                self.gui.unlock_Z.setChecked(False)
                self.variables.table.set_axis([True, True, True]) # This is necessary so all axis can be adresses while move

        elif not self.variables.default_values_dict["settings"]["table_ready"]:
            self.Tablog.error("No table connected to the setup. Joystick cannot be activated.")
        else:
            # This will be done when the table control will be dissabled
            self.gui.table_frame.setEnabled(bool)
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True])

    def move_previous(self):
        '''This function moves the table back to the previous position'''
        self.variables.table.set_joystick(False)
        self.variables.table.set_axis([True, True, True]) # so all axis can be adressed
        errorcode = self.variables.table.move_to([self.previous_xloc, self.previous_yloc, self.previous_zloc], True, self.variables.default_values_dict["settings"]["height_movement"])
        self.variables.table.set_axis([True, True, False])  # so z axis is off again
        self.variables.table.set_joystick(True)

    def z_pos_warning(self):
        if self.variables.default_values_dict["settings"]["zlock"]:
            move_z = QMessageBox.question(None, 'Warning',"Moving the table in Z, can cause serious demage on the setup and sensor.", QMessageBox.Ok)
            if move_z:
                self.variables.table.set_axis([False, False, True])
                self.gui.unlock_Z.setChecked(True)
                self.variables.default_values_dict["settings"]["zlock"] = False
                self.variables.table.set_joystick(True)

            else:
                self.gui.unlock_Z.setChecked(False)
        else:
            self.variables.table.set_axis([True, True, False])
            self.variables.default_values_dict["settings"]["zlock"] = True
            self.gui.unlock_Z.setChecked(False)
            self.variables.table.set_joystick(True)

    def table_move_update(self):
        '''Here all functions concerning the table move update are handled'''
        pos = self.variables.table.get_current_position()
        self.gui.x_move.setProperty("value", int(pos[0]))
        self.gui.y_move.setProperty("value", int(pos[1]))
        self.gui.z_move.setProperty("value", int(pos[2]))