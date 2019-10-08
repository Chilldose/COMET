import logging
from PyQt5.QtWidgets import QWidget, QFileDialog, QTreeWidgetItem
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.Qt import QApplication

import yaml
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

        # Device communication widget
        self.VisWidget = QWidget()
        self.widget = self.variables.load_QtUi_file("DataVisualisation.ui",  self.VisWidget)
        self.layout.addWidget(self.VisWidget)

        # Config
        self.config_selectable_templates()

        # Connect buttons
        self.widget.files_toolButton.clicked.connect(self.select_files_action)
        self.widget.upload_pushButton.clicked.connect(self.upload_to_DB)
        self.widget.save_toolButton.clicked.connect(self.select_save_to_action)
        self.widget.render_pushButton.clicked.connect(self.render_action)
        self.widget.output_tree.itemClicked.connect(self.load_html_to_screen)

    def load_html_to_screen(self, item):
        """Loads a html file plot to the screen"""
        self.variables.app.setOverrideCursor(Qt.WaitCursor)
        for analy in self.plotting_Object.plotObjects:
            if hasattr(analy["All"], item.text(0)):
                split_ind = item.text(0).find("_")
                plot = getattr(analy["All"], item.text(0)[:split_ind])
                plot = getattr(plot, item.text(0)[split_ind+1:])
                filepath = self.plotting_Object.temp_html_output(plot)
                self.widget.webEngineView.load(QUrl.fromLocalFile(filepath))
        self.variables.app.restoreOverrideCursor()

    def select_files_action(self):
        """Opens a file selection window and writes it to the data files drop down menu"""
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
        # Set the curso to wait
        self.variables.app.setOverrideCursor(Qt.WaitCursor)

        try:
            os.mkdir(self.widget.save_lineEdit.text())
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
        filepath = os.path.normpath(os.path.join(self.widget.save_lineEdit.text(), "{}.yml".format("CONFIG")))
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
        for analy in plotting_output.plotObjects:
            Allplots = analy.get("All", {})
            for name, subdict in Allplots.keys():
                tree = QTreeWidgetItem([name+"_"+subdict])
                self.widget.output_tree.addTopLevelItem(tree)


    def upload_to_DB(self):
        """lets you upload the data to the DB"""
        self.log.error("Saving to the Data Base is not yet implemented.")

    def config_selectable_templates(self):
        """Configs the combo box for selectable analysis templates"""
        plotConfigs = self.variables.framework_variables["Configs"]["additional_files"].get("Plotting", {})
        for key in plotConfigs.keys():
            if "_template" in key:
                self.widget.templates_comboBox.addItem(key.split("_template")[0])