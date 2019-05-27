
import logging
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import os


class Controls_widget(object):

    def __init__(self, gui):
        """Configures the cotrols widget"""
        super(Controls_widget, self).__init__()
        self.gui = gui
        self.Conlog = logging.getLogger(__name__)

        self.gui.quit_button.clicked.connect(self.exit_order)
        self.gui.start_button.clicked.connect(self.Start_order)
        self.gui.stop_button.clicked.connect(self.Stop_order)

        self.gui.progressBar.setRange(0,100)
        self.gui.progressBar.setValue(0)

        # Adding update functions
        self.variables.add_update_function(self.error_update)
        self.variables.add_update_function(self.update_statistics)
        self.variables.add_update_function(self.update_current_state)
        #self.variables.add_update_function(self.led_update) # Todo: currently no led

    def update_current_state(self):
        """Updates the label of the state of the program. Either IDLE or Measurement running"""

        if self.variables.default_values_dict["settings"]["Measurement_running"] and not self.gui.state_indi.text() == "Measurement running":
            self.gui.state_indi.setText("Measurement running")
        elif not self.variables.default_values_dict["settings"]["Measurement_running"] and not self.gui.state_indi.text() == "IDLE":
            self.gui.state_indi.setText("IDLE")


    # Orders
    def exit_order(self):
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


    def Start_order(self):
        if self.variables.default_values_dict["settings"]["Current_filename"] and os.path.isdir(self.variables.default_values_dict["settings"]["Current_directory"]):
            if not self.variables.default_values_dict["settings"]["Measurement_running"]:
                self.variables.reset_plot_data()

            # Ensures that the new values are in the state machine
            self.variables.ui_plugins["Settings_window"].load_new_settings()

            additional_settings = {"Save_data": True,
                                           "Filepath": self.variables.default_values_dict["settings"]["Current_directory"],
                                           "Filename": self.variables.default_values_dict["settings"]["Current_filename"],
                                           "Project": self.variables.default_values_dict["settings"]["Current_project"],
                                           "Sensor": self.variables.default_values_dict["settings"]["Current_sensor"],
                                           "enviroment": self.gui.log_env_check.isChecked(), # if enviroment surveillance should be done
                                           "skip_init": False} #warning this prevents the device init

            self.job.generate_job(additional_settings)

        else:
            reply = QMessageBox.information(None, 'Warning', "Please enter a valid filepath and filename.", QMessageBox.Ok)

    def Stop_order(self):
        order = {"ABORT_MEASUREMENT": True} # just for now
        self.variables.message_to_main.put(order)

    def Load_order(self):
        '''This function loads an old measurement file and displays it if no measurement is curently conducted'''

        if not self.variables.default_values_dict["settings"]["Measurement_running"]:
            fileDialog = QFileDialog()
            file = fileDialog.getOpenFileName()

            if file[0]:
                pass
        else:
            reply = QMessageBox.information(None, 'Warning', "You cannot load a measurement files while data taking is in progress.", QMessageBox.Ok)

    def update_statistics(self):
            self.gui.bias_voltage_lcd.display(float(self.variables.default_values_dict["settings"].get("bias_voltage","0")))
            self.gui.current_pad_lcd.display(self.variables.default_values_dict["settings"].get("current_strip", None))
            self.gui.bad_pads_lcd.display(self.variables.default_values_dict["settings"].get("Bad_strips", None))


    # Update functions
    def error_update(self):
        last_errors = self.variables.event_loop_thread.error_log
        error_text = "\n".join(last_errors[-14:])

        if self.gui.event_log.text() != error_text: # Only update text if necessary
            self.gui.event_log.setText(error_text)

    def led_update(self):

        current_state = self.variables.default_values_dict["settings"]["current_led_state"]
        alignment = self.variables.default_values_dict["settings"]["Alignment"]
        running = self.variables.default_values_dict["settings"]["Measurement_running"]
        enviroment = self.variables.default_values_dict["settings"]["Environment_status"]

        if current_state != "running" and running:
            self.variables.default_values_dict["settings"]["current_led_state"] = "running"
            textbox_led.setStyleSheet("background : rgb(0,0,255); border-radius: 25px")
            textbox_led.setText("Measurement running")
            return


        elif current_state != "Alignment" and not alignment and not running:
            self.variables.default_values_dict["settings"]["current_led_state"] = "Alignment"
            textbox_led.setStyleSheet("background : rgb(255,0,0); border-radius: 25px")
            textbox_led.setText("Alignement missing")
            return


        elif current_state != "enviroment" and not enviroment and alignment and not running:
            self.variables.default_values_dict["settings"]["current_led_state"] = "enviroment"
            textbox_led.setStyleSheet("background : rgb(255,153,51); border-radius: 25px")
            textbox_led.setText("Environment status not ok")
            return

        if current_state != "ready" and alignment and not running and enviroment:
            self.variables.default_values_dict["settings"]["current_led_state"] = "ready"
            textbox_led.setStyleSheet("background : rgb(0,255,0); border-radius: 25px")
            textbox_led.setText("Ready to go")
            return

