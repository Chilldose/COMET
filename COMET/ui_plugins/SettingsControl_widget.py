import logging
from PyQt5.QtWidgets import QFileDialog, QWidget
from PyQt5 import QtCore
import yaml
import os, sys
from ..utilities import write_init_file


class SettingsControl_widget(object):
    def __init__(self, gui):
        """Configures the settings widget"""
        self.Setlog = logging.getLogger(__name__)
        self.autodirgen = True  # If the auto dir generator is on or off

        # Project widget
        if not "Settings" in gui.child_layouts:
            self.Tablog.error("No layout found to render settings widget. Skipping...")
            return
        settings_Qwidget = QWidget()
        self.settings_layout = gui.child_layouts["Settings"]
        self.settings_widget = self.variables.load_QtUi_file(
            "Project_selector.ui", settings_Qwidget
        )
        self.settings_layout.addWidget(settings_Qwidget)

        try:
            super(SettingsControl_widget, self).__init__(gui)
        except:
            super(SettingsControl_widget, self).__init__()

        self.Settings_gui = self.settings_widget

        # TODO: The init needs to be cleaned up a bit, currently not very pythonic structured
        # Adds all projects to the combo box
        for projects in self.variables.additional_files.get("Pad_files", {}):
            self.Settings_gui.proj_comboBox.addItem(str(projects))

        if "Current_project" in self.variables.default_values_dict["settings"]:
            self.variables.default_values_dict["settings"]["Current_project"] = list(
                self.variables.additional_files["Pad_files"].keys()
            )[
                0
            ]  # That one project is definetly choosen
        else:
            self.variables.default_values_dict["settings"].update(
                {"Current_project": self.Settings_gui.proj_comboBox.currentText()}
            )

        current_project = self.variables.default_values_dict["settings"].get(
            "Current_project", None
        )
        self.Settings_gui.sensor_comboBox.addItems(
            self.variables.additional_files["Pad_files"][current_project]
        )  # Adds all items to the combo box

        if "Current_sensor" in self.variables.default_values_dict["settings"]:
            try:
                self.variables.default_values_dict["settings"]["Current_sensor"] = list(
                    self.variables.additional_files["Pad_files"][current_project]
                )[
                    0
                ]  # That one project is definetly choosen
            except:
                self.variables.default_values_dict["settings"][
                    "Current_sensor"
                ] = "None"
        else:
            if current_project and self.variables.additional_files["Pad_files"]:
                self.variables.default_values_dict["settings"].update(
                    {
                        "Current_sensor": list(
                            self.variables.additional_files["Pad_files"][
                                current_project
                            ]
                        )[0]
                    }
                )
            else:
                self.variables.default_values_dict["settings"].update(
                    {"Current_sensor": "None"}
                )

        if "Current_filename" in self.variables.default_values_dict["settings"]:
            self.Settings_gui.filename.setText(
                str(self.variables.default_values_dict["settings"]["Current_filename"])
            )
        else:
            self.variables.default_values_dict["settings"].update(
                {"Current_filename": ""}
            )
            self.Settings_gui.filename.setText(
                str(self.variables.default_values_dict["settings"]["Current_filename"])
            )

        for projects in self.variables.default_values_dict["settings"].get(
            "Operator", ["None",]
        ):
            self.Settings_gui.operator_comboBox.addItem(
                str(projects)
            )  # Adds all items to the combo box

        if "Current_operator" in self.variables.default_values_dict["settings"]:
            self.variables.default_values_dict["settings"][
                "Current_operator"
            ] = self.variables.default_values_dict["settings"]["Operator"][
                0
            ]  # That one project is definetly choosen
        else:
            self.variables.default_values_dict["settings"].update(
                {
                    "Current_operator": self.variables.default_values_dict[
                        "settings"
                    ].get("Operator", ["None",])[0]
                }
            )

        if "Current_directory" in self.variables.default_values_dict["settings"]:
            self.Settings_gui.output_dir_edit.setText(
                str(self.variables.default_values_dict["settings"]["Current_directory"])
            )
        else:
            self.variables.default_values_dict["settings"].update(
                {"Current_directory": str(os.getcwd())}
            )
            self.Settings_gui.output_dir_edit.setText(
                str(self.variables.default_values_dict["settings"]["Current_directory"])
            )

        self.variables.default_values_dict["settings"][
            "Base_directory"
        ] = self.variables.default_values_dict["settings"]["Current_directory"]

        # Load settings presets
        self.load_setting_presets()

        self.Settings_gui.load_settings_button.clicked.connect(
            self.load_setting_presets
        )
        self.Settings_gui.save_settings_button.clicked.connect(
            self.save_measurement_settings_file
        )
        self.Settings_gui.save_to_button.clicked.connect(self.dir_selector_action)
        self.Settings_gui.operator_comboBox.activated[str].connect(
            self.operator_selector_action
        )
        self.Settings_gui.sensor_comboBox.activated[str].connect(
            self.sensor_selector_action
        )
        self.Settings_gui.proj_comboBox.activated[str].connect(
            self.project_selector_action
        )
        self.Settings_gui.filename.textChanged[str].connect(self.change_name)
        self.Settings_gui.filename.textChanged[str].connect(self.dir_autopath_generator)
        self.Settings_gui.output_dir_edit.textChanged[str].connect(
            self.dir_change_action
        )
        self.Settings_gui.select_settings_comboBox.currentTextChanged.connect(
            self.settings_select_change_action
        )

    # Order functions
    def change_name(self, filename):
        self.variables.default_values_dict["settings"]["Current_filename"] = str(
            filename
        )

    def project_selector_action(self, project):
        self.load_valid_sensors_for_project(str(project))
        self.variables.default_values_dict["settings"]["Current_project"] = str(project)

    def sensor_selector_action(self, sensor):
        self.variables.default_values_dict["settings"]["Current_sensor"] = str(sensor)

    def operator_selector_action(self, operator):
        self.variables.default_values_dict["settings"]["Current_operator"] = str(
            operator
        )

    def dir_selector_action(self):
        self.autodirgen = True
        fileDialog = QFileDialog()
        directory = fileDialog.getExistingDirectory()
        self.Settings_gui.output_dir_edit.setText(directory)
        self.variables.default_values_dict["settings"]["Current_directory"] = str(
            directory
        )
        self.variables.default_values_dict["settings"]["Base_directory"] = str(
            directory
        )

    def dir_change_action(self, dire):
        """If the user changes the directory by hand"""
        self.variables.default_values_dict["settings"]["Current_directory"] = dire

    def dir_autopath_generator(self, filename):
        """Generates a directory structure out of the file name"""
        if self.autodirgen:
            seperators = ["_", "-", ":"]
            for sep in seperators:
                splitted = filename.split(sep)
                if len(splitted) > 1:
                    new_dir = os.path.join(
                        self.variables.default_values_dict["settings"][
                            "Base_directory"
                        ],
                        *splitted
                    )
                    self.Settings_gui.output_dir_edit.setText(new_dir)
                    break

    def load_measurement_settings_file(self):
        """ This function loads a measurement settings file
        DEPRICATED: YOU CAN ONLY LOAD FROM THE DEDICATED FOLDER"""

        # First update the settings that the state machine is up to date
        self.variables.ui_plugins["Settings_window"].load_new_settings()

        fileDialog = QFileDialog()
        file = fileDialog.getOpenFileName()

        if file[0]:
            with open(str(file[0]), "r") as fp:
                dict = yaml.safe_load(fp)

            self.Setlog.info("Loaded new measurement settings file: {}".format(file[0]))
            self.variables.default_values_dict["settings"].update(dict)
            self.variables.ui_plugins["Settings_window"].configure_settings()

    def save_measurement_settings_file(self):
        """ This function saves a measuerment settings file"""
        fileDialog = QFileDialog()
        file = fileDialog.getSaveFileName()

        if file[0]:
            with open(os.path.normpath(file[0].split(".")[0]) + ".yml", "w+") as fp:
                self.variables.framework_variables["Configs"]["config"][
                    "MeasurementSettings"
                ]["Settings_name"] = os.path.basename(file[0])
                yaml.safe_dump(
                    self.variables.framework_variables["Configs"]["config"][
                        "MeasurementSettings"
                    ],
                    fp,
                )

            self.variables.framework_variables["Configs"]["additional_files"][
                "Measurement_Settings"
            ][os.path.basename(file[0])] = self.variables.framework_variables[
                "Configs"
            ][
                "config"
            ][
                "MeasurementSettings"
            ]
            self.variables.framework_variables["Configs"]["additional_files"][
                "Measurement_Settings"
            ][os.path.basename(file[0])]["raw"] = yaml.dump(
                self.variables.framework_variables["Configs"]["config"][
                    "MeasurementSettings"
                ]
            )
            self.Settings_gui.select_settings_comboBox.addItem(
                os.path.basename(file[0])
            )

            index = self.Settings_gui.select_settings_comboBox.findText(
                os.path.basename(file[0]), QtCore.Qt.MatchFixedString
            )
            if index >= 0:
                self.Settings_gui.select_settings_comboBox.setCurrentIndex(index)

            self.Setlog.info(
                "Settings file successfully written to: {}".format(file[0])
            )

    def load_valid_sensors_for_project(self, project_name):
        """This function loads the valid sensors for each project"""
        # Warning sensor_comboBox must be accessable for this function to work
        self.Settings_gui.sensor_comboBox.clear()
        try:
            # self.variables.default_values_dict["settings"]["Sensor_types"][project_name]
            self.Settings_gui.sensor_comboBox.addItems(
                list(self.variables.additional_files["Pad_files"][project_name].keys())
            )  # Adds all items to the combo box
            # Select the first element to be right, if possible
            self.variables.default_values_dict["settings"][
                "Current_sensor"
            ] = self.Settings_gui.sensor_comboBox.currentText()

        except:
            self.log.error("No sensors defined for project: " + str(project_name))
            self.variables.default_values_dict["settings"]["Current_sensor"] = "None"

    def load_setting_presets(self):
        """Loads the file pathes for the predefined measurement settings in the folder"""
        self.Settings_gui.select_settings_comboBox.clear()
        settings = self.variables.framework_variables["Configs"]["additional_files"][
            "Measurement_Settings"
        ]
        self.Settings_gui.select_settings_comboBox.addItems(settings.keys())
        # Load settings
        selected = self.Settings_gui.select_settings_comboBox.currentText()
        try:
            self.variables.ui_plugins[
                "MeasurementConfig_window"
            ].load_settings_from_file(settings[selected]["raw"])
        except:
            # Sometimes the settings are not loaded yet
            self.Settings_gui.select_settings_comboBox.clear()
            self.Setlog.warning(
                "Could not set settings, since settingsTab was not ready on runtime. Please reload..."
            )

    def settings_select_change_action(self):
        """Changes the settings after selection"""
        # Load settings
        settings = self.variables.framework_variables["Configs"]["additional_files"][
            "Measurement_Settings"
        ]
        selected = self.Settings_gui.select_settings_comboBox.currentText()
        if selected:
            self.variables.ui_plugins[
                "MeasurementConfig_window"
            ].load_settings_from_file(settings[selected]["raw"])
