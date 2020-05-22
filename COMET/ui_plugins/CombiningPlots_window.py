
from PyQt5.QtWidgets import QWidget, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QUrl, Qt
from ..misc_plugins.PlotScripts.forge.tools import customize_plot, relabelPlot
import ast

import yaml
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from ..misc_plugins.PlotScripts.myplot import *

class CombiningPlots_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.plotting_sessions = None
        self.current_session = None
        self.allFiles = []
        self.plot_path = {} # The plot hierachy inside the "all" entry of the plotObject
        self.plot_analysis = {} # The analysis each individual plot comes from
        self.selected_plot_option = ()
        self.current_plot_object = None # This is a list of tuples (plot_obj, session, path_in_session)
        self.plotting_thread = None
        self.to_combine_plots = [] # This is a list of tuples (plot_obj, session, path_in_session)
        self.not_saving = True
        self.combined_plot = None
        self.combinedPlotOptions = None

        # Device communication widget
        self.VisWidget = QWidget()
        self.widget = self.variables.load_QtUi_file("CombinePlots.ui",  self.VisWidget)
        self.layout.addWidget(self.VisWidget)

        # Config
        self.config_save_options()
        self.config_selectable_templates()

        # Connect buttons
        self.widget.save_toolButton.clicked.connect(self.select_save_to_action)
        self.widget.refresh_pushButton.clicked.connect(self.refresh_action)
        self.widget.output_tree.itemClicked.connect(self.get_current_selected_plot_object)
        self.widget.combine_treeWidget.itemClicked.connect(self.get_current_selected_to_combine_plot_object)
        self.widget.add_plot_pushButton.clicked.connect(self.add_action)
        self.widget.session_comboBox.currentIndexChanged.connect(self.session_change_action)
        self.widget.remove_plot_pushButton.clicked.connect(self.clear_action)
        self.widget.render_pushButton.clicked.connect(self.combine_and_show_action)
        self.widget.select_template_toolButton.clicked.connect(self.select_analysis_template)
        self.widget.save_as_pushButton.clicked.connect(self.save_as_action)
        self.widget.plot_options_treeWidget.itemClicked.connect(self.tree_option_select_action)
        self.widget.apply_option_pushButton.clicked.connect(self.apply_option_button)

    def save_as_action(self):
        """Saves the plots etc to the defined directory"""

        # Sets the cursor to wait
        self.variables.app.setOverrideCursor(Qt.WaitCursor)

        if self.not_saving:
            # Check if valid dir was given
            directory = self.widget.save_lineEdit.text()
            if os.path.exists(directory) and self.combined_plot:

                # Get save option
                options = self.widget.save_as_comboBox.currentText().split("/")

                plotters = ["html", "png", "svg"]

                # Start renderer
                for plot in plotters:
                    if plot in options:
                        save_plot("Combined Plot", self.combined_plot, directory, save_as = [plot], backend="bokeh")
            else:
                self.log.error("Either the path {} does not exist, or you must first render a few plots".format(directory))

        # Restore Cursor
        self.variables.app.restoreOverrideCursor()


    def config_selectable_templates(self):
        """Configs the combo box for selectable analysis templates"""
        self.widget.templates_comboBox.clear()
        plotConfigs = self.variables.framework_variables["Configs"]["additional_files"].get("Plotting", {})
        self.widget.templates_comboBox.addItems(plotConfigs.keys())

    def select_analysis_template(self):
        """Opens file select for template selection"""
        fileDialog = QFileDialog()
        files = fileDialog.getOpenFileNames()
        if files:
            for file in files[0]:
                try:
                    json_dump = load_yaml(file)
                    basename = os.path.basename(file).split(".")[0]
                    self.variables.framework_variables['Configs']['additional_files']['Plotting'][basename] = {"data": json_dump}
                except Exception as err:
                    self.log.error("Could not load file {}, exception raised: {}".format(file, err))
        self.config_selectable_templates()

    def combine_and_show_action(self):
        """Combines the plots and displays it"""
        self.variables.app.setOverrideCursor(Qt.WaitCursor)
        path = os.path.join(os.getcwd(), "__temp__")
        if not os.path.exists(path):
            os.mkdir(path)
        finalPlot = None
        for item in self.to_combine_plots:
            try:
                if finalPlot:
                    finalPlot *= item[0]
                else:
                    finalPlot = item[0]
            except:
                pass
        # Crude reconfig of the plots with the plot parameters from a simple plot file
        self.combinedPlotOptions = self.convert_config_to_dict(self.widget.templates_comboBox.currentText())
        self.combinedPlotTemplate = self.widget.templates_comboBox.currentText()
        finalPlot = customize_plot(finalPlot, self.widget.templates_comboBox.currentText(),
                                   self.combinedPlotOptions)
        save_plot("temp_combine_plot", finalPlot, path, save_as =["html"])
        self.widget.webEngineView.load(QUrl.fromLocalFile(os.path.join(path, "html", "temp_combine_plot.html")))
        self.current_plot_object = None
        self.combined_plot = finalPlot
        self.update_plot_options_tree(self.combined_plot)
        self.variables.app.restoreOverrideCursor()

    def parse_yaml_string(self, ys):
        fd = StringIO(ys)
        dct = yaml.load(fd)
        return dct

    def convert_config_to_dict(self, config_name):
        """Converts the config to a Dict if necessary"""
        plotConfigs = self.variables.framework_variables["Configs"]["additional_files"].get("Plotting", {})
        if not "data" in plotConfigs[(config_name)]:
            template = plotConfigs[(config_name)]["raw"]
            template = self.parse_yaml_string(template)
            plotConfigs[(config_name)]["data"] = template
        else:
            template = plotConfigs[(config_name)]["data"]
        return template

    def clear_action(self):
        """Clears the to combine data"""
        self.to_combine_plots = []
        self.widget.combine_treeWidget.clear()

    def add_action(self):
        """Actions to be made if you hit the add button"""
        if self.current_plot_object: # Only do something if a plot is selected
            tree = "_".join(self.current_plot_object[2])
            tree = "{} -> {}".format(self.current_plot_object[1], tree)
            tree = QTreeWidgetItem([tree])
            self.widget.combine_treeWidget.addTopLevelItem(tree)
            self.to_combine_plots.append(self.current_plot_object)

    def get_current_selected_to_combine_plot_object(self, item):
        """Loads a html file plot to the screen and stores the current value"""
        self.variables.app.setOverrideCursor(Qt.WaitCursor)
        path = os.path.join(os.getcwd(), "__temp__")
        if not os.path.exists(path):
            os.mkdir(path)
        ind = self.widget.combine_treeWidget.currentIndex().row()
        plot = self.to_combine_plots[ind][0]
        save_plot("temp_combine_plot", plot, path, save_as=["html"])
        self.widget.webEngineView.load(QUrl.fromLocalFile(os.path.join(path, "html", "temp_combine_plot.html")))

        self.variables.app.restoreOverrideCursor()

    def get_current_selected_plot_object(self, item):
        """Loads a html file plot to the screen and stores the current value"""
        self.variables.app.setOverrideCursor(Qt.WaitCursor)
        plotting_Object = self.plotting_sessions[self.current_session]
        try:
            for analy in plotting_Object.plotObjects:
                if self.plot_analysis[item.text(0)] == analy["Name"]:
                    plot = analy["All"]
                    for path_part in self.plot_path[item.text(0)]:
                        plot = getattr(plot, path_part)
                    filepath = plotting_Object.temp_html_output(plot)
                    self.widget.webEngineView.load(QUrl.fromLocalFile(filepath))
                    self.current_plot_object = (plot, self.current_session, self.plot_path[item.text(0)])
                    break

        except Exception as err:
            self.log.error("Plot could not be loaded. If this issue is not resolvable, re-render the plots! Error: {}".format(err))
        self.variables.app.restoreOverrideCursor()

    def session_change_action(self, text=None):
        """What to do if the session changes"""
        if self.widget.session_comboBox.currentText():
            self.current_session = self.widget.session_comboBox.currentText()
            self.update_plt_tree(self.plotting_sessions[self.widget.session_comboBox.currentText()])

    def refresh_action(self):
        """Refreshes the possible runs with plots"""
        try:
            self.widget.session_comboBox.clear()
            self.plotting_sessions = self.variables.ui_plugins["DataVisualization_window"].plot_sessions
            self.widget.session_comboBox.addItems(self.plotting_sessions.keys())
            self.session_change_action()

        except Exception as err:
            self.log.error("Could not load any plot sessions. It seems the plotting Tab is not rendered, or the plotting output is corrupted. Error: {}".format(err))

    def replot_and_reload_html(self, plot):
        """Replots a plot and displays it"""
        path = os.path.join(os.getcwd(), "__temp__")
        if not os.path.exists(path):
            os.mkdir(path)
        save_plot("temp_combine_plot", plot, path, save_as=["html"])
        self.widget.webEngineView.load(QUrl.fromLocalFile(os.path.join(path, "html", "temp_combine_plot.html")))
        self.current_plot_object = None
        self.combined_plot = plot
        self.update_plot_options_tree(self.combined_plot)

    def select_save_to_action(self):
        """Lets you select the output folder"""
        fileDialog = QFileDialog()
        dirr = fileDialog.getExistingDirectory()
        self.widget.save_lineEdit.setText(dirr)


    def render_action(self):
        """Stats the plotting scripts"""
        # Sets the cursor to wait
        self.variables.app.restoreOverrideCursor()
        self.variables.app.setOverrideCursor(Qt.WaitCursor)
        os.mkdir(os.path.join(os.getcwd(), "COMET", "temp")) if not os.path.exists(os.path.join(os.getcwd(), "COMET", "temp")) else True

        # Find template and load the yaml file
        plotConfigs = self.variables.framework_variables["Configs"]["additional_files"].get("Plotting", {})
        if not "data" in plotConfigs[(self.widget.templates_comboBox.currentText())]:
            template = plotConfigs[(self.widget.templates_comboBox.currentText())]["raw"]
            template = self.parse_yaml_string(template)
            plotConfigs[(self.widget.templates_comboBox.currentText())]["data"] = template
        else:
            template = plotConfigs[(self.widget.templates_comboBox.currentText())]["data"]

        # Add the parameters
        template["Files"] = [self.widget.session_comboBox.itemText(i) for i in range(self.widget.session_comboBox.count())]
        template["Output"] = self.widget.save_lineEdit.text()

        # Dump the yaml file in the output directory
        filepath = os.path.normpath(os.path.join(os.getcwd(), "COMET", "temp", "{}.yml".format("tempCONFIG")))
        with open(filepath, 'w') as outfile:
            yaml.dump(template, outfile, default_flow_style=False)

        args = ["--config", "{}".format(filepath), "--dont_show"]
        plotting = PlottingMain(configs=args)
        try:
            plotting.run()
            self.update_plt_tree(plotting)
            # Store current session
            self.plotting_Object = plotting
        except Exception as err:
            self.log.error("An error happened during plotting with error {}".format(err), exc_info=True)
            # Try to extract data until crash (this is just wishfull thinking, in most cases this will fail)
            try:
                self.update_plt_tree(plotting)
                # Store current session
                self.plotting_Object = plotting
            except:
                pass
            # Restore Cursor
            self.variables.app.restoreOverrideCursor()
            raise
        # Restore Cursor
        self.variables.app.restoreOverrideCursor()

    def update_plt_tree(self, plotting_output):
        """Updates the plot tree"""
        # Delete all values from the combo box
        self.widget.output_tree.clear()
        self.selected_plot_option = ()
        self.current_plot_object = None

        for analy in plotting_output.plotObjects:
            Allplots = analy.get("All", {})

            # Plot the inindividual plots/subplots
            if isinstance(Allplots,hv.core.layout.Layout):
                try:
                    for path in Allplots.keys():
                        tree = QTreeWidgetItem(["_".join(path)])
                        self.plot_path["_".join(path)] = path
                        self.plot_analysis["_".join(path)] = analy.get("Name", "")
                        self.widget.output_tree.addTopLevelItem(tree)
                except AttributeError as err:
                    self.log.warning("Attribute error happened during plot object access. Error: {}. "
                                     "Tyring to adapt...".format(err))
                    tree = QTreeWidgetItem([Allplots._group_param_value])
                    self.widget.output_tree.addTopLevelItem(tree)
                    self.plot_path[Allplots._group_param_value] = ()
                    self.plot_analysis[Allplots._group_param_value] = analy["Name"]
                except Exception as err:
                    self.log.error("An error happened during plot object access. Error: {}".format(err))
            else:
                try:
                    tree = QTreeWidgetItem(["Plot"])
                    self.plot_path["Plot"] = ()
                    self.plot_analysis["Plot"] = analy.get("Name", "")
                    self.widget.output_tree.addTopLevelItem(tree)
                except Exception as err:
                    self.log.error("An error happened during plot object access. Error: {}".format(err))

    def config_save_options(self):
        """Configs the save options like json,hdf5,etc"""
        options = ["html/png", "html", "png"]
        self.widget.save_as_comboBox.addItems(options)
    ########################

    def tree_option_select_action(self, item):
        """Action what happens when an option is selected"""
        key = item.text(0)
        value = item.text(1)
        self.widget.options_lineEdit.setText("{}: {}".format(key, value))

    def apply_option_button(self):
        """Applies the option made to the plot and repolts the current plot"""

        # Change the plot label from the line edit
        self.combined_plot = relabelPlot(self.combined_plot, self.widget.plot_label_lineEdit.text())

        line = self.widget.options_lineEdit.text()
        if line:
            ind = line.find(":")
            if ind == -1:
                ind = line.find("=")
            # Try  to evaluate
            try:
                value = ast.literal_eval(line[ind + 1:].strip())
            except:
                value = line[ind + 1:].strip()
            newItem = {line[:ind].strip(): value}
        else:
            newItem = {}  # If no options are passed, generate an empty one

        try:
            self.apply_options_to_plot(self.combined_plot, **newItem)
            self.replot_and_reload_html(self.combined_plot)
            if "PlotOptions" in self.combinedPlotOptions[self.combinedPlotTemplate]:
                self.combinedPlotOptions[self.combinedPlotTemplate]["PlotOptions"].update(newItem) # Kinda redundant
            else:
                self.combinedPlotOptions[self.combinedPlotTemplate]["PlotOptions"] = newItem

            self.update_plot_options_tree(self.combined_plot)
        except Exception as err:
            self.log.error("An error happened with the newly passed option with error: {} Option will be removed! "
                               "Warning: Depending on the error, you may have compromised the plot object and a re-render "
                               "may be needed!".format(err))

    def apply_options_to_plot(self, plot, **opts):
        """Applies the opts to the plot"""
        plot.opts(**opts)


    def update_plot_options_tree(self, plot):
        """Updates the plot options tree for the plot"""
        self.widget.plot_options_treeWidget.clear()
        self.widget.options_lineEdit.setText("")
        try:
            try:
                plotLabel = plot.label
            except:
                plotLabel = plot._label # This changed somehow
            if not plotLabel:
                raise ValueError # If none of the above exists

        except:
            self.log.debug("Plot object has no label, trying with group parameter...")
            # In case of special plots other access needed
            try:
                plotLabel = plot._group_param_value
                plotLabel = plotLabel.split(":")

            except:
                plotLabel = "None"
        self.widget.plot_label_lineEdit.setText(plotLabel)
        configs = self.combinedPlotOptions
        for opt, value in configs[self.combinedPlotTemplate].get("PlotOptions", {}).items():
            tree = QTreeWidgetItem({str(opt): "Option", str(value): "Value"})
            self.widget.plot_options_treeWidget.addTopLevelItem(tree)