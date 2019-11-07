import logging
from PyQt5.QtWidgets import *
from functools import partial
import yaml
import os


class MeasurementConfig_window():

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        # Load settings if some are defined in the parent directory
        self.settings = self.variables.framework_variables['Configs']['config'].get('MeasurementSettings', {})
        self.ui_groups = {}
        self.settings_boxes = {}
        self.columns = 4 # Number of columns per group
        if not self.settings:
            self.log.error("Measurement settings tab was loaded but no options have been given. Please add the settings to your project")


        # Settings Main tab
        self.SettingsMainWidget = QWidget()
        self.SettingsGui = self.variables.load_QtUi_file("SettingsTab.ui",  self.SettingsMainWidget)
        self.layout.addWidget(self.SettingsMainWidget)

        if not self.settings:
            self.log.warning("Not settings found to render, please select/load one...")
        self.construct_ui()

        self.SettingsGui.Unlock_pushButton.clicked[bool].connect(self.SettingsGui.scrollArea.setEnabled)

    def load_settings_from_file(self, path):
        """Loads settings from a yaml file and configs the GUI with it. This deletes an old GUI"""
        if os.path.exists(os.path.normpath(path)):
            try:
                self.delete_old_settings_layout()
                with open(os.path.normpath(path)) as fp:
                    self.settings = yaml.safe_load(fp)
                self.construct_ui()
            except Exception as err:
                self.log.error("An error happened while loading yaml settings with error: {}".format(err))
                return

    def delete_old_settings_layout(self):
        """Deletes the layout childs of the main layout"""
        for i in reversed(range(self.SettingsGui.MainSettings_Layout.count())):
            self.SettingsGui.MainSettings_Layout.itemAt(i).widget().setParent(None)

    def generate_job_for_group(self, group):
        """Generates a Measurement job dict, out of the passed group. returns empty dict if meas is disabled"""
        if not group in self.settings:
            self.log.warning("No settings group {} is present.".format(group))
            return {}

        job = {}
        for Name, value in self.settings[group]["Measurements"].items():
            if self.settings[group]["Do"] and value["Do"]:
                job[Name] = {}
                for set, val in value.items():
                    if set != "Do":
                        job[Name][set] = val[-1] # Only the last value from all is the current set value in the spin box

        # Add the other settings
        if job:
            for ent, value in self.settings[group].items():
                if ent not in ["Do", "Measurements"]:
                    job[ent] = value

            return {group: job}
        else:
            return {}



    def construct_ui(self):
        """Constructs the UI"""

        # Run through all options
        if self.settings:
            for groupName, group in self.settings.items():
                if isinstance(group, dict):
                    if "Measurements" in group:
                        # Load a group widget
                        SettingsWidget = QWidget()
                        gui = self.variables.load_QtUi_file("SettingsFrame.ui", SettingsWidget)
                        self.SettingsGui.MainSettings_Layout.addWidget(SettingsWidget)

                        try:
                            self.config_group(gui, groupName, group)
                        except Exception as err:
                            self.log.error("An error happend during settings ui construction, this usually happens if you "
                                           "have passed wrong options for the measruements. Error: {}".format(err))

                    else:
                        self.log.error("Wrong typed settings options. Each group needs to have a 'Measurements' entry.")

    def config_group(self, ui, Name, measurements):
        """Configs the group and loads the individual measurements"""
        ui.Group_label.setText(str(Name))
        ui.EnableGroup_pushButton.setChecked(measurements["Do"])
        #ui.settingsGroup_Layout.setEnabled(measurements["Do"])


        self.ui_groups[Name] = {"Group_Ui": ui}
        self.settings_boxes[Name] = {}

        row = 0  # Current render row
        line = 0  # Current render line

        for measName, opt in measurements["Measurements"].items():
            MeasWidget = QWidget()
            conf_ui = self.variables.load_QtUi_file("SettingsConfig_widget.ui", MeasWidget)
            ui.settingsGroup_Layout.addWidget(MeasWidget, line, row, 1, 1)

            # Add this information to the dict
            self.ui_groups[Name][measName] = conf_ui

            # Adjust all names
            conf_ui.measurement_label.setText(str(measName))
            conf_ui.enable_checkBox.setChecked(opt["Do"])

            options_col = 0
            for option, values in opt.items():
                if option != "Do":
                    label = QLabel()
                    box = QSpinBox()
                    #sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
                    conf_ui.MeasSettings_layout.addWidget(label, 0, options_col)
                    conf_ui.MeasSettings_layout.addWidget(box, 1, options_col)
                    label.setText(str(option))
                    #label.setSizePolicy(sizePolicy)
                    box.setRange(*values[0:2])
                    box.setSingleStep(values[2])
                    box.setValue(values[3])
                    options_col += 1

                    self.settings_boxes[Name] = {}

                    # Add the button and enable
                    conf_ui.frame.setEnabled(measurements["Do"])
                    ui.EnableGroup_pushButton.clicked[bool].connect(conf_ui.frame.setEnabled)
                    ui.EnableGroup_pushButton.clicked[bool].connect(partial(self.change_check, measurements))
                    conf_ui.enable_checkBox.clicked[bool].connect(partial(self.change_check, measurements["Measurements"][measName]))
                    box.valueChanged.connect(partial(self.change_value, box, measurements["Measurements"][measName], option))

            # Adjust grid position
            row += 1

            if row >= self.columns:
                row = 0
                line += 1

    def change_value(self, box, measurement_dict, entry):
        """Changes the value in the dict of the settings"""
        measurement_dict[entry][3] = box.value()

    def change_check(self, measurement_dict, value):
        """Changes the checkbox value"""
        measurement_dict["Do"] = value
