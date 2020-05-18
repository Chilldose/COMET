import logging
from PyQt5.QtWidgets import QWidget
from ..utilities import build_command

class DeviceCommunication_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)

        self.currentDevice = None
        self.session_connections = {}

        # Device communication widget
        self.ComWidget = QWidget()
        self.gui = self.variables.load_QtUi_file("DeviceCommunication.ui",  self.ComWidget)
        self.layout.addWidget(self.ComWidget)


        # Add all devices to the dropdown menu
        self.gui.device_comboBox.addItems(self.variables.devices_dict.keys())


        # Connect all gui elements
        self.gui.device_comboBox.activated[str].connect(self.change_device_action)
        self.gui.query_Button.clicked.connect(self.query_action)
        self.gui.read_Button.clicked.connect(self.read_action)
        self.gui.send_Button.clicked.connect(self.write_action)
        self.gui.connect_Button.clicked.connect(self.connect_to)
        self.gui.list_all_Button.clicked.connect(self.list_all_action)
        #self.gui.disconnect_Button.clicked.connect(self.write_action)

        try:
            self.currentDevice = self.variables.devices_dict[self.gui.device_comboBox.currentText()]
            self.get_device_commands()
        except:
            self.log.warning("It seems no devices are connected...")

    def list_all_action(self):
        """Lists all devices"""
        self.variables.vcw.search_for_instruments()
        self.gui.all_devices_comboBox.clear()
        self.gui.all_devices_comboBox.addItems(self.variables.vcw.resource_names)

    def connect_to(self):
        """Connects to the currently selected item"""
        device = self.gui.all_devices_comboBox.currentText()
        try:
            new_device = self.variables.vcw.rm.open_resource(device)
            if new_device:
                self.session_connections[device] = {"Visa_Resource": new_device, "Device_name": device}
                self.gui.device_comboBox.addItem(device)
                self.currentDevice = new_device
                self.gui.device_comboBox.setCurrentIndex(-1)
        except:
            self.log.error("Could not connect to device {}, this device may be already used by the framework or is not"
                           " correctly configured. This happens especially with ASRL device types".format(device))

    def change_device_action(self, device):
        """What happens when a new device is selected in the drop down menu"""
        if device in self.variables.devices_dict:
            self.currentDevice = self.variables.devices_dict[device]
            self.get_device_commands()
        else:
            self.currentDevice = self.session_connections[device]
            self.gui.commands_comboBox.clear()

    def write_action(self):
        self.gui.response_label.setText("")
        message = self.get_message()
        """What to do when the write button is pressed"""
        self.variables.vcw.write(self.currentDevice, message)
        return None

    def query_action(self):
        """What to do when the query button is pressed"""
        #self.gui.response_label.setText("")
        message = self.get_message()
        count = int(self.gui.spinBox.value())
        total_message = ""
        if not count:
            count = 1
        try:
            for i in range(count):
                resp = self.variables.vcw.query(self.currentDevice, message, reconnect=False)
                currenttext = self.gui.response_label.text()
                self.gui.response_label.setText(currenttext + resp)
                total_message += "\n" + resp
            return total_message
        except:
            return None

    def read_action(self):
        """What to do when the read button is pressed"""
        #self.gui.response_label.setText("")
        try:
            resp = self.variables.vcw.read(self.currentDevice)
            currenttext = self.gui.response_label.text()
            self.gui.response_label.setText(currenttext + "\n" + resp)
            return resp
        except:
            return None

    def get_message(self):
        """Gets the message to write"""
        lineedit = self.gui.message_lineEdit.text()
        if lineedit:
            return lineedit
        else:
            command = build_command(self.currentDevice, (self.gui.commands_comboBox.currentText(),
                                                         self.gui.value_lineEdit.text()))
            return command

    def get_device_commands(self):
        """Gerts the device commands for the selected device"""
        commands = self.currentDevice.keys()
        self.gui.commands_comboBox.clear()
        for comm in sorted(commands):
            if "set_" in comm or "get_" in comm:
                self.gui.commands_comboBox.addItem(comm)

