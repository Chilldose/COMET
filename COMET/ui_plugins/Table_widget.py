import logging
from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtCore
from time import time


class Table_widget(object):
    def __init__(self, gui):
        """Configures the table widget"""

        self.Tablog = logging.getLogger(__name__)
        self.last_update = 0.0

        # Table widget
        if not "Table" in gui.child_layouts:
            self.Tablog.error("No layout found to render table widget. Skipping...")
            return
        Table_Qwidget = QWidget()
        self.table_layout = gui.child_layouts["Table"]
        self.table_widget = self.variables.load_QtUi_file(
            "table_control.ui", Table_Qwidget
        )
        self.table_layout.addWidget(Table_Qwidget)

        try:
            super(Table_widget, self).__init__(gui)
        except:
            pass

        self.Table_gui = self.table_widget
        self.Table_gui.table_frame.setDisabled(True)

        if "Table_control" in self.variables.devices_dict:
            self.init_table_position_indicators()
        else:
            self.Table_gui.x_move.setMinimum(float(0))
            self.Table_gui.x_move.setMaximum(float(0))
            self.Table_gui.y_move.setMinimum(float(0))
            self.Table_gui.y_move.setMaximum(float(0))
            self.Table_gui.z_move.setMinimum(float(0))
            self.Table_gui.z_move.setMaximum(float(0))
            self.Table_gui.Table_speed.setValue(0)

        self.Table_gui.x_move.sliderReleased.connect(self.adjust_x_pos)
        self.Table_gui.y_move.sliderReleased.connect(self.adjust_y_pos)
        self.Table_gui.z_move.sliderReleased.connect(self.adjust_z_pos)
        self.Table_gui.got_to_previous.clicked.connect(self.move_previous)
        self.Table_gui.Table_speed.valueChanged.connect(self.adjust_table_speed)
        self.Table_gui.unlock_Z.clicked.connect(self.z_pos_warning)
        self.Table_gui.Enable_table.clicked["bool"].connect(self.enable_table_control)
        self.Table_gui.init_table_Button.clicked.connect(self.init_table_action)
        self.Table_gui.move_down_button.clicked.connect(self.move_down_action)
        self.Table_gui.move_up_button.clicked.connect(self.move_up_action)
        self.Table_gui.check_position.clicked.connect(self.check_position_action)
        self.Table_gui.Unload_sensorpushButton.clicked.connect(
            self.unload_sensor_action
        )
        self.Table_gui.load_sensor_pushButton.clicked.connect(self.load_sensor_action)
        self.Table_gui.Up_button.clicked.connect(self.moveYplus)
        # The directions are setup specific
        self.Table_gui.Down_button.clicked.connect(self.moveYminus)
        self.Table_gui.Left_button.clicked.connect(self.moveXminus)
        self.Table_gui.Right_button.clicked.connect(self.moveXplus)
        self.Table_gui.Zup_button.clicked.connect(self.moveZplus)
        self.Table_gui.Zdown_button.clicked.connect(self.moveZminus)
        self.Table_gui.XPos.returnPressed.connect(self.move_to_user_defined_pos)
        self.Table_gui.YPos.returnPressed.connect(self.move_to_user_defined_pos)
        self.Table_gui.ZPos.returnPressed.connect(self.move_to_user_defined_pos)

        self.variables.add_update_function(self.update_tableIndi_periodically)

        # Set key press events

        setattr(Table_Qwidget, "keyPressEvent", self.keyPressEvent)

    def update_tableIndi_periodically(self):
        """Updates the table in dicator every now an than"""
        if abs(self.last_update - time()) > 0.5:
            self.table_move_indi()
            self.last_update = time()

    def keyPressEvent(self, event):
        if self.Table_gui.Arro_control_frame.isEnabled():
            if event.key() == QtCore.Qt.Key_Up or event.key() == QtCore.Qt.Key_W:
                self.moveYplus()
                self.Tablog.debug(
                    "Pressed move Y plus keys. Key: {}".format(event.key())
                )
            elif event.key() == QtCore.Qt.Key_Down or event.key() == QtCore.Qt.Key_S:
                self.moveYminus()
                self.Tablog.debug(
                    "Pressed move Y minus keys. Key: {}".format(event.key())
                )
            elif event.key() == QtCore.Qt.Key_Left or event.key() == QtCore.Qt.Key_A:
                self.moveXminus()
                self.Tablog.debug(
                    "Pressed move X minus keys. Key: {}".format(event.key())
                )
            elif event.key() == QtCore.Qt.Key_Right or event.key() == QtCore.Qt.Key_D:
                self.moveXplus()
                self.Tablog.debug(
                    "Pressed move X plus keys. Key: {}".format(event.key())
                )
            elif event.key() == QtCore.Qt.Key_PageUp:
                self.moveZplus()
                self.Tablog.debug(
                    "Pressed move Z plus keys. Key: {}".format(event.key())
                )
            elif event.key() == QtCore.Qt.Key_PageDown:
                self.moveZminus()
                self.Tablog.debug(
                    "Pressed move Z minus keys. Key: {}".format(event.key())
                )
            event.accept()

    def check_position_action(self):
        """Checks the position of the table."""
        if self.variables.table:
            pos = self.variables.table.get_current_position()
            self.position_indicators_update()
            return pos
        else:
            self.Tablog.error("No table connected...")

    def move_up_action(self):
        """Moves the table up"""
        succ = self.variables.table.move_up(
            lifting=self.variables.default_values_dict["settings"]["height_movement"]
        )
        self.position_indicators_update()
        return succ

    def move_down_action(self):
        """Moves the table up"""
        succ = self.variables.table.move_down(
            lifting=self.variables.default_values_dict["settings"]["height_movement"]
        )
        self.position_indicators_update()
        return succ

    def init_table_action(self):
        """Does the init for the Table"""
        self.Tablog.critical("Pressed the table init button...")
        reply = QMessageBox.question(
            None,
            "Warning",
            "Are you sure to init the table?\n"
            "This action will cause the table to move to its most outer point in all directions.\n"
            "This can cause serious damage to the setup. Please make sure the table can move freely!",
            QMessageBox.Yes,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.variables.table.initiate_table()
            self.variables.table.move_to(
                [
                    self.variables.devices_dict["Table_control"]["table_xmax"] / 2,
                    self.variables.devices_dict["Table_control"]["table_ymax"] / 2,
                    self.variables.devices_dict["Table_control"]["table_zmax"] / 2,
                ]
            )
            self.position_indicators_update()
        else:
            self.Tablog.info("No table init will be done...")

    def table_move_indi(self):
        """This function updates the table indicator"""
        if self.variables.default_values_dict["settings"].get("table_is_moving", None):
            self.Table_gui.table_ind.setStyleSheet(
                "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
            )
        else:
            self.Table_gui.table_ind.setStyleSheet(
                "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
            )

    def adjust_table_speed(self):  # must be here because of reasons
        """This function adjusts the speed of the table"""
        speed = int(
            float(self.variables.devices_dict["Table_control"]["default_joy_speed"])
            / 100.0
            * float(self.Table_gui.Table_speed.value())
        )
        self.variables.table.set_joystick_speed(float(speed))
        self.Table_gui.Table_speed_indicator.display(speed)

    def adjust_x_pos(self):
        """This function adjusts the xpos of the table"""
        pos = self.variables.table.get_current_position()
        self.variables.table.set_joystick(False)
        self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
        xpos = self.Table_gui.x_move.value()
        error = self.variables.table.move_to(
            [xpos, pos[1], pos[2]],
            True,
            self.variables.default_values_dict["settings"]["height_movement"],
        )
        self.variables.table.set_joystick(True)
        self.variables.table.set_axis(
            [True, True, False]
        )  # so z axis cannot be adressed
        self.position_indicators_update()

    def adjust_y_pos(self):
        """This function adjusts the ypos of the table"""
        pos = self.variables.table.get_current_position()
        self.variables.table.set_joystick(False)
        self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
        ypos = self.Table_gui.y_move.value()
        error = self.variables.table.move_to(
            [pos[0], ypos, pos[2]],
            self.variables.default_values_dict["settings"]["height_movement"],
        )
        self.variables.table.set_joystick(True)
        self.variables.table.set_axis(
            [True, True, False]
        )  # so z axis cannot be adressed
        self.position_indicators_update()

    def adjust_z_pos(self):
        """This function adjusts the zpos of the table"""
        pos = self.variables.table.get_current_position()
        self.variables.table.set_joystick(False)
        self.variables.table.set_axis([True, True, True])  # so all axis can be adressed
        zpos = self.Table_gui.z_move.value()
        error = self.variables.table.move_to(
            [pos[0], pos[1], zpos],
            self.variables.default_values_dict["settings"]["height_movement"],
        )
        self.variables.table.set_joystick(True)
        self.variables.table.set_axis(
            [True, True, False]
        )  # so z axis cannot be adressed
        self.position_indicators_update()

    def enable_table_control(self, bool):
        """This function enables the table and the joystick frame"""
        self.position_indicators_update()
        if bool and self.variables.default_values_dict["settings"]["table_ready"]:
            # This will be called, when the table control is enabled
            reply = QMessageBox.question(
                None,
                "Warning",
                "Are you sure move the table? \n Warning: If measurement is running table movement is not possible",
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if (
                reply == QMessageBox.Yes
                and not self.variables.default_values_dict["settings"][
                    "Measurement_running"
                ]
            ):
                self.Tablog.info("Switched on joystick control")
                self.Table_gui.table_frame.setEnabled(bool)
                if self.Table_gui.z_move.isEnabled():
                    self.Table_gui.z_move.setEnabled(False)
                    self.Table_gui.unlock_Z.toggle()
                if not self.variables.table.store_current_position_as_previous():
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Information)
                    msg.setText(
                        "There seems to be a bad error with the table. Is it connected to the PC?"
                    )
                    # msg.setInformativeText("This is additional information")
                    msg.setWindowTitle("Really bad error occured.")
                    # msg.setDetailedText("The details are as follows:")
                    msg.exec_()
                    self.Table_gui.table_frame.setDisabled(True)
                    self.Table_gui.Enable_table.setChecked(False)
                    self.variables.table.set_joystick(False)
                    self.variables.default_values_dict["settings"]["zlock"] = True
                    self.variables.default_values_dict["settings"]["joystick"] = False
                    self.Table_gui.unlock_Z.setChecked(False)
                    self.variables.table.set_axis(
                        [True, True, True]
                    )  # This is necessary so all axis can be adresses while move
                    return

                self.variables.table.set_axis(
                    [True, True, False]
                )  # This is necessary so by default the joystick can adresses xy axis
                self.variables.table.set_joystick(True)
                self.variables.default_values_dict["settings"]["joystick"] = True
                self.adjust_table_speed()

            else:
                reply = QMessageBox.question(
                    None,
                    "Warning",
                    "Are you sure to disable the joystick controls?",
                    QMessageBox.Yes,
                    QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    self.Tablog.info("Switched off joystick control")
                    self.Table_gui.table_frame.setDisabled(bool)
                    self.Table_gui.Enable_table.setChecked(False)
                    self.variables.table.set_joystick(False)
                    self.variables.default_values_dict["settings"]["zlock"] = True
                    self.variables.default_values_dict["settings"]["joystick"] = False
                    self.Table_gui.unlock_Z.setChecked(False)
                    self.variables.table.set_axis(
                        [True, True, True]
                    )  # This is necessary so all axis can be adresses while move

        elif not self.variables.default_values_dict["settings"]["table_ready"]:
            self.Tablog.error(
                "No table connected to the setup. Joystick cannot be activated."
            )
        else:
            # This will be done when the table control will be dissabled
            self.Table_gui.table_frame.setEnabled(bool)
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis([True, True, True])

    def unload_sensor_action(self):
        """Moves the table to the edge so you can load a new sensor"""
        if self.variables.table:
            self.Table_gui.table_ind.setStyleSheet(
                "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
            )
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis(
                [True, True, True]
            )  # so all axis can be adressed
            self.variables.table.move_table_to_edge(
                "y",
                False,
                self.variables.default_values_dict["settings"]["height_movement"],
                clearance=self.variables.default_values_dict["settings"][
                    "height_movement"
                ],
            )
            self.variables.table.set_axis([True, True, False])  # so z axis is off again
            self.position_indicators_update()
        else:
            self.Tablog.error("No table connected...")
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )

    def load_sensor_action(self):
        """Moves the table to the edge so you can load a new sensor"""
        if self.variables.table:
            self.Table_gui.table_ind.setStyleSheet(
                "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
            )
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis(
                [True, True, True]
            )  # so all axis can be addressed
            self.variables.table.move_previous_position(
                self.variables.default_values_dict["settings"]["height_movement"],
                clearance=self.variables.default_values_dict["settings"]["clearance"],
            )
            self.variables.table.set_axis([True, True, False])  # so z axis is off again
            self.position_indicators_update()
        else:
            self.Tablog.error("No table connected...")
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )

    def move_previous(self):
        """This function moves the table back to the previous position"""
        if self.variables.table:
            self.variables.table.set_joystick(False)
            self.variables.table.set_axis(
                [True, True, True]
            )  # so all axis can be addressed
            self.variables.table.move_previous_position(
                self.variables.default_values_dict["settings"]["height_movement"]
            )
            self.variables.table.set_axis([True, True, False])  # so z axis is off again
            self.position_indicators_update()
        else:
            self.Tablog.error("No table connected...")

    def z_pos_warning(self):
        if self.variables.default_values_dict["settings"]["zlock"]:
            move_z = QMessageBox.question(
                None,
                "Warning",
                "Moving the table in Z, can cause serious demage on the setup and sensor.",
                QMessageBox.Ok,
            )
            if move_z:
                self.position_indicators_update()
                self.variables.table.set_axis([False, False, True])
                self.Table_gui.unlock_Z.setChecked(True)
                self.variables.default_values_dict["settings"]["zlock"] = False
                self.variables.table.set_joystick(True)

            else:
                self.Table_gui.unlock_Z.setChecked(False)
        else:
            self.variables.table.set_axis([True, True, False])
            self.variables.default_values_dict["settings"]["zlock"] = True
            self.Table_gui.unlock_Z.setChecked(False)
            self.variables.table.set_joystick(True)

    def init_table_position_indicators(self):
        """Configs the the table move position indicators with the maximum and minimum values"""
        try:

            # Slider
            self.Table_gui.x_move.setMinimum(
                float(self.variables.devices_dict["Table_control"]["table_ymin"])
            )
            self.Table_gui.x_move.setMaximum(
                float(self.variables.devices_dict["Table_control"]["table_ymax"])
            )

            self.Table_gui.y_move.setMinimum(
                float(self.variables.devices_dict["Table_control"]["table_xmin"])
            )
            self.Table_gui.y_move.setMaximum(
                float(self.variables.devices_dict["Table_control"]["table_xmax"])
            )

            self.Table_gui.z_move.setMinimum(
                float(self.variables.devices_dict["Table_control"]["table_zmin"])
            )
            self.Table_gui.z_move.setMaximum(
                float(self.variables.devices_dict["Table_control"]["table_zmax"])
            )

            self.Table_gui.Table_speed.setMinimum(0)
            self.Table_gui.Table_speed.setMaximum(100)

            if "current_speed" in self.variables.devices_dict["Table_control"]:
                speed = int(
                    float(self.variables.devices_dict["Table_control"]["current_speed"])
                    / float(
                        self.variables.devices_dict["Table_control"]["default_speed"]
                    )
                    * 100
                )
                self.Table_gui.Table_speed.setValue(speed)
                self.Table_gui.Table_speed_indicator.display(speed)
            else:
                self.Table_gui.Table_speed.setValue(100)
                self.variables.devices_dict["Table_control"].update(
                    {
                        "current_speed": float(
                            self.variables.devices_dict["Table_control"][
                                "default_speed"
                            ]
                        )
                    }
                )
                self.Table_gui.Table_speed_indicator.display(100)

        except Exception as err:
            self.Tablog.error(
                "Table position indicator config error. Error: {}".format(err)
            )

    def position_indicators_update(self):
        """Here all functions concerning the table move update are handled"""
        if self.variables.table:
            pos = self.variables.table.get_current_position()
            self.Table_gui.y_move.setProperty("value", int(pos[0]))
            self.Table_gui.x_move.setProperty("value", int(pos[1]))
            self.Table_gui.z_move.setProperty("value", int(pos[2]))

            self.Table_gui.YPos.setText(str(pos[0]))
            self.Table_gui.XPos.setText(str(pos[1]))
            self.Table_gui.ZPos.setText(str(pos[2]))
        else:
            self.Tablog.critical(
                "Table position update not possible, due to missing Table instance."
            )

    def move_to_position_action(self, pos):
        """Moves table to a new position, based on the double spin boxes"""

        if (
            self.variables.table
            and not self.variables.default_values_dict["settings"]["table_is_moving"]
        ):
            self.variables.table.set_axis(
                [True, True, True]
            )  # so all axis can be adressed
            self.variables.table.move_to(pos, False)
            self.variables.table.set_axis([True, True, False])  # so z axis is off again
            self.position_indicators_update()
        elif self.variables.default_values_dict["settings"]["table_is_moving"]:
            self.Tablog.warning(
                "Table is currently moving, wait until movement is finished..."
            )
        else:
            self.Tablog.error("No table connected...")

    def rmove_to_position_action(self, pos):
        """Moves table to a new position, based on the double spin boxes"""

        if (
            self.variables.table
            and not self.variables.default_values_dict["settings"]["table_is_moving"]
        ):
            self.variables.table.set_axis(
                [True, True, True]
            )  # so all axis can be adressed
            self.variables.table.relative_move_to(pos, False)
            self.variables.table.set_axis([True, True, False])  # so z axis is off again
            self.position_indicators_update()
        elif self.variables.default_values_dict["settings"]["table_is_moving"]:
            self.Tablog.warning(
                "Table is currently moving, wait until movement is finished..."
            )
        else:
            self.Tablog.error("No table connected...")

    def moveXplus(self):
        """Moves the table in the yplus direction"""
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )
        step = self.Table_gui.Stepx_spinBox.value()
        self.rmove_to_position_action([step, 0, 0])
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )

    def moveXminus(self):
        """Moves the table in the yplus direction"""
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )
        step = self.Table_gui.Stepx_spinBox.value()
        self.rmove_to_position_action([-step, 0, 0])
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )

    def moveYplus(self):
        """Moves the table in the yplus direction"""
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )
        step = self.Table_gui.Stepy_spinBox.value()
        self.rmove_to_position_action([0, step, 0])
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )

    def moveYminus(self):
        """Moves the table in the yplus direction"""
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )
        step = self.Table_gui.Stepy_spinBox.value()
        self.rmove_to_position_action([0, -step, 0])
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )

    def moveZplus(self):
        """Moves the table in the yplus direction"""
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )
        step = self.Table_gui.Stepz_spinBox.value()
        self.rmove_to_position_action([0, 0, step])
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )

    def moveZminus(self):
        """Moves the table in the yplus direction"""
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )
        step = self.Table_gui.Stepz_spinBox.value()
        self.rmove_to_position_action([0, 0, -step])
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )

    def move_to_user_defined_pos(self):
        """Moves to a user defined position"""
        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(255,0,0); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )
        valid = False
        try:
            # Table at QTC is switched by 90 deg
            x = float(self.Table_gui.YPos.text())
            y = float(self.Table_gui.XPos.text())
            z = float(self.Table_gui.ZPos.text())
            valid = True
        except:
            self.Tablog.error("Non valid table coordinate input. Number needed.")
            x, y, z = 0, 0, 0
            return

        move = QMessageBox.question(
            None,
            "Warning",
            "Are you sure to move the table to the position {}.\nThis can cause serious damage to a sensor and setup!".format(
                [x, y, z]
            ),
            QMessageBox.Ok,
            QMessageBox.Abort,
        )
        if valid and move == QMessageBox.Ok:
            self.move_to_position_action([x, y, z])

        self.Table_gui.table_ind.setStyleSheet(
            "background: rgb(105,105,105); border-radius: 25px; border: 1px solid black; border-radius: 5px"
        )
