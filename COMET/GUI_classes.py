# Warning while using PyQT: PyQt is a wrapper over the C++ code of QT. Therefore errors are handled in the C++ enviroment and may
# not be catched by the python interpret. This alos applies when functions are called by a Qt module like button pressen.
# For real error handling every action which could cause an error, seperate error handler with try/except are recommended.
# For testing an helpfull function was written raise_exception. This function works as decorator and will handle the occuring errors
# Also some kind of stack trace will be shown. Warning: When functions are called by Qt objects make sure that at least two arguments are passed
# or the method will fail. Just add to the function foo(a) a None variable so foo(a, b=None) this will work in most cases


import importlib
import glob
from time import sleep
import pyqtgraph as pq
from PyQt5 import uic
from PyQt5.QtWidgets import *
from .gui.MainWindow import MainWindow
from .gui.PluginWidget import PluginWidget
from .GUI_event_loop import *
import os


QT_UI_DIR = 'QT_Designer_UI'
"""Name of directory containing all plugin UI files."""


class GUI_classes(QWidget):
    # app, message_from_main, message_to_main, devices_dict, default_values_dict, pad_files_dict, visa, queue_to_GUI, table, switching)
    def __init__(self, framework_variables):

        super(GUI_classes, self).__init__()

        #Intialize the QT classes
        self.app = framework_variables["App"]
        self.log = logging.getLogger(__name__)

        # Framework variables
        self.vcw = framework_variables["VCW"]
        self.client = framework_variables["Client"]
        self.server = framework_variables["Server"]
        self.devices_dict = framework_variables["Devices"]
        self.default_values_dict = framework_variables["Configs"]["config"]
        self.table = framework_variables["Table"]
        self.switching = framework_variables["Switching"]
        self.additional_files = framework_variables["Configs"]["additional_files"]
        self.message_to_main = framework_variables["Message_to_main"]
        self.message_from_main = framework_variables["Message_from_main"]
        self.queue_to_GUI = framework_variables["Queue_to_GUI"]
        self.framework_variables = framework_variables
        self.default_values_dict["settings"]["new_data"] = False
        self.default_values_dict["settings"]["Measurement_running"] = False

        # Config response function for the server
        if self.server:
            self.server.responder = self.process_messages_from_Django_server

        # Some Variables
        self.functions = [] # Function for the framework to update

        if "GUI_update_interval" not in self.default_values_dict["settings"]:
            self.variables.default_values_dict["settings"]["GUI_update_interval"] = 200
            self.envlog.warning("No time_format defined, defaulting to 200")
        self.update_interval = float(self.default_values_dict["settings"]["GUI_update_interval"])  # msec

        self.meas_data = {}
        self.all_plugin_modules = {}
        self.qt_designer_ui = []
        self.ui_widgets = {}
        self.final_tabs = []
        self.ui_plugins = {}

        # Load ui plugins
        self.load_GUI_plugins()

        # Measurement data for plotting
        # Data type Dict for what kind of measurement (keys) values are tuple of numpy arrays (x,y)
        # Extend as you please in the config file
        if "measurement_types" in self.default_values_dict["settings"]:
            for measurments in self.default_values_dict["settings"].get("measurement_types",[]):
                self.meas_data.update({measurments: [np.array([]), np.array([])]})
        else:
            self.log.warning("No measurement_types specified, no data storage initiated!")


        # This is the main Tab Widget in which all other tabs are implemented
        self.main_window = MainWindow(self.message_to_main)

        # Base config for all qtgraph plots
        plot_style = QtCore.QSettings().value("plot_style")
        if plot_style == "light":
            pq.setConfigOption('background', 'w')
            pq.setConfigOption('foreground', 'k')
        if plot_style == "dark":
            pq.setConfigOption('background', '#323232')
            pq.setConfigOption('foreground', '#bec4ce')
        else:
            self.log.warning("No plot style selected standard style selected...")

        pq.setConfigOption('antialias', True)
        pq.setConfigOption('crashWarning', True)


        sleep(0.2) # That gives the threads time to initialize all values before missmatch in gui can occur

        # Run plugins and generate a widget for every plugin
        self.construct_ui()

        self.begin_rendering() # Starts the rendering process for all tabs

        # Initialise and start the GUI_event_loop
        self.event_loop_thread = GUI_event_loop(self, self.framework_variables, self.meas_data)
        self.event_loop_thread.Errsig.connect(self.main_window.errMsg.new_message)
        self.event_loop_thread.start()

        self.log.info("Starting GUI ... ")


    def add_rendering_function(self, widget, name):
        '''This function adds a widget for rendering'''
        self.log.debug("Adding rendering function: %s", name)
        self.final_tabs.append((widget, name))


    def construct_ui(self):
        '''This function generates all ui elements in form of tab widgets'''
        for module in self.all_plugin_modules:
            self.log.debug("Constructing UI module: {!s}".format(module))
            # Create plugin widget
            widget = PluginWidget()
            layout = QGridLayout()  # Just a layout type
            widget.setLayout(layout)

            # Here the init function of all UI python plugins will be called
            try:
                plugin = getattr(self.all_plugin_modules[module], module)(self, layout)
                self.ui_plugins.update({module: plugin})

                # Add the ui to the renderer
                self.add_rendering_function(widget, module.split("_")[0])
            except AttributeError as err:
                self.log.error("The Module {} for the GUI app generation could not be found. Error: {}".format(module, err))

    def load_QtUi_file(self, filename, widget):
        '''This function returns a qt generated Ui object.'''
        package_dir = os.path.normpath(os.path.dirname(__file__))
        qtCreatorFile = os.path.join(package_dir, QT_UI_DIR, filename)
        Ui_Window, QtBaseClass = uic.loadUiType(qtCreatorFile)
        return self.add_QtUi_to_window(Ui_Window, widget)

    def add_QtUi_to_window(self, Qt_ui_class, widget):
        '''This function just adds a qt generated Ui (python file needed)'''
        UI = Qt_ui_class()
        UI.setupUi(widget)
        return UI

    def load_GUI_plugins(self):
        def locate_modules(pattern):
            """Returns list of modules names.
            >>> locate_modules("/path/to/*.py")
            ['foo', 'bar', 'baz']
            """
            modules = []
            for filename in glob.glob(pattern):
                module = os.path.basename(os.path.splitext(filename)[0])
                if module not in ("__init__", "__pycache__"):
                    modules.append(module)
            return modules

        # Load all measurement functions
        #install_directory = os.getcwd() # Obtain the install path of this module
        package_dir = os.path.normpath(os.path.dirname(__file__))
        self.ui_classes = locate_modules(os.path.join(package_dir, 'ui_plugins', '*.py'))
        self.qt_designer_ui = locate_modules(os.path.join(package_dir, QT_UI_DIR, '*.ui'))

        self.log.debug("Located %s Ui classes:", len(self.ui_classes))
        for module in self.ui_classes:
            self.log.debug(module)
        self.log.debug("Located %s Qt Ui objects:", len(self.qt_designer_ui))
        for module in self.qt_designer_ui:
            self.log.debug(module)

        if "GUI_render_order" in self.default_values_dict["settings"]:
            for modules in self.default_values_dict["settings"]["GUI_render_order"]:  # import all modules from all files in the plugins folder
                if modules+"_window" in self.ui_classes:
                    self.all_plugin_modules.update({modules+"_window": importlib.import_module("COMET.ui_plugins." + str(modules+"_window"))})
                else:
                    self.log.error("The GUI element {} was specified but could not be found as resource!".format(modules+"_window"))
        else:
            self.log.error("No GUI_render_order defined, no GUI can be rendered!")
    def updateWidget(self, widget):
        '''This function updates the QApplication'''
        widget.repaint()
        self.log.debug("Updating widgets...")

    def begin_rendering(self):

        self.log.debug("Starting rendering main window...")

        if "GUI_render_order" in self.default_values_dict["settings"]: # Renders taps in specific order
            for elements in self.default_values_dict["settings"]["GUI_render_order"]:
                for ui_obj in self.final_tabs: # Not very pretty
                    if elements in ui_obj:
                        self.log.debug("Adding UI module to widget: {!s}".format(elements))
                        self.main_window.addTab(ui_obj[0], ui_obj[1])  # elements consits of a tupel object, first is the ui object the second the name of the tab

        else: # If no order is implied, also renders all plugins found
            for ui_obj in self.final_tabs:
                self.main_window.addTab(ui_obj[0], ui_obj[1]) #elements consits of a tupel object, first is the ui object the second the name of the tab

        # Show me what you goooot!!!!
        self.main_window.show()
        self.main_window.raise_()

    def add_update_function(self, func): # This function adds function objects to a list which will later on be executed by updated periodically
        self.functions.append(func)
        self.log.debug("Added framework function: " + str(func))

    def give_framework_functions(self):
        return self.functions, self.update_interval

    def reset_plot_data(self):
        """Simply resets all plots"""
        self.log.debug("Resetting Plots...")
        for data in self.meas_data: # resets the plot data when new measurement is conducted
            # called by e.g. the start button
            self.meas_data[data][0] = np.array([])
            self.meas_data[data][1] = np.array([])

        self.default_values_dict["settings"]["new_data"] = True


    # Todo: Not sure if this is the correct place ot place the server_client_thing
    def send_plot_data(self, measurement="all"):
        """This function sends the data for a specified measurement over a socket connection
        If 'all' is stated then all data will be send."""
        if measurement != "all":
            if measurement in self.meas_data:
                return {measurement: [x.tolist() for x in self.meas_data[measurement]]}
            else:
                return "Measurement {} was not recognised".format(measurement)
        if measurement == "all":
            return self.meas_data

        else:
            return "Measurement {} was not recognised".format(measurement)

    def process_messages_from_Django_server(self, action, value):
        """Processes the message recieved by a Django server. Message which cannot be interpreted will be protocoled"""

        if action == "plot_data":
            # If plot data should be send
            return self.send_plot_data(value["Plot"])

        if action == "get_plot_types":
            return self.meas_data.keys()

        else:
            return "Action {} was not recognised.".format(action)

