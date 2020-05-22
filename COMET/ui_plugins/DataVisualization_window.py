
from PyQt5.QtWidgets import QWidget, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QUrl, Qt
from PyQt5 import QtGui
from PyQt5 import QtCore
import threading
import traceback
import ast
import re
from time import asctime
from ..utilities import save_dict_as_hdf5, save_dict_as_json, save_dict_as_xml, convert_dict_to_xml
import yaml
from warnings import filterwarnings
filterwarnings('ignore', message='yaml.load()', category=yaml.YAMLLoadWarning)


try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from ..misc_plugins.PlotScripts.myplot import *
from ..misc_plugins.PlotScripts.forge.tools import relabelPlot

class DataVisualization_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)
        self.allFiles = []
        self.plotting_Object = None
        self.plot_sessions = {}
        self.plot_path = {} # The plot hierachy inside the "all" entry of the plotObject
        self.plot_analysis = {} # The analysis each individual plot comes from
        self.selected_plot_option = ()
        self.current_plot_object = None
        self.current_plot_name = ""
        self.not_saving = True
        self.plotting_thread = None
        self.backend = None

        # Device communication widget
        self.VisWidget = QWidget()
        self.widget = self.variables.load_QtUi_file("DataVisualisation.ui",  self.VisWidget)
        self.layout.addWidget(self.VisWidget)

        # Config
        self.config_selectable_templates()
        self.config_save_options()

        # Set the possible plotting backends
        self.possible_backends = ["bokeh", "matplotlib"]
        self.widget.backend_comboBox.addItems(self.possible_backends)
        self.set_backend("bokeh")

        # Connect buttons
        self.widget.files_toolButton.clicked.connect(self.select_files_action)
        self.widget.select_template_toolButton.clicked.connect(self.select_analysis_template)
        self.widget.upload_pushButton.clicked.connect(self.upload_to_DB)
        self.widget.save_toolButton.clicked.connect(self.select_save_to_action)
        self.widget.render_pushButton.clicked.connect(self.render_action)
        self.widget.output_tree.itemClicked.connect(self.load_html_to_screen)
        self.widget.plot_options_treeWidget.itemClicked.connect(self.tree_option_select_action)
        self.widget.save_as_pushButton.clicked.connect(self.save_as_action)
        self.widget.apply_option_pushButton.clicked.connect(self.apply_option_button)
        self.widget.backend_comboBox.currentTextChanged.connect(self.set_backend)

    def set_backend(self, backend):
        """Sets the entries for the plotting backends"""
        self.backend = backend
        index = self.widget.backend_comboBox.findText(backend, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.widget.backend_comboBox.setCurrentIndex(index)

    def set_current_plot_object(self):
        """Saves the current plot object in the global data construct. Otherwise changes are not saved"""
        for analy in self.plotting_Object.plotObjects:
            if self.plot_analysis[self.current_plot_name] == analy["Name"]:
                plot = analy["All"]
                if len(self.plot_path[self.current_plot_name]):
                    for path_part in self.plot_path[self.current_plot_name][:-1]:
                        plot = getattr(plot, path_part)
                    setattr(plot, self.plot_path[self.current_plot_name][-1], self.current_plot_object)
                else:
                    analy["All"] = self.current_plot_object

    def generate_html_page_for_png_view(self, filepath):
        """Generates a html page, which simply shows an png."""
        html_content = '<html> \
                       <body> \
                       <img border="0" src="{}" alt="name" width="{}" height="{}" /> \
                       </body> \
                       </html>'

        path = os.path.normpath(filepath.split(".")[0] + ".html")
        width, height = self.get_image_size(filepath)
        with open(path, "w+") as f:
            f.write(html_content.format(filepath, width, height))
        return path

    def load_html_to_screen(self, item):
        """Loads a html file plot to the screen"""
        self.variables.app.setOverrideCursor(Qt.WaitCursor)
        try:
            for analy in self.plotting_Object.plotObjects:
                if self.plot_analysis[item.text(0)] == analy["Name"]:
                    plot = analy["All"]
                    for path_part in self.plot_path[item.text(0)]:
                        plot = getattr(plot, path_part)
                    if self.backend == "bokeh":
                        filepath = self.plotting_Object.temp_html_output(plot)
                    elif self.backend == "matplotlib":
                        filepath = self.plotting_Object.temp_png_output(plot)
                        filepath = self.generate_html_page_for_png_view(filepath)
                    else:
                        self.log.error("The backend {} is not a valid backend!".format(self.backend))
                        return
                    self.widget.webEngineView.load(QUrl.fromLocalFile(filepath))
                    self.current_plot_object = plot
                    self.current_plot_name = item.text(0)
                    self.update_plot_options_tree(plot)
                    break

        except Exception as err:
            self.log.error("Plot could not be loaded. If this issue is not resolvable, re-render the plots! Error: {}".format(err))
        self.variables.app.restoreOverrideCursor()

    def change_plot_label_edit(self, Label):
        """Changes the plot label edit"""
        self.widget.plot_label_lineEdit.setText(Label)

    def replot_and_reload_html(self, plot):
        """Replots a plot and displays it"""
        if self.backend == "bokeh":
            filepath = self.plotting_Object.temp_html_output(plot)
        elif self.backend == "matplotlib":
            filepath = self.plotting_Object.temp_png_output(plot)
            filepath = self.generate_html_page_for_png_view(filepath)
        self.widget.webEngineView.load(QUrl.fromLocalFile(filepath))

    def select_analysis_template(self):
        """Opens file select for template selection"""
        fileDialog = QFileDialog()
        files = fileDialog.getOpenFileNames()
        basename = None
        if files:
            for file in files[0]:
                try:
                    json_dump = load_yaml(file)
                    basename = os.path.basename(file).split(".")[0]
                    self.variables.framework_variables['Configs']['additional_files']['Plotting'][basename] = {"data": json_dump}

                except Exception as err:
                    self.log.error("Could not load file {}, exception raised: {}".format(file, err))
        self.config_selectable_templates(select=basename)


    def select_files_action(self):
        """Opens a file selection window and writes it to the data files drop down menu"""
        self.widget.files_comboBox.clear()
        fileDialog = QFileDialog()
        files = fileDialog.getOpenFileNames()
        self.config_files_combo_box(files[0])
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

    def save_config_yaml(self, config, dirr):
        """Simply saves the dict as yaml"""
        with open(dirr, 'w') as outfile:
            yaml.dump(config, outfile, default_flow_style=False)

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
        template["Files"] = [self.widget.files_comboBox.itemText(i) for i in range(self.widget.files_comboBox.count())]
        template["Output"] = self.widget.save_lineEdit.text()
        #if "backend" in template:
        #    self.set_backend(template["backend"])
        #else:
        template["backend"] = self.backend

        # Dump the yaml file in the output directory
        filepath = os.path.normpath(os.path.join(os.getcwd(), "COMET", "temp", "{}.yml".format("tempCONFIG")))
        with open(filepath, 'w') as outfile:
            yaml.dump(template, outfile, default_flow_style=False)

        args = ["--config", "{}".format(filepath), "--dont_show"]

        try:
            plotting = PlottingMain(configs=args)
            plotting.run()
            self.update_plt_tree(plotting)

            # Name the session with a ascii time stamp
            session_name = self.widget.session_name_lineEdit.text()
            if not session_name:
                self.log.critical("You did not define a name for the current plotting session, taking timestamp instead! Please always define a session name!")
                self.widget.session_name_lineEdit.setText("{}".format(asctime()))
            elif session_name in self.plot_sessions.keys():
                self.log.critical(
                    "The session name {} already exists, taking timestamp instead! Please always define a unique session name!".format(session_name))
                self.widget.session_name_lineEdit.setText("{}".format(asctime()))

            # Store current session
            self.plotting_Object = plotting

            # Save session
            self.save_session(self.widget.session_name_lineEdit.text(), self.plotting_Object)

        except Exception as err:
            self.log.error("An error happened during plotting with error {}".format(err), exc_info=True)
            try:
                raise
            except:
                self.log.error(traceback.format_exc())
            # Try to extract data until crash (this is just wishfull thinking, in most cases this will fail)
            try:
                self.update_plt_tree(plotting)
                # Store current session
                self.plotting_Object = plotting
            except:
                pass
            # Restore Cursor
            self.variables.app.restoreOverrideCursor()

        # Restore Cursor
        self.variables.app.restoreOverrideCursor()

    def save_session(self, name, session):
        """Saves the current session in a deepcopy environement"""
        if name in self.plot_sessions:
            self.plot_sessions[name] = None
        self.plot_sessions[name] = session

    def tree_option_select_action(self, item):
        """Action what happens when an option is selected"""
        key = item.text(0)
        value = item.text(1)
        self.widget.options_lineEdit.setText("{}: {}".format(key, value))

    def apply_option_button(self):
        """Applies the option made to the plot and repolts the current plot"""

        # get the correct options
        configs = self.plotting_Object.config

        if self.selected_plot_option:
            for path in self.selected_plot_option:
                configs = configs[path]

            # Change the plot label from the line edit
            if self.widget.plot_label_lineEdit.text():
                configs["PlotLabel"] = self.widget.plot_label_lineEdit.text()
                self.current_plot_object = relabelPlot(self.current_plot_object, configs["PlotLabel"])

            # Find the plot options otherwise generate
            if not "PlotOptions" in configs:
                configs["PlotOptions"] = {}

            # Find index of first colon
            line = self.widget.options_lineEdit.text()
            if line:
                ind = line.find(":")
                if ind == -1:
                    ind = line.find("=")
                #Try  to evaluate
                try:
                    value = ast.literal_eval(line[ind + 1:].strip())
                except:
                    value = line[ind + 1:].strip()
                newItem = {line[:ind].strip(): value}
            else:
                newItem = {} # If no options are passed, generate an empty one
            try:
                apply_success = False
                errors = []

                if hasattr(self.current_plot_object, "children"):
                    childs = len(self.current_plot_object.children)
                else: childs = 1

                if childs > 1:
                    self.log.critical("Applying options to composite plot objects is currently experimental. Unforseen results may occure!")
                    for child in self.current_plot_object.keys():
                        plot_object = self.current_plot_object
                        for path in child:
                            plot_object = getattr(plot_object, path)
                        try:
                            self.apply_options_to_plot(plot_object, **newItem)
                            apply_success = True
                            break
                        except Exception as err:
                            self.log.debug(err)
                            errors.append(err)
                    if not apply_success:
                        for err in errors:
                                raise Exception(err)
                else:
                    self.apply_options_to_plot(self.current_plot_object, **newItem)

                self.replot_and_reload_html(self.current_plot_object)
                configs["PlotOptions"].update(newItem)
                self.update_plot_options_tree(self.current_plot_object)
                self.set_current_plot_object()
                self.save_session(self.widget.session_name_lineEdit.text(), self.plotting_Object) # Saves the changes in the session
            except Exception as err:
                self.log.error("An error happened with the newly passed option with error: {} Option will be removed! "
                               "Warning: Depending on the error, you may have compromised the plot object and a re-render "
                               "may be needed!".format(err))

        else:
            # If the plot was altered and no options can be rebuild
            self.log.error("The plot options for this plot can not be retraced! Maybe the plot was altered during building."
                           " Applying options anyway, but no options history can be shown!")
            try:
                # Change the plot label from the line edit
                if self.widget.plot_label_lineEdit.text():
                    configs["PlotLabel"] = self.widget.plot_label_lineEdit.text()
                    self.current_plot_object = relabelPlot(self.current_plot_object, configs["PlotLabel"])

                # Find index of first colon
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
                self.apply_options_to_plot(self.current_plot_object, **newItem)
                self.replot_and_reload_html(self.current_plot_object)
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
        self.change_plot_label_edit("")
        configs = self.plotting_Object.config
        self.selected_plot_option = ()
        try:
            try:
                plotLabel = plot.label
            except:
                plotLabel = plot._label # This changed somehow
            if not plotLabel:
                raise ValueError # If none of the above exists
            for ana in configs["Analysis"]:
                for plot_name, plt_opt in configs[ana].items():
                    try:
                        if plotLabel == plt_opt.get("PlotLabel", ""):
                            self.change_plot_label_edit(plotLabel)
                            # Save current options tree
                            self.selected_plot_option = (ana, plot_name)

                            # Add the key to the tree
                            plotconf = configs[ana].get("General", {}).copy()
                            plotconf.update(plt_opt.get("PlotOptions", {}))
                            for opt, value in plotconf.items():
                                tree = QTreeWidgetItem({str(opt): "Option", str(value): "Value"})
                                self.widget.plot_options_treeWidget.addTopLevelItem(tree)
                            break
                    except:
                        pass
        except:
            self.log.debug("Plot object has no label, trying with group parameter...")

            # In case of special plots other access needed
            try:
                plotLabel = plot.group
                plotLabel = plotLabel.split(":")

                for ana in configs["Analysis"]:
                    for plot_name, plt_opt in configs[ana].items():
                        try:
                            if plotLabel[1].strip() == plt_opt.get("PlotLabel", "") or plotLabel[1].strip() == plot_name:
                                if "{}".format(plotLabel[0].strip()) in plt_opt:
                                    # Save current options tree
                                    self.selected_plot_option = (ana, plot_name, "{}".format(plotLabel[0].strip()))

                                    # Add the key to the tree
                                    plotconf = configs[ana].get("General", {}).copy()
                                    plotconf.update(configs[ana].get("{}".format(plotLabel[0].strip()) + "Options", {}))
                                    plotconf.update(plt_opt["{}".format(plotLabel[0].strip())].get("PlotOptions", {}))
                                    for opt, value in plotconf.items():
                                        tree = QTreeWidgetItem({str(opt): "Option", str(value): "Value"})
                                        self.widget.plot_options_treeWidget.addTopLevelItem(tree)
                                    return
                                else:
                                    # If this entry is missing generate an empty dict so options can be added later on
                                    self.selected_plot_option = (ana, plot_name, "{}".format(plotLabel[0].strip()))
                                    plt_opt["{}".format(plotLabel[0].strip())] = {}
                                    self.update_plot_options_tree(plot)
                                    return
                        except Exception as err:
                            self.selected_plot_option = ()
            except:
                self.selected_plot_option = ()

    def update_plt_tree(self, plotting_output):
        """Updates the plot tree"""
        # Delete all values from the combo box
        self.widget.output_tree.clear()
        self.widget.plot_options_treeWidget.clear()
        self.widget.options_lineEdit.setText("")
        self.selected_plot_option = ()
        self.current_plot_object = None

        for analy in plotting_output.plotObjects:
            Allplots = analy.get("All", {})

            # Try to plot all together as well. but this my not work for all
            #try:
            #    tree = QTreeWidgetItem(["_".join(path)])
            #    self.plot_path["_".join(path)] = path
            #    self.plot_analysis["_".join(path)] = analy.get("Name", "")
            #    self.widget.output_tree.addTopLevelItem(tree)

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
                    self.log.error("An error happened during plot object access.", exc_info=True)
            else:
                try:
                    tree = QTreeWidgetItem(["Plot"])
                    self.plot_path["Plot"] = ()
                    self.plot_analysis["Plot"] = analy.get("Name", "")
                    self.widget.output_tree.addTopLevelItem(tree)
                except Exception as err:
                    self.log.error("An error happened during plot object access.", exc_info=True)



    def upload_to_DB(self):
        """lets you upload the data to the DB"""
        self.log.error("Saving to the Data Base is not yet implemented.")

    def config_save_options(self):
        """Configs the save options like json,hdf5,etc"""
        options = ["html/png/xml", "html/png/json/hdf5", "html", "html/png", "html/json", "html/png/json", "png", "html/hdf5", "hdf5/json", "svg", "xml"]
        self.widget.save_as_comboBox.addItems(options)

    def config_selectable_templates(self, select=None):
        """Configs the combo box for selectable analysis templates"""
        self.widget.templates_comboBox.clear()
        plotConfigs = self.variables.framework_variables["Configs"]["additional_files"].get("Plotting", {})
        self.widget.templates_comboBox.addItems(plotConfigs.keys())
        if select:
            index = self.widget.templates_comboBox.findText(select, QtCore.Qt.MatchFixedString)
            if index >= 0:
                self.widget.templates_comboBox.setCurrentIndex(index)


    def save_data(self, type, dirr, base_name="data"):
        """Saves the data in the specified type"""
        try:
            os.mkdir(os.path.join(os.path.normpath(dirr), "data"))
        except:
            pass

        if type == "json":
            # JSON serialize
            self.log.info("Saving JSON file...")
            save_dict_as_json(deepcopy(self.plotting_Object.data), os.path.join(os.path.normpath(dirr), "data"), base_name)
        if type == "hdf5":
            self.log.info("Saving HDF5 file...")
            save_dict_as_hdf5(deepcopy(self.plotting_Object.data), os.path.join(os.path.normpath(dirr), "data"), base_name)
        if type == "xml":
            self.log.info("Saving xml file...")

            # Convert to CMS database xml
            data = self.plotting_Object.data
            for key, dat in data.items():
                template_name = self.variables.framework_variables["Configs"]["config"]["settings"].get("xml_template", None)
                if template_name:
                    template = self.variables.framework_variables["Configs"]["config"][template_name]
                    header_dict = self.insert_values_from_header(template, dat["header"])
                    final_xml = convert_dict_to_xml(header_dict)
                    final_xml_dict = self.insert_templates(dat, final_xml, template)

                    for subkey, value in final_xml_dict.items():
                        save_dict_as_xml(value, os.path.join(os.path.normpath(dirr), "data"), "{}_{}_".format(key, subkey))
                else:
                    self.log.error("No xml template stated in settings. Please add 'xml_template' to your configs.")

    def insert_templates(self, dat, xml_string, xml_config_file):
        """Inserts any template for data into the XML string and returns a XML string"""#
        import xml.etree.ElementTree as ET
        template_re = re.compile(r"//(.*)//") # Regex for the template
        root = ET.fromstring(xml_string) # convert the xml string to a xmltree

        def validate_node(elem, path):
            """This just validates the node from a given path for easy access"""
            for child in elem.getchildren():
                if path[0] == child.tag:
                    if len(path[1:]): # If len is left, the full path is not yet resolved
                        validate_node(child, path[1:])
                    else:
                        return child

        def generate_template_xml_elements(kdim, element_name, xml_node, template, data):
            """Genrerates a xml template entry"""
            xml_node.remove(xml_node.find(element_name)) # So that the template entry is gone
            keyword_re = re.compile(r"<(.*)>")
            for i, value in enumerate(data["data"][kdim]):
                root = ET.SubElement(xml_node, element_name)
                for key, entry in template.items():
                    data_key = keyword_re.findall(entry)
                    if data_key:
                        try:
                            element = ET.SubElement(root, key)
                            element.text = str(data["data"][entry.replace("<", "").replace(">","")][i])
                        except IndexError:
                            self.log.warning("The Index {} seems to be missing in the data".format(entry.replace("<", "").replace(">","")))
                            break
            pass

        def dict_template_insert_iter(diction, path):
            """Goes over all entries in the dict and inserts single values from the header"""
            final_tree = {}
            for key, item in diction.items():
                if isinstance(item, dict):
                    path.append(key)
                    final_tree.update(dict_template_insert_iter(item, path))
                    path.pop()
                else:
                    keyword = template_re.match(str(item))
                    subtrees = {}  # Todo: only one template allowed here, fix
                    if keyword:
                        path.append(key)
                        for kdim in xml_config_file[keyword.string.replace("/", "")]:
                            if kdim in dat["data"].keys(): # Todo: this may fail, and I am using raw data here,
                                subtrees[kdim] = deepcopy(root)
                                node = validate_node(subtrees[kdim], path[:-1]) # Since we dont want the actual entry, just where to put it
                                generate_template_xml_elements(kdim, path[-1], node, xml_config_file[keyword.string.replace("/", "")][kdim], dat)
                        final_tree.update(subtrees)
                        path.pop()
                    #return final_tree
            return final_tree

        xml_dicts = dict_template_insert_iter(xml_config_file["Template"], path=[])
        return xml_dicts


    def insert_values_from_header(self, xml_config_file, header=""):
        """
        Converts data to a specific form, as a dict stated in the config parameter.
        The config file must have a key named 'template' in it must be the dict representation of the xml file.
        Subkeys with a value enclosed by <..> are keywords. The header of the file will be searched for such key words.
        If it finds the regular expression r'<EXPR>\W\s?(.*)'

        :param data: data structure
        :param xml_config_file: the configs on how to convert data to xml
        :param header: a header (str) with key values like "Operator: Batman", the function tries to extract the data for the xml from there
        :return: None
        """
        template = deepcopy(xml_config_file["Template"])
        keyword_re = re.compile(r"<(.*)>")

        def dict_value_insert_iter(diction):
            """Goes over all entries in the dict and inserts single values from the header"""
            for key, item in diction.items():
                if isinstance(item, dict):
                    dict_value_insert_iter(item)
                else:
                    keyword = keyword_re.match(str(item))
                    if keyword:
                        for line in header:
                            newvalue = re.search(r"{}\W\s?(.*)".format(keyword[1]), line)
                            if newvalue:
                                diction[key] = str(newvalue[1]).strip()
                                break
                            else:
                                #pass
                                diction[key] = str(None)
                    else:
                        diction[key] = str(None)

        # Insert the simple values from the header
        dict_value_insert_iter(template)
        # Insert the templates

        return template


    def config_files_combo_box(self, items):
        """Set dragable combobox"""
        model = QtGui.QStandardItemModel()
        for text in items:
            item = QtGui.QStandardItem(text)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsDropEnabled)
            model.appendRow(item)

        self.widget.files_comboBox.setModel(model)
        self.widget.files_comboBox.view().setDragDropMode(QtGui.QAbstractItemView.InternalMove)

    def save_as_action(self):
        """Saves the plots etc to the defined directory"""

        # Sets the cursor to wait
        self.variables.app.setOverrideCursor(Qt.WaitCursor)

        if self.not_saving:
            # Check if valid dir was given
            directory = self.widget.save_lineEdit.text()
            if os.path.exists(directory) and self.plotting_Object:

                # Save the config.yml file
                self.log.info("Saving config file...")
                self.save_config_yaml(self.plotting_Object.config, os.path.join(os.path.normpath(directory), "CONFIG.yml"))

                # Get save option
                options = self.widget.save_as_comboBox.currentText().split("/")

                plotters = ["html", "png", "svg"]
                data = ["json", "hdf5", "xml"]

                # Start data saver
                for ty in data:
                    if ty in options:
                        self.save_data(ty, directory, os.path.basename(directory))

                # Start renderer
                if self.plotting_Object.config:
                    self.plotting_Object.config["Save_as"] = []
                    self.plotting_Object.config["Output"] = directory
                    for plot in plotters:
                        if plot in options:
                            self.plotting_Object.config["Save_as"].append(plot)
                    if not self.plotting_thread:
                        self.plotting_thread = threading.Thread(target=self.plotting_Object.save_to, args=(
                            self.variables.framework_variables["Message_to_main"],))
                    else:
                        del self.plotting_thread
                        self.plotting_thread = threading.Thread(target=self.plotting_Object.save_to, args=(
                            self.variables.framework_variables["Message_to_main"],))
                    if self.not_saving:
                        self.plotting_thread.start()
                        self.not_saving = False
                    else:
                        self.log.error("Saving of plots is currently ongoing, please wait until saving is complete!")
            else:
                self.log.error("Either the path {} does not exist, or you must first render a few plots".format(directory))
        else:
            if not self.plotting_thread.is_alive():
                self.not_saving = True
                self.save_as_action() # Start it here.

        # Restore Cursor
        self.variables.app.restoreOverrideCursor()

    def get_image_size(self, fname):
        '''Determine the image type of fhandle and return its size.
        from draco'''
        import struct
        import imghdr
        with open(fname, 'rb') as fhandle:
            head = fhandle.read(24)
            if len(head) != 24:
                return
            if imghdr.what(fname) == 'png':
                check = struct.unpack('>i', head[4:8])[0]
                if check != 0x0d0a1a0a:
                    return
                width, height = struct.unpack('>ii', head[16:24])
            elif imghdr.what(fname) == 'gif':
                width, height = struct.unpack('<HH', head[6:10])
            elif imghdr.what(fname) == 'jpeg':
                try:
                    fhandle.seek(0)  # Read 0xff next
                    size = 2
                    ftype = 0
                    while not 0xc0 <= ftype <= 0xcf:
                        fhandle.seek(size, 1)
                        byte = fhandle.read(1)
                        while ord(byte) == 0xff:
                            byte = fhandle.read(1)
                        ftype = ord(byte)
                        size = struct.unpack('>H', fhandle.read(2))[0] - 2
                    # We are at a SOFn block
                    fhandle.seek(1, 1)  # Skip `precision' byte.
                    height, width = struct.unpack('>HH', fhandle.read(4))
                except Exception:  # IGNORE:W0703
                    return
            else:
                return
            return width, height