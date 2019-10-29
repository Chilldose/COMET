import logging

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from functools import partial




class Resources_window:
    """This window handles the resources tab"""

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)


        self.list_of_instruments = {}
        self.list_of_widgets = {}
        self.possible_states = {"CONNECTED": "QFrame { background :rgb(255, 215, 0) }",
                                "CONFIGURED": "QFrame { background :rgb(55, 205, 0) }",
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

        # Add the device update function
        self.variables.add_update_function(self.update_device_states)

    def reconnect_action(self, device):
        """Reconnects to the device"""
        if self.variables.devices_dict[device].get("Visa_resource"):
            self.variables.vcw.reconnect_to_device(self.variables.devices_dict[device])
        else:
            self.log.error("In order to reconnect to a device, a previous connection has to be present...")

    def test_connection_action(self, device):
        """Test the connection to a device by sending the IDN query"""
        if self.variables.devices_dict[device].get("Visa_resource"):
            success = self.variables.vcw.verify_ID(self.variables.devices_dict[device]["Visa_resource"], self.variables.devices_dict[device].get("device_IDN_query","*IDN?"))
            if success == self.variables.devices_dict[device]["Device_IDN"]:
                reply = QMessageBox.question(None, 'INFO',
                                             "The device is responding and seems fully functional...",
                                             QMessageBox.Ok)
            else:
                self.log.error("Device IDN request did not match. Answer from device {} was not {}".format(success,
                                                                                                           self.variables.devices_dict[device]["Device_IDN"]))
        else:
            self.log.error("Can not query device, because not device is connected...")

    def configure_device_action(self, device):
        """Configs the the device"""
        if self.variables.devices_dict[device].get("Visa_resource"):
            self.init_device(self.variables.devices_dict[device])
        else:
            self.log.error("Can not config device, because not device is connected...")

    def reset_device_action(self, device):
        """Sends the device reset commands to the device"""
        if self.variables.devices_dict[device].get("Visa_resource"):
            self.reset_device(self.variables.devices_dict[device])
        else:
            self.log.error("Can not reset device, because not device is connected...")

    def device_state(self, device, GUI):
        """This function changes the state of a device"""
        state = device.get("State", None)
        GUI.device_connected_label.setStyleSheet(self.possible_states.get(state, "None"))
        GUI.device_connected_at_label.setText(str(device["Visa_Resource"]))
        GUI.device_connected_label.setText(state)

    def update_device_states(self):
        """Updates the device state flag"""
        for device, widget in self.list_of_instruments.items():
            if not self.variables.devices_dict[device].get("State", "None") == widget.device_connected_label.text():
                self.device_state(self.variables.devices_dict[device], widget)

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
                self.device_state(device_dict, instrument)

                self.list_of_instruments[device] = instrument
                self.list_of_widgets[device] = resources_widget

                # Connect the device widget and buttons to the actions
                instrument.Test_pushButton.clicked.connect(partial(self.test_connection_action, device))
                instrument.Configure_pushButton.clicked.connect(partial(self.configure_device_action, device))
                instrument.Reconnect_pushButton.clicked.connect(partial(self.reconnect_action, device))
                instrument.Reset_pushButton.clicked.connect(partial(self.reset_device_action, device))

            else:
                pass

    def begin_rendering_of_instruments(self):
        """Renders all instruments"""

        # First define size of the grid layout, so nothing gets stretched

        #num_inst = len(self.list_of_instruments)
        row = 0  # Current render row
        line = 0  # Current render line

        for instrument in self.list_of_widgets.values():
            self.gridLayout.addWidget(instrument, line, row, 1, 1)
            row += 1
            if row >= 3:
                row = 0
                line += 1

        self.layout.addWidget(self.device_widget)


    def reset_device(self, device_dict):
        """Sends the reset device commands"""
        if device_dict.get("Visa_Resource", None):  # Looks if a Visa resource is assigned to the device.
            self.log.info("Configuring instrument: {!s}".format(device_dict.get("Device_name", "NoName")))

            # Sends the resets commands to the device
            if "reset_device" in device_dict:
                self.variables.vcw.write(device_dict, list(device_dict["reset_device"]))
            else:
                self.variables.vcw.list_write(device_dict, ["*rst", "*cls"], delay=0.1)

            device_dict["State"] = "UNCONFIGURED"


    def init_device(self, device_dict):
            '''This function makes the necessary configuration for a device'''

            if device_dict.get("Visa_Resource", None): # Looks if a Visa resource is assigned to the device.
                self.log.info("Configuring instrument: {!s}".format(device_dict.get("Device_name", "NoName")))

                # Sends the resets commands to the device
                if "reset_device" in device_dict:
                    self.variables.vcw.write(device_dict, list(device_dict["reset_device"]))
                else:
                    self.variables.vcw.list_write(device_dict, ["*rst", "*cls"], delay=0.1)

                device_dict["State"] = "UNCONFIGURED"

                # Begin sending commands from the reset list
                if "reset" in device_dict:
                    for comm in device_dict["reset"]:
                        command, values = list(comm.items())[0]
                        command_list = self.variables.build_init_command(device_dict, command, values)
                        self.variables.vcw.list_write(device_dict, command_list, delay=0.05)

                    # Only if reset commands are prevalent, otherwise its not configured
                    device_dict["State"] = "CONFIGURED"


