import logging

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *



class Resources_window:
    """This window handles the resources tab"""

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)


        self.list_of_instruments = []
        self.possible_states = {"CONNECTED": "QFrame { background :rgb(232, 239, 26) }",
                                "CONFIGURED": "QFrame { background :rgb(36, 216, 93) }",
                                "UNCONFIGURED": "QFrame { background :rgb(36, 216, 93) }",
                                "NOT CONNECTED": "QFrame { background :rgb(214, 40, 49) }",
                                "None": "QFrame {}"}

        self.device_widget = QtWidgets.QFrame()
        self.device_widget.setAutoFillBackground(False)
        self.device_widget.setFrameShape(QtWidgets.QFrame.Box)
        self.device_widget.setFrameShadow(QtWidgets.QFrame.Raised)
        self.device_widget.setObjectName("device_widget")
        self.gridLayout = QtWidgets.QGridLayout(self.device_widget)
        self.gridLayout.setObjectName("gridLayout")

        # Begin finding all resources and render them
        self.get_all_instruments()
        self.begin_rendering_of_instruments()

    def device_state(self, device, GUI, state):
        """This function changes the state of a device"""
        GUI.device_connected_label.setStyleSheet(self.possible_states.get(state, "None"))
        GUI.device_connected_at_label.setText(str(device["Visa_Resource"]))
        GUI.device_connected_label.setText(state)



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

                instrument = self.variables.load_QtUi_file("Device_connection_info.ui",
                                                           resources_widget)
                instrument.device_name_label.setText(device_dict["Device_name"])
                instrument.device_IDN_label.setText(device_dict.get("Device_IDN", "None"))

                if type(device_dict.get("Device_type", "MissingNo")) == list:
                    device_type = ""
                    for items in device_dict["Device_type"]:
                        device_type += str(items) + ", "
                else:
                    device_type = str(device_dict.get("Device_type", "MissingNo"))
                instrument.device_assigned_to_label.setText(device_type)

                # Define device state
                state = device_dict.get("State", None)
                self.device_state(device_dict, instrument, state)

                # if device_dict.get("Visa_Resource", None):
                #     self.log.info("Resource found for device: {}".format(device_dict["Device_name"]))
                #     instrument.device_connected_at_label.setText(str(device_dict["Visa_Resource"]))
                #     instrument.device_connected_label.setText("CONNECTED")
                #     self.device_state(instrument.device_connected_label, "CONFIGURED")
                #
                # else:
                #     self.log.info("Resource NOT found for device: {}".format(device_dict["Device_name"]))
                #     instrument.device_connected_at_label.setText("None")
                #     instrument.device_connected_label.setText("NOT CONNECTED")
                #     self.device_state(instrument.device_connected_label, "ERROR")

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
