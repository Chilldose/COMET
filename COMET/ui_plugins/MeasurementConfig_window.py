import logging
from PyQt5.QtWidgets import *
from PyQt5 import QtGui


class MeasurementConfig_window():

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.settings = self.variables.framework_variables['Configs']['config'].get('MeasurementSettings', {}).copy()
        self.ui_groups = {}
        self.columns = 4 # Number of columns per group
        if not self.settings:
            self.log.error("Measurement settings tab was loaded but no options have been given. Please add the settings to your project")


        # Settings Main tab
        self.SettingsMainWidget = QWidget()
        self.SettingsGui = self.variables.load_QtUi_file("SettingsTab.ui",  self.SettingsMainWidget)
        self.layout.addWidget(self.SettingsMainWidget)
        #self.SettingsMainWidget.scrollAreaWidgetContents.widgetResizable = True

        self.construct_ui()


    def construct_ui(self):
        """Constructs the UI"""

        # Run through all options
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

                    # Add the button and enable
                    conf_ui.frame.setEnabled(measurements["Do"])
                    ui.EnableGroup_pushButton.clicked[bool].connect(conf_ui.frame.setEnabled)

            # Adjust grid position
            row += 1

            if row >= self.columns:
                row = 0
                line += 1
