import logging
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QWidget
import os
from time import asctime


class Controls_widget(object):
    def __init__(self, gui):
        """Configures the cotrols widget"""

        self.Conlog = logging.getLogger(__name__)
        self.gui = gui

        # Controls widget
        if not "Start" in gui.child_layouts:
            self.Conlog.error("No layout found to render controls widget. Skipping...")
            return
        controls_Qwidget = QWidget()
        self.controls_layout = gui.child_layouts["Start"]
        self.controls_widget = self.variables.load_QtUi_file(
            "Start_Stop.ui", controls_Qwidget
        )
        self.controls_layout.addWidget(controls_Qwidget)

        super(Controls_widget, self).__init__(gui)
        self.Start_Stop_gui = self.controls_widget

        self.Start_Stop_gui.quit_button.clicked.connect(self.exit_order)
        self.Start_Stop_gui.start_button.clicked.connect(self.Start_order)
        self.Start_Stop_gui.stop_button.clicked.connect(self.Stop_order)

        self.Start_Stop_gui.progressBar.setRange(0, 100)
        self.Start_Stop_gui.progressBar.setValue(0.0)
        self.variables.default_values_dict["settings"]["progress"] = 0.0

        # Adding update functions
        self.variables.add_update_function(self.error_update)
        self.variables.add_update_function(self.update_statistics)
        self.variables.add_update_function(self.update_current_state)
        self.variables.add_update_function(self.update_progress_bar)

        self.states = {
            "Measurement running": "background : rgb(50,20,200); border-radius: 5px",
            "IDLE": "background : rgb(50,100,100); border-radius: 5px",
            "DEFAULT": "background : rgb(50,10,200); border-radius: 5px",
        }

    def update_progress_bar(self):
        """Updates the progress bar"""
        self.Start_Stop_gui.progressBar.setValue(
            self.variables.default_values_dict["settings"].get("progress", 0.0) * 100
        )

    def update_current_state(self):
        """Updates the label of the state of the program. Either IDLE or Measurement running"""

        if (
            self.Start_Stop_gui.state_indi.text()
            != self.variables.default_values_dict["settings"]["State"]
        ):
            self.Start_Stop_gui.state_indi.setText(
                self.variables.default_values_dict["settings"]["State"]
            )
            self.Start_Stop_gui.state_indi.setStyleSheet(
                self.states.get(
                    self.variables.default_values_dict["settings"]["State"], "DEFAULT"
                )
            )

    # Orders
    def exit_order(self):
        reply = QMessageBox.question(
            None, "Warning", "Are you sure to quit?", QMessageBox.Yes, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            result = QMessageBox.question(
                None,
                "Save session?",
                "Do you want to save the current session?",
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if result == QMessageBox.Yes:
                self.variables.message_to_main.put({"SAVE_SESSION": True})
            self.variables.message_to_main.put({"CLOSE_PROGRAM": True})
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(
                "The program is shuting down, depending on the amount of instruments attached to the PC this can take a while..."
            )
            # msg.setInformativeText("This is additional information")
            msg.setWindowTitle("Shutdown in progress")
            # msg.setDetailedText("The details are as follows:")
            msg.exec_()

    def onStart(self):
        """The QWidget onStart construct. This is used for the ToolBar start stop etc."""
        self.Conlog.critical("Start order send by non Tab intern signal.")
        self.Start_order()

    def onStop(self):
        """The QWidget onStart construct. This is used for the ToolBar start stop etc."""
        self.Conlog.critical("Stop order send by non Tab intern signal.")
        self.Stop_order()

    def Start_order(self):
        if self.variables.default_values_dict["settings"][
            "Current_filename"
        ] and os.path.isdir(
            self.variables.default_values_dict["settings"]["Current_directory"]
        ):
            if not self.variables.default_values_dict["settings"][
                "Measurement_running"
            ]:
                self.variables.reset_plot_data()

            # Ensures that the new values are in the state machine
            # Todo: not really pretty, try pulling this out of here and place it at a better place
            try:
                self.variables.ui_plugins["Settings_window"].load_new_settings()
            except:
                pass

            additional_settings = {
                "Save_data": True,
                "Filepath": self.variables.default_values_dict["settings"][
                    "Current_directory"
                ],
                "Filename": self.variables.default_values_dict["settings"][
                    "Current_filename"
                ],
                "Project": self.variables.default_values_dict["settings"][
                    "Current_project"
                ],
                "Sensor": self.variables.default_values_dict["settings"][
                    "Current_sensor"
                ],
                "environment": self.variables.default_values_dict["settings"][
                    "Log_environment"
                ],  # if enviroment surveillance should be done
                "skip_init": False,
            }  # warning this prevents the device init

            header = (
                "# Measurement file: \n "
                "# Project: "
                + self.variables.default_values_dict["settings"]["Current_project"]
                + "\n "
                "# Sensor Type: "
                + self.variables.default_values_dict["settings"]["Current_sensor"]
                + "\n "
                "# ID: "
                + self.variables.default_values_dict["settings"]["Current_filename"]
                + "\n "
                "# Operator: "
                + self.variables.default_values_dict["settings"]["Current_operator"]
                + "\n "
                "# Date: " + str(asctime()) + "\n\n"
            )

            job = self.generate_job()
            if job:
                job.update(additional_settings)
                job["Header"] = header
                self.send_job(job)

        else:
            reply = QMessageBox.information(
                None,
                "Warning",
                "Please enter a valid filepath and filename.",
                QMessageBox.Ok,
            )

    def Stop_order(self):
        order = {"ABORT_MEASUREMENT": True}  # just for now
        self.variables.message_to_main.put(order)

    def Load_order(self):
        """This function loads an old measurement file and displays it if no measurement is curently conducted"""

        if not self.variables.default_values_dict["settings"]["Measurement_running"]:
            fileDialog = QFileDialog()
            file = fileDialog.getOpenFileName()

            if file[0]:
                pass
        else:
            reply = QMessageBox.information(
                None,
                "Warning",
                "You cannot load a measurement files while data taking is in progress.",
                QMessageBox.Ok,
            )

    def update_statistics(self):
        self.Start_Stop_gui.bias_voltage_lcd.display(
            float(
                self.variables.default_values_dict["settings"].get("bias_voltage", "0")
            )
        )
        # self.Start_Stop_gui.current_pad_lcd.display(self.variables.default_values_dict["settings"].get("current_strip", None))
        # self.Start_Stop_gui.bad_pads_lcd.display(self.variables.default_values_dict["settings"].get("Bad_strips", None))

    # Update functions
    def error_update(self):
        last_errors = self.variables.event_loop_thread.error_log
        error_text = ""
        for error in reversed(last_errors[-100:]):
            error_text += ": ".join(error) + "\n"

        if (
            self.Start_Stop_gui.event_log.text() != error_text
        ):  # Only update text if necessary
            self.Start_Stop_gui.event_log.setText(error_text)

    def led_update(self):
        """Debricated"""

        current_state = self.variables.default_values_dict["settings"][
            "current_led_state"
        ]
        alignment = self.variables.default_values_dict["settings"]["Alignment"]
        running = self.variables.default_values_dict["settings"]["Measurement_running"]
        enviroment = self.variables.default_values_dict["settings"][
            "Environment_status"
        ]

        if current_state != "running" and running:
            self.variables.default_values_dict["settings"][
                "current_led_state"
            ] = "running"
            self.Start_Stop_gui.textbox_led.setStyleSheet(
                "background : rgb(0,0,255); border-radius: 25px"
            )
            self.Start_Stop_gui.textbox_led.setText("Measurement running")
            return

        elif current_state != "Alignment" and not alignment and not running:
            self.variables.default_values_dict["settings"][
                "current_led_state"
            ] = "Alignment"
            self.Start_Stop_gui.textbox_led.setStyleSheet(
                "background : rgb(255,0,0); border-radius: 25px"
            )
            self.Start_Stop_gui.textbox_led.setText("Alignement missing")
            return

        elif (
            current_state != "environment"
            and not enviroment
            and alignment
            and not running
        ):
            self.variables.default_values_dict["settings"][
                "current_led_state"
            ] = "environment"
            self.Start_Stop_gui.textbox_led.setStyleSheet(
                "background : rgb(255,153,51); border-radius: 25px"
            )
            self.Start_Stop_gui.textbox_led.setText("Environment status not ok")
            return

        if current_state != "ready" and alignment and not running and enviroment:
            self.variables.default_values_dict["settings"][
                "current_led_state"
            ] = "ready"
            self.Start_Stop_gui.textbox_led.setStyleSheet(
                "background : rgb(0,255,0); border-radius: 25px"
            )
            self.Start_Stop_gui.textbox_led.setText("Ready to go")
            return

    def send_job(self, job):
        # Check if filepath is a valid path
        if job["Filename"] and os.path.isdir(os.path.normpath(job["Filepath"])):
            # self.final_job.update({"Header": header})
            self.variables.message_from_main.put({"Measurement": job})
            self.Conlog.info("Sendet job: " + str({"Measurement": job}))
        else:
            self.Conlog.error(
                "Please enter a valid path and name for the measurement file."
            )
