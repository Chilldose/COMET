# Warning while using PyQT: PyQt is a wrapper over the C++ code of QT. Therefore errors are handled in the C++ enviroment and may
# not be catched by the python interpret. This alos applies when functions are called by a Qt module like button pressen.
# For real error handling every action which could cause an error, seperate error handler with try/except are recommended.
# For testing an helpfull function was written raise_exception. This function works as decorator and will handle the occuring errors
# Also some kind of stack trace will be shown. Warning: When functions are called by Qt objects make sure that at least two arguments are passed
# or the method will fail. Just add to the function foo(a) a None variable so foo(a, b=None) this will work in most cases


import importlib
import os.path as osp
import sys
from time import sleep

import pyqtgraph as pq
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from GUI_event_loop import *
from bad_strip_detection import *
from utilities import newThread, measurement_job_generation

l = logging.getLogger(__name__)

hf = help_functions()

class GUI_classes(GUI_event_loop, QWidget):

    def __init__(self, message_from_main, message_to_main, devices_dict, default_values_dict, pad_files_dict, help, visa, queue_to_GUI, table, switching, shell):

        #Intialize the QT classes
        self.app = QApplication(sys.argv)

        # Set Style of the GUI
        style = "Fusion"
        self.app.setStyle(QStyleFactory.create(style))

        # Some Variables
        self.help = help
        self.message_to_main = message_to_main
        self.message_from_main = message_from_main
        self.vcw = visa
        self.devices_dict = devices_dict
        self.default_values_dict = default_values_dict
        self.pad_files_dict = pad_files_dict
        self.functions = []
        self.update_interval = float(self.default_values_dict["Defaults"].get("GUI_update_interval", 100.))  # msec
        self.queue_to_GUI = queue_to_GUI
        self.table = table
        self.switching = switching
        self.job = measurement_job_generation(self.default_values_dict, self.message_from_main)
        self.white_plots = default_values_dict["Defaults"].get("Thomas_mode", False)
        self.meas_data = {}
        self.all_plugin_modules = {}
        self.qt_designer_ui = []
        self.ui_widgets = {}
        self.final_tabs = []
        self.ui_plugins = {}
        self.shell = shell
        self.analysis = stripanalysis(self) # Not very good it is a loop condition

        # Load ui plugins
        self.load_plugins()

        # Measurement data for plotting
        # Data type Dict for what kind of measurement (keys) values are tupel of numpy arrays (x,y)
        # Extend as you please in the init file
        for measurments in self.default_values_dict["Defaults"]["measurement_types"]:
            self.meas_data.update({measurments: [np.array([]), np.array([])]})


        # This is the main Tab Widget in which all other tabs are implemented
        self.QTabWidget_obj = QTabWidget()
        self.QTabWidget_obj.setWindowFlags(Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint) # Only minimize and maximize button are active
        self.QTabWidget_obj.resize(1900, 1000) # in pixels

        # Initialise and start the GUI_event_loop
        event_loop_thread = newThread(2, "GUI_event_loop", GUI_event_loop.__init__, self, self, self.message_from_main, self.message_to_main, self.devices_dict, self.default_values_dict, self.pad_files_dict, self.help, self.vcw, self.meas_data)
        event_loop_thread.start()

        # For Thomas, because he does not like black plots
        if self.white_plots:
            pq.setConfigOption('background', 'w')
            pq.setConfigOption('foreground', 'k')

        sleep(0.2) # That gives the threads time to initialize all values before missmatch in gui can occur

        # Run plugins and generate a widget for every plugin
        self.construct_ui()

        self.begin_rendering() # Starts the rendering process for all tabs

        self.add_update_function(self.process_pending_events)

        # Add the cmd options
        self.shell.add_cmd_command(self.reset_plot_data)
        self.shell.add_cmd_command(self.give_framework_functions)

        l.info("Starting GUI ... ")

    def add_rendering_function(self, widget, name):
        '''This function adds a widget for rendering'''
        self.final_tabs.append((widget,str(name)))

    def construct_ui(self):
        '''This function generates all ui elements in form of tab widgets'''

        for modules in self.all_plugin_modules:
            # QWidget object
            QWidgets = QWidget()
            layout = QGridLayout()  # Just a layout type
            QWidgets.setLayout(layout)

            plugin = getattr(self.all_plugin_modules[modules], str(modules))(self, layout)
            self.ui_plugins.update({modules: plugin})

            self.add_rendering_function(QWidgets, str(modules).split("_")[0])

    def load_QtUi_file(self, Qt_ui_file, widget):
        '''This function just adds a qt generated Ui (ui file needed)'''
        qtCreatorFile = os.path.abspath(str(Qt_ui_file))
        Ui_Window, QtBaseClass = uic.loadUiType(qtCreatorFile)
        UI = self.add_QtUi_to_window(Ui_Window, widget)
        return UI

    def add_QtUi_to_window(self, Qt_ui_class, widget):
        '''This function just adds a qt generated Ui (python file needed)'''
        UI = Qt_ui_class()
        UI.setupUi(widget)
        return UI

    def load_plugins(self):
        # Load all measurement functions
        #install_directory = os.getcwd() # Obtain the install path of this module
        self.ui_classes = os.listdir(os.path.normpath("modules/ui_plugins/"))
        self.ui_classes = list(set([modules.split(".")[0] for modules in self.ui_classes]))

        self.qt_designer_ui = os.listdir(os.path.normpath("modules/QT_Designer_UI"))
        self.qt_designer_ui = list(set([modules.split(".")[0] for modules in self.qt_designer_ui]))

        l.info("All Ui classes found: " + str(self.ui_classes) + ".")
        l.info("All Qt Ui objects found: " + str(self.qt_designer_ui) + ".")


        for modules in self.ui_classes:  # import all modules from all files in the plugins folder
            if "__init__" not in modules:
                self.all_plugin_modules.update({modules: importlib.import_module("modules.ui_plugins." + str(modules))})


    def updateWidget(self, widget):
        '''This function updates the QApplication'''
        widget.repaint()

    def begin_rendering(self):

        if "GUI_render_order" in self.default_values_dict["Defaults"]: # Renders taps in specific order
            for elements in self.default_values_dict["Defaults"]["GUI_render_order"]:
                for ui_obj in self.final_tabs: # Not very pretty
                    if elements in ui_obj:
                        self.QTabWidget_obj.addTab(ui_obj[0], ui_obj[1])  # elements consits of a tupel object, first is the ui object the second the name of the tab

        else: # If no order is implied, also renders all plugins found
            for ui_obj in self.final_tabs:
                self.QTabWidget_obj.addTab(ui_obj[0], ui_obj[1]) #elements consits of a tupel object, first is the ui object the second the name of the tab
        # Add tabs (for better understanding)
        #self.QTabWidget_obj.addTab(self.QWidget_Maintab, "Main")

        # Appearence of the window
        self.QTabWidget_obj.setWindowTitle('SenTestSoftCMS - STSC')

        # setting the path variable for icon
        path = osp.join(osp.dirname(sys.modules[__name__].__file__), 'images/logo.png')
        self.QTabWidget_obj.setWindowIcon(QIcon(path))

        # Show me what you goooot!!!!
        self.QTabWidget_obj.show()

    def add_update_function(self, func): # This function adds function objects to a list which will later on be executed by updated periodically
        self.functions.append(func)

    def give_framework_functions(self, args=None):
        return self.functions, self.update_interval

    def reset_plot_data(self, args=None):

        for data in self.meas_data: # resets the plot data when new measurement is conducted (called by the start button)
            self.meas_data[data][0] = np.array([])
            self.meas_data[data][1] = np.array([])

        self.default_values_dict["Defaults"]["new_data"] = True

        # This functions need to be called in case that no clear statement is set during plotting
        #for plot in self.plots:
            #plot.clear()

    def error_pop_up(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(message)
        msg.setWindowTitle("Really bad error occured")
        msg.exec_()

class MyWin(QMainWindow):
    def __init__(self, parent=None):
        super(MyWin, self).__init__(parent)
        self.setWindowTitle("My Window")
        self.setWindowIcon(QtGui.QIcon('logo.png'))
        self.show()
