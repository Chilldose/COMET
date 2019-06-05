import logging
from PyQt5.QtWidgets import QWidget

class Device_communication_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)

        # Device communication widget
        self.ComWidget = QWidget()
        self.gui = self.variables.load_QtUi_file("Device_communication.ui",  self.ComWidget)
        self.layout.addWidget(self.ComWidget)