from PyQt5.QtWidgets import QWidget, QVBoxLayout, QDialog
from ..measurement_plugins.forge_tools import tools


class pause_stripscan_widget(QDialog):

    def __init__(self, gui, parent=None):

        super(pause_stripscan_widget, self).__init__(None)
        self.gui = gui
        self.tools = tools
        self.old_bias_voltage = None

        layout = QVBoxLayout(self)

        # Dynamic waiting time detection tab
        self.Pause_Widget_object = QWidget()
        self.PauseWidget = self.gui.variables.load_QtUi_file("Pause_widget.ui", self.Pause_Widget_object)

        layout.addWidget(self.Pause_Widget_object)

        self.PauseWidget.continue_pushButton.clicked.connect(self.continue_action)

    def ramp_down_action(self):
        """Ramps the voltage down"""
        self.tools.do_ramp_value()

    def ramp_previous(self):
        """Ramps to previous voltage"""
        self.tools.do_ramp_value()

    def continue_action(self):
        """Resumes the program"""
        self.close()