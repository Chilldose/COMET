import logging

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *

from .. import utilities

l = logging.getLogger(__name__)

hf = utilities.help_functions()


class Resources_window:
    """This window handles the resources tab"""

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.list_of_instruments = []
        self.possible_states = [("INIT", "QFrame { background :rgb(0, 0, 255) }"),
                                ("CONFIGURED", "QFrame { background :rgb(0, 255, 0) }"),
                                ("ERROR", "QFrame { background :rgb(255, 0, 0) }")]

        self.device_widget = QtWidgets.QFrame()
        self.device_widget.setGeometry(QtCore.QRect(10, 10, 1000, 1800))
        self.device_widget.setAutoFillBackground(False)
        # self.device_widget.setStyleSheet("QFrame { background: rgb(234, 247, 255)}")
        self.device_widget.setFrameShape(QtWidgets.QFrame.Box)
        self.device_widget.setFrameShadow(QtWidgets.QFrame.Raised)
        self.device_widget.setObjectName("device_widget")
        self.gridLayout = QtWidgets.QGridLayout(self.device_widget)
        self.gridLayout.setObjectName("gridLayout")

        # Settings tab
        # resources_widget = QWidget()
        # self.resources = Ui_device_info() # Starts the init of the ui file
        # self.resources_widget.setupUi(resources_widget)
        # self.layout.addWidget(resources_widget)

        # Begin finding all resources and render them
        self.get_all_instruments()
        self.begin_rendering_of_instruments()

    def device_state(self, device, state):  # Not used yet
        """This function changes the state of a device"""
        for states in self.possible_states:
            if state.upper() == states[0]:  # makes a list out of the states
                device.device_state_label.setText(states[0])
                device.device_state_label.setStyleSheet(states[1])

    def get_all_instruments(self):
        """Gets all instruments which are listed"""

        #_translate = QtCore.QCoreApplication.translate
        QtCore.QMetaObject.connectSlotsByName(self.layout)
        # Get list of Instruments
        already_in = []
        for device, value in self.variables.devices_dict.items():
            if value not in already_in:  # so that a multifunctional device is not rendered twice
                already_in.append(value)
                device_dict = self.variables.devices_dict[device]
                resources_widget = QWidget()

                # Standard test labels
                # instrument = Ui_device_info()  # Starts the init of the ui file
                # instrument.setupUi(resources_widget)
                instrument = self.variables.load_QtUi_file("./modules/QT_Designer_UI/Device_connection_info.ui",
                                                           resources_widget)
                instrument.device_name_label.setText(device_dict["Device_name"])
                instrument.device_IDN_label.setText(device_dict["Device_IDN"])

                if type(device_dict.get("Device_type", "MissingNo")) == list:
                    device_type = ""
                    for items in device_dict["Device_type"]:
                        device_type += str(items) + ", "
                else:
                    device_type = str(device_dict.get("Device_type", "MissingNo"))
                instrument.device_assigned_to_label.setText(device_type)

                # To be checked values
                if "Visa_Resource" in device_dict:
                    instrument.device_connected_at_label.setText(str(device_dict["Visa_Resource"]))
                    instrument.device_connected_label.setText("CONNECTED")
                    # instrument.device_connected_checkbox.setChecked(True) # legacy
                    instrument.device_connected_label.setStyleSheet("QFrame { background :rgb(0, 255, 0) }")
                else:
                    instrument.device_connected_at_label.setText("None")
                    instrument.device_connected_label.setText("NOT CONNECTED")
                    # self.device_state(instrument, "ERROR")
                    # instrument.device_state_label.setText("ERROR")
                    # instrument.device_connected_checkbox.setChecked(False) #legacy
                    instrument.device_connected_label.setStyleSheet("QFrame { background :rgb(255, 0, 0) }")
                    # instrument.device_state_label.setStyleSheet("QFrame { background :rgb(255, 0, 0) }")

                self.list_of_instruments.append(resources_widget)


            else:
                pass

    def begin_rendering_of_instruments(self):
        """Renders all instruments"""

        # First define size of the grid layout, so nothing gets stretched

        #num_inst = len(self.list_of_instruments)
        row = 0  # Current render row
        line = 0  # Current render line

        for instrument in self.list_of_instruments:
            self.gridLayout.addWidget(instrument, line, row, 1, 1)
            row += 1
            if row >= 3:
                row = 0
                line += 1

        self.layout.addWidget(self.device_widget)
