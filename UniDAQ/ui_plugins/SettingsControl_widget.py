
import logging
from PyQt5.QtWidgets import QFileDialog
import yaml
import os, sys
from ..utilities import write_init_file


class SettingsControl_widget:

    def __init__(self, gui):
        """Configures the settings widget"""
        super(SettingsControl_widget, self).__init__(gui)
        self.gui = gui
        self.Setlog = logging.getLogger(__name__)

        # TODO: The init needs to be cleaned up a bit, currently not very pythonic structured
        # Adds all projects to the combo box
        for projects in self.variables.additional_files.get("Pad_files", {}):
            self.gui.proj_comboBox.addItem(str(projects))


        if "Current_project" in self.variables.default_values_dict["settings"]:
            self.variables.default_values_dict["settings"]["Current_project"] = \
            list(self.variables.additional_files["Pad_files"].keys())[0]  # That one project is definetly choosen
        else:
            self.variables.default_values_dict["settings"].update(
                {"Current_project": self.variables.default_values_dict["settings"].get("Projects", ["No Projects"])[0]})

        current_project = self.variables.default_values_dict["settings"].get("Current_project", None)
        self.gui.sensor_comboBox.addItems(self.variables.additional_files["Pad_files"][current_project])  # Adds all items to the combo box


        if "Current_sensor" in self.variables.default_values_dict["settings"]:
            try:
                self.variables.default_values_dict["settings"]["Current_sensor"] = \
                list(self.variables.additional_files["Pad_files"][current_project])[0]  # That one project is definetly choosen
            except:
                self.variables.default_values_dict["settings"]["Current_sensor"] = "None"
        else:
            if current_project and self.variables.additional_files["Pad_files"]:
                self.variables.default_values_dict["settings"].update({
                    "Current_sensor": list(self.variables.additional_files["Pad_files"][current_project])[0]})
            else:
                self.variables.default_values_dict["settings"].update({"Current_sensor": "None"})

        if "Current_filename" in self.variables.default_values_dict["settings"]:
            self.gui.filename.setText(str(self.variables.default_values_dict["settings"]["Current_filename"]))
        else:
            self.variables.default_values_dict["settings"].update({"Current_filename": "enter_filename_here"})
            self.gui.filename.setText(str(self.variables.default_values_dict["settings"]["Current_filename"]))

        for projects in self.variables.default_values_dict["settings"].get("Operator", "None"):
            self.gui.operator_comboBox.addItem(str(projects))  # Adds all items to the combo box

        if "Current_operator" in self.variables.default_values_dict["settings"]:
            self.variables.default_values_dict["settings"]["Current_operator"] = \
            self.variables.default_values_dict["settings"]["Operator"][0]  # That one project is definetly choosen
        else:
            self.variables.default_values_dict["settings"].update(
                {"Current_operator": self.variables.default_values_dict["settings"].get("Operator", ["None", ])[0]})

        if "Current_directory" in self.variables.default_values_dict["settings"]:  # TODO check if directory exists
            self.gui.output_dir_edit.setText(str(self.variables.default_values_dict["settings"]["Current_directory"]))
        else:
            self.variables.default_values_dict["settings"].update(
                {"Current_directory": str(os.path.join(os.path.dirname(sys.modules[__name__].__file__)))})
            self.gui.output_dir_edit.setText(str(os.path.join(os.path.dirname(sys.modules[__name__].__file__))))

        self.gui.load_settings_button.clicked.connect(self.load_measurement_settings_file)
        self.gui.save_settings_button.clicked.connect(self.save_measurement_settings_file)
        self.gui.save_to_button.clicked.connect(self.dir_selector_action)
        self.gui.operator_comboBox.activated[str].connect(self.operator_selector_action)
        self.gui.sensor_comboBox.activated[str].connect(self.sensor_selector_action)
        self.gui.proj_comboBox.activated[str].connect(self.project_selector_action)
        self.gui.filename.textChanged[str].connect(self.change_name)

    # Order functions
    def change_name(self, filename):
        self.variables.default_values_dict["settings"]["Current_filename"] = str(filename)

    def project_selector_action(self, project):
        self.load_valid_sensors_for_project(str(project))
        self.variables.default_values_dict["settings"]["Current_project"] = str(project)

    def sensor_selector_action(self,sensor):
        self.variables.default_values_dict["settings"]["Current_sensor"] = str(sensor)

    def operator_selector_action(self,operator):
        self.variables.default_values_dict["settings"]["Current_operator"] = str(operator)

    def dir_selector_action(self):
        fileDialog = QFileDialog()
        directory = fileDialog.getExistingDirectory()
        self.gui.output_dir_edit.setText(directory)
        self.variables.default_values_dict["settings"]["Current_directory"] = str(directory)

    def load_measurement_settings_file(self):
        ''' This function loads a mesuerment settings file'''

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
        ''' This function saves a mesuerment settings file'''

        #First update the settings that the state machine is up to date
        self.variables.ui_plugins["Settings_window"].load_new_settings()

        fileDialog = QFileDialog()
        file = fileDialog.getSaveFileName()

        if file[0]:
            # gets me all settings which are to be saved
            write_init_file(file[0], self.variables.ui_plugins["Settings_window"].get_all_settings())
            self.Setlog.info("Settings file successfully written to: {}".format(file))

    def load_valid_sensors_for_project(self, project_name):
        '''This function loads the valid sensors for each project'''
        #Warning sensor_comboBox must be accessable for this function to work
        self.gui.sensor_comboBox.clear()
        try:
            # self.variables.default_values_dict["settings"]["Sensor_types"][project_name]
            self.gui.sensor_comboBox.addItems(list(self.variables.additional_files["Pad_files"][project_name].keys()))  # Adds all items to the combo box
            # Select the first element to be right, if possible
            self.variables.default_values_dict["settings"]["Current_sensor"] = self.gui.sensor_comboBox.currentText()

        except:
            self.log.error("No sensors defined for project: " + str(project_name))
            self.variables.default_values_dict["settings"]["Current_sensor"] = "None"

