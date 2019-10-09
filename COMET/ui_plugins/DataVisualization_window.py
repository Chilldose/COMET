import logging
from PyQt5.QtWidgets import QWidget, QFileDialog, QTreeWidgetItem
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.Qt import QApplication
import numpy as np
from ..utilities import save_dict_as_hdf5, save_dict_as_json

import yaml, json
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from ..misc_plugins.PlotScripts.myplot import *

class DataVisualization_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.allFiles = []
        self.plotting_Object = None
        self.plot_path = {}

        # Device communication widget
        self.VisWidget = QWidget()
        self.widget = self.variables.load_QtUi_file("DataVisualisation.ui",  self.VisWidget)
        self.layout.addWidget(self.VisWidget)

        # Config
        self.config_selectable_templates()
        self.config_save_options()

        # Connect buttons
        self.widget.files_toolButton.clicked.connect(self.select_files_action)
        self.widget.upload_pushButton.clicked.connect(self.upload_to_DB)
        self.widget.save_toolButton.clicked.connect(self.select_save_to_action)
        self.widget.render_pushButton.clicked.connect(self.render_action)
        self.widget.output_tree.itemClicked.connect(self.load_html_to_screen)
        self.widget.save_as_pushButton.clicked.connect(self.save_as_action)

    def load_html_to_screen(self, item):
        """Loads a html file plot to the screen"""
        self.variables.app.setOverrideCursor(Qt.WaitCursor)
        for analy in self.plotting_Object.plotObjects:
            if hasattr(analy["All"], item.text(0)):
                plot = getattr(analy["All"], self.plot_path[item.text(0)][0])
                plot = getattr(plot, self.plot_path[item.text(0)][1])
                filepath = self.plotting_Object.temp_html_output(plot)
                self.widget.webEngineView.load(QUrl.fromLocalFile(filepath))
        self.variables.app.restoreOverrideCursor()

    def select_files_action(self):
        """Opens a file selection window and writes it to the data files drop down menu"""
        self.widget.files_comboBox.clear()
        fileDialog = QFileDialog()
        files = fileDialog.getOpenFileNames()
        self.widget.files_comboBox.addItems(files[0])
        self.allFiles = files[0]

    def select_save_to_action(self):
        """Lets you select the output folder"""
        fileDialog = QFileDialog()
        dirr = fileDialog.getExistingDirectory()
        self.widget.save_lineEdit.setText(dirr)

    def parse_yaml_string(self, ys):
        fd = StringIO(ys)
        dct = yaml.load(fd)
        return dct

    def render_action(self):
        """Stats the plotting scripts"""
        # Sets the cursor to wait
        self.variables.app.setOverrideCursor(Qt.WaitCursor)

        try:
            os.mkdir(os.path.join(os.getcwd(), "COMET", "temp"))
        except:
            pass

        # Find template and load the yaml file
        plotConfigs = self.variables.framework_variables["Configs"]["additional_files"].get("Plotting", {})
        template = plotConfigs[(self.widget.templates_comboBox.currentText()+"_template")]["raw"]
        template = self.parse_yaml_string(template)

        # Add the parameters
        template["Files"] = self.allFiles
        template["Output"] = self.widget.save_lineEdit.text()

        # Dump the yaml file in the output directory
        filepath = os.path.normpath(os.path.join(os.getcwd(), "COMET", "temp", "{}.yml".format("tempCONFIG")))
        with open(filepath, 'w') as outfile:
            yaml.dump(template, outfile, default_flow_style=False)

        args = ["--config", "{}".format(filepath), "--show"]
        plotting = PlottingMain(configs=args)
        plotting.run()

        self.update_plt_tree(plotting)

        # Store current session
        self.plotting_Object = plotting

        # Restore Cursor
        self.variables.app.restoreOverrideCursor()



    def update_plt_tree(self, plotting_output):
        """Updates the plot tree"""
        # Delete all values from the combo box
        self.widget.output_tree.clear()
        for analy in plotting_output.plotObjects:
            Allplots = analy.get("All", {})
            try:
                for name, subdict in Allplots.keys():
                    tree = QTreeWidgetItem([name+"_"+subdict])
                    self.plot_path[name+"_"+subdict] = (name, subdict)
                    self.widget.output_tree.addTopLevelItem(tree)
            except AttributeError as err:
                self.log.error("Attribute Error happened during plot object access. Error: {}".format(err))


    def upload_to_DB(self):
        """lets you upload the data to the DB"""
        self.log.error("Saving to the Data Base is not yet implemented.")

    def config_save_options(self):
        """Configs the save options like json,hdf5,etc"""
        options = ["html", "html/png", "html/json", "html/png/json", "png", "html/hdf5"]
        self.widget.save_as_comboBox.addItems(options)

    def config_selectable_templates(self):
        """Configs the combo box for selectable analysis templates"""
        plotConfigs = self.variables.framework_variables["Configs"]["additional_files"].get("Plotting", {})
        for key in plotConfigs.keys():
            if "_template" in key:
                self.widget.templates_comboBox.addItem(key.split("_template")[0])

    def save_data(self, type, dirr):
        """Saves the data in the specified type"""
        try:
            os.mkdir(os.path.join(os.path.normpath(dirr), "data"))
        except:
            pass

        if type == "json":
            # JSON serialize
            save_dict_as_json(self.plotting_Object.data, os.path.join(os.path.normpath(dirr), "data", "data.json"))
        if type == "hdf5":
            save_dict_as_hdf5(self.plotting_Object.data, os.path.join(os.path.normpath(dirr), "data", "data.hdf5"))

    def save_as_action(self):
        """Saves the plots etc to the defined directory"""

        # Sets the cursor to wait
        self.variables.app.setOverrideCursor(Qt.WaitCursor)

        # Check if valid dir was given
        directory = self.widget.save_lineEdit.text()
        if os.path.exists(directory):
            # Get save option
            options = self.widget.save_as_comboBox.currentText().split("/")

            plotters = ["html", "png", "svg"]
            data = ["json", "hdf5"]

            # Start renderer
            if self.plotting_Object.config:
                self.plotting_Object.config["Save_as"] = []
                self.plotting_Object.config["Output"] = directory
                for plot in plotters:
                    if plot in options:
                        self.plotting_Object.config["Save_as"].append(plot)
                self.plotting_Object.save_to() # Starts the routine

                # Start data saver
                for ty in data:
                    if ty in options:
                        self.save_data(ty, directory)

        else:
            self.log.error("Path {} does not exist, please choose a valid path".format(directory))

        # Restore Cursor
        self.variables.app.restoreOverrideCursor()