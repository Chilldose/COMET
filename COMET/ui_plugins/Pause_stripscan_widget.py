from PyQt5.QtWidgets import QWidget, QVBoxLayout, QDialog
from ..measurement_plugins.forge_tools import tools
from time import sleep


class pause_stripscan_widget(QDialog):

    def __init__(self, gui, parent=None):

        super(pause_stripscan_widget, self).__init__(None)
        self.gui = gui
        self.tools = tools
        self.old_bias_voltage = None
        self.stop = False

        layout = QVBoxLayout(self)

        # Dynamic waiting time detection tab
        self.Pause_Widget_object = QWidget()
        self.PauseWidget = self.gui.variables.load_QtUi_file("Pause_widget.ui", self.Pause_Widget_object)
        layout.addWidget(self.Pause_Widget_object)

        self.PauseWidget.continue_pushButton.clicked.connect(self.continue_action)
        self.PauseWidget.ramp_down_pushButton.clicked.connect(self.ramp_down_action)
        self.PauseWidget.ramp_previous_pushButton.clicked.connect(self.ramp_previous)
        self.PauseWidget.do_pause_pushButton.clicked.connect(self.do_pause_action)
        self.PauseWidget.ramp_down_pushButton.setEnabled(False)
        self.PauseWidget.ramp_previous_pushButton.setEnabled(False)



    def do_pause_action(self):
        """Actually pauses the stripcan routine"""
        from PyQt5.QtWidgets import QApplication
        self.PauseWidget.status_label.setText("Try pausing Stripcan...")
        self.gui.variables.default_values_dict["settings"]["pause_stripscan"] = True
        counter = 0
        #self.PauseWidget.do_pause_pushButton.setText("Stop pausing")
        self.PauseWidget.do_pause_pushButton.setEnabled(False)
        while not self.gui.variables.default_values_dict["settings"].get("stripscan_is_paused", False) or counter >= 300:  # Wait until the stripscan is paused
            counter += 1
            sleep(0.1)
            QApplication.processEvents()
            if self.stop: return
        if counter >= 300:
            self.PauseWidget.status_label.setText("Stripscan script could NOT paused, no answer from the stripscan...")

        self.PauseWidget.status_label.setText("Stripscan script successfully paused...")
        self.PauseWidget.ramp_down_pushButton.setEnabled(True)
        self.PauseWidget.ramp_previous_pushButton.setEnabled(True)

    def ramp_down_action(self):
        """Ramps the voltage down"""
        self.PauseWidget.status_label.setText("Ramping to 0 volt...")
        values = self.gui.variables.default_values_dict["settings"]["stripscan_device"] #(self.bias_SMU, "set_voltage", self.current_voltage, self.voltage_steps)
        self.tools.do_ramp_value(resource=values[0], order=values[1],
                                 voltage_Start=values[2], voltage_End=0.0,
                                 step=values[3], wait_time=0.5, compliance=0.0001,
                                 set_value=self.changeBiasVolt)

    def changeBiasVolt(self, volt):
        """Changes the bias voltage"""
        self.gui.variables.default_values_dict["settings"]["bias_voltage"] = volt

    def ramp_previous(self):
        """Ramps to previous voltage"""
        self.PauseWidget.status_label.setText("Ramping to previous bias voltage...")
        values = self.gui.variables.default_values_dict["settings"][
            "stripscan_device"]  # (self.bias_SMU, "set_voltage", self.current_voltage, self.voltage_steps)
        self.tools.do_ramp_value(resource=values[0], order=values[1],
                                 voltage_Start=self.gui.variables.default_values_dict["settings"]["bias_voltage"], voltage_End=values[2],
                                 step=values[3], wait_time=0.5, compliance=0.0001,
                                 set_value=self.changeBiasVolt)

    def continue_action(self):
        """Resumes the program"""
        self.PauseWidget.status_label.setText("Try resuming Stripcan...")
        self.PauseWidget.ramp_down_pushButton.setEnabled(False)
        self.PauseWidget.ramp_previous_pushButton.setEnabled(False)
        self.gui.variables.default_values_dict["settings"]["pause_stripscan"] = False
        while self.gui.variables.default_values_dict["settings"].get("stripscan_is_paused", False):  # Wait until the stripscan is paused
            sleep(0.1)
        self.gui.variables.default_values_dict["settings"]["stripscan_is_paused"] = False
        self.stop = True
        self.close()