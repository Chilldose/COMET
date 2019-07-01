import logging
from PyQt5.QtWidgets import *
from ..utilities import build_command

class SwitchingSystemQTC_window:

    def __init__(self, GUI_classes, layout):

        self.settings = GUI_classes
        self.layout = layout
        self.switching_control = GUI_classes.switching
        self.manual_switching = False
        self.variables = self.settings.default_values_dict["settings"]
        self.log = logging.getLogger(__name__)
        self.num_7072_cards = self.variables["Devices"]["Matrix"]["Cards"] # Todo: Potential error if you rename Matrix
        self.Keithley_7072 = self.settings.devices_dict["LVSwitching"]
        self.measurements = self.settings.default_values_dict["Switching"]["Switching_Schemes"].copy()

        # Settings tab
        switching_widget = QWidget()
        self.switching = self.settings.load_QtUi_file("Switching_70xB.ui", switching_widget)
        self.layout.addWidget(switching_widget)

        # Add the measurements to the comboBox
        self.switching.select_meas_comboBox.addItems(sorted(self.measurements.keys()))

        # Connect all buttons etc.
        self.switching.Override.clicked['bool'].connect(self.manual_override_action)
        self.switching.matrix_sel_spinBox.setMaximum(self.num_7072_cards)
        self.switching.check_switching_Button.clicked.connect(self.update_GUI_switching_scheme)

        #self.set_radio_buttons_checkable(False)
        self.switching.apply_button.clicked.connect(self.apply_switching_button_action)
        self.switching.check_switching_Button.clicked.connect(self.update_GUI_switching_scheme)
        self.switching.reset_button.clicked.connect(self.reset_switching)
        self.switching.matrix_sel_spinBox.valueChanged.connect(self.update_GUI_switching_scheme)


    def manual_override_action(self, bool):
        '''Manual switching enabling'''
        if bool:
            self.manual_switching = True
        else:
            self.manual_switching = False
        #self.switching.keithley_frame.setEnable(bool) # Done by the gui itself
        #self.switching.brandbox_frame.setEnable(bool)

    def reset_selected_GUI_checkboxes(self):
        """Resets all selected/eactivated GUI elements"""

        # Rreset Brandbox checkboxes
        try:
            self.switching.A1.setChecked(False)
            self.switching.A2.setChecked(False)
            self.switching.B1.setChecked(False)
            self.switching.B2.setChecked(False)
            self.switching.C1.setChecked(False)
            self.switching.C2.setChecked(False)
        except:
            pass

        # Reset all Matrices checkboxes
        for row in self.Keithley_7072["Rows"]:
            for column in self.Keithley_7072["Columns"]:
                getattr(self.switching, "{row}{column:02d}".format(row=row, column=int(column))).setChecked(False)

    def update_GUI_switching_scheme(self):
        '''This function updates the GUI switching scheme'''
        switching = self.switching_control.check_switching_action()
        self.reset_selected_GUI_checkboxes()
        for name, scheme in switching.items(): # loop over all switching systems
            if name == "Brand Box":
                # Now set all which need to be set
                for item in scheme:
                    if item:
                        getattr(self.switching, item).setChecked(True)

            if name == "Keithley 708B Switching":
                matrix = self.switching.matrix_sel_spinBox.value()
                for item in scheme:
                    if item:
                        # Todo: not the prettiest way to do it, may be cool to clean it up
                        if item[0] == str(matrix): # Checks for the selected matrix
                            getattr(self.switching, "{relay}".format(relay=item[1:])).setChecked(True)

    def reset_switching(self):
        for device in self.settings.devices_dict.values():
            if "Switching relay" in device["Device_type"]:
                self.switching_control.reset_switching(device) # Opens all closed switches
                self.update_GUI_switching_scheme()

    def apply_switching_button_action(self):
        if not self.manual_switching:
            selected_meas = self.switching.select_meas_comboBox.currentText()
            self.switching_control.switch_to_measurement(selected_meas)

        else:
            self.apply_manual_switching()

        self.update_GUI_switching_scheme()

    def apply_manual_switching(self):
        """This function switches to the current selected GUI switching settings"""
        # First get all pressed check boxes for the switching

        to_switch = {}
        # Brandbox
        to_switch.update({"HVSwitching": []})
        # Now get all nodes which need to be set
        for relay in ["A1", "A2", "B1", "B2", "C1", "C2"]: # This is GUI specific!!!!
            if getattr(self.switching, relay).isChecked(): # find out if the button is checked
                to_switch["HVSwitching"].append(relay)


        # Switching matrix
        to_switch.update({"LVSwitching": []})
        matrix = self.switching.matrix_sel_spinBox.value()
        # Now get all nodes which need to be set
        # Reset all Matrices checkboxes
        for row in self.Keithley_7072["Rows"]:
            for column in self.Keithley_7072["Columns"]:
                if getattr(self.switching, "{row}{column:02d}".format(row=row, column=int(column))).isChecked():
                    to_switch["LVSwitching"].append("{matrix}{row}{column:02d}".format(matrix=matrix, row=row, column=int(column)))


        # No apply the switching
        self.switching_control.apply_specific_switching(to_switch)
