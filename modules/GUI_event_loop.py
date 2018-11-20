# This starts the event loop for the GUI
#from GUI_classes import *
import logging

import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import QCoreApplication

l = logging.getLogger(__name__)


class GUI_event_loop:
    ''' This class is for starting and managing the event loop for the GUI. It starts the syncronised connection betweent ifself and the
        measurement event loop. Message based on dictionaries. '''

    def __init__(self, main, message_from_main, message_to_main, devices_dict, default_values_dict, pad_files_dict, help, visa, meas_data):

        # Initialise the GUI class, classes
        #GUI_classes.__init__(self)

        self.main = main
        self.message_to_main = message_to_main
        self.message_from_main = message_from_main
        self.vcw = visa
        self.device_dict = devices_dict
        self.default_values_dict = default_values_dict
        self.pad_files_dict = pad_files_dict
        self.stop_GUI_loop = False
        self.close_program = False
        self.measurement_running = False
        self.measurement_loop_running = True
        self.error_types = ["Info","MeasError", "DataError", "RequestError", "MEASUREMENT_FAILED", "Warning", "FatalError", "ThresholdError"]
        #self.measurement_types = ["IV", "IV_longterm", "CV", "R_int", "I_strip", "I_diel", "R_poly", "C_ac", "I_strip_overhang", "C_int", "I_dark", "humidity", "temperature", "Cback", "Cback_scan", "Cac_scan", "Cint_scan"]
        self.measurement_types = self.default_values_dict["Defaults"]["measurement_types"]
        self.event_types = ["MEASUREMENT_FINISHED", "CLOSE_PROGRAM", "ABORT_MEASUREMENT", "START_MEASUREMENT", "MEASUREMENT_EVENT_LOOP_STOPED"]
        self.error_list = []
        self.measurement_list = []
        self.event_list = [] # Messages send to the loop
        self.pending_events = {} # Messages which should processed after all other orders are processed
        self.help = help
        self.error_log = []

        # Plot data
        #self.IV_data = np.array([])
        #self.IV_longterm_data = np.array([])
        self.meas_data = meas_data # This is a dict with keys like "IV" rtc and than [np.array, np.array] for x,y

        # Start additional timer for pending events, so that the GUI can shutdown properly
        timer = QtCore.QTimer()
        timer.timeout.connect(self.process_pending_events)
        timer.start(1000)

        # Start the event loop
        self.start_loop()



    def start_loop(self):
        ''' This function actually starts the event loop. '''
        while not self.stop_GUI_loop:
            message = self.message_to_main.get()  # This function waits until a message is received from the measurement loop!

            self.translate_message(message)  # This translates the message
            self.process_message(message)  # Here the message will be processed
            self.process_pending_events()  # Here all events during message work will be send or done

    def translate_message(self, message):
        '''This function converts the message to a measurement list which can be processed'''

        # A measurement message is a Dict of a Dict {SignalMessage: {Orders}, ...}
        # Other messages like errors or data from the measurement event loop can be simple dicts like {IV: value} etc..
        message_key_set = set(message.keys())

        # Create list of all errors in the message Dict
        self.error_list = list(set(self.error_types).intersection(message_key_set))

        # Create list of all measurements which are send (data from measurement loop)
        self.measurement_list = list(set(self.measurement_types).intersection(message_key_set))

        # Create list of all events which are send (also all from the gui like measurements orders)
        self.event_list = list(set(self.event_types).intersection(message_key_set))



    def process_message(self, message):
        '''This function will do some actions in case of a valid new operation'''

        # Show all errors which has occured in a message box
        for error in self.error_list:
            prepend = ""
            if "INFO" in error.upper():
                prepend = '<font color=\"green\">'
            elif "ERROR" in error.upper():
                prepend = '<font color=\"red\">'
            elif "WARNING" in error.upper():
                prepend = '<font color=\"orange\">'
            self.error_log.append(prepend + str(error).upper() + ": " + str(message[str(error)]) + "</font> <br/>")

            # If a fatal error occurs a pop up should be displayed TODO:make the error pop up working
            if error.upper() == "FATALERROR":
                #thread.start_new_thread(self.main.error_pop_up, (str(message[str(error)]),))
                #self.main.error_pop_up(str(message[str(error)]))
                pass # TODO: make warning pop up work



        for event in self.event_list: #besser if "dfdf" in self.events oder? TODO vlt hier die abfrage der events anders machen

            if event == "START_MEASUREMENT":
                if not self.measurement_running:
                    #self.measurement_running = True # If a measurement is running the loop will send and MeasError in which this value will be correted
                    self.message_from_main.put({"Measurement": message.get["START_MEASUREMENT", {}]})
                else:
                    self.message_to_main.put({"MeasError": True})

            elif event == "ABORT_MEASUREMENT":
                self.message_from_main.put({"Status": {"ABORT_MEASUREMENT": True}})

            elif event == "CLOSE_PROGRAM":

                if not self.measurement_running: #Prevents closing the program if a measurement is currently running
                    order = {"Status": {"CLOSE": True}}
                    self.close_program = True
                    self.message_from_main.put(order)
                else:
                    self.pending_events.update({"MeasRunning": True}) # message to user if measurement is running

            elif event == "MEASUREMENT_FINISHED": # Message from the event loop when measurement ist finished
                self.measurement_running = False

            elif event == "MEASUREMENT_EVENT_LOOP_STOPED": # Signals that the event loop has stoped which means that the main gui loop needs to be stoped
                self.measurement_loop_running = False      # This will be processed in the pending event function


            # Handles all data for coming from the measurements
        for measurement in self.measurement_list:

            self.default_values_dict["Defaults"]["new_data"] = True  # Initiates the update of the plots
            self.default_values_dict["Defaults"]["last_plot_update"] = self.default_values_dict["Defaults"]["update_counter"]

            # Correctly write the data to the arrays for plotting
            if measurement in self.default_values_dict["Defaults"]["measurement_types"]:
                if type(message[measurement][0]) is not list:
                    self.meas_data[measurement][0] = np.append(self.meas_data[measurement][0], message[measurement][0])
                    self.meas_data[measurement][1] = np.append(self.meas_data[measurement][1], message[measurement][1])
                else:
                    self.meas_data[measurement][0] = message[measurement][0]
                    self.meas_data[measurement][1] = message[measurement][1]

            else:
                l.error("Measurement " + str(measurement) + " could not be found in active data arrays. Data discarded.")
                print "Measurement " + str(measurement) + " could not be found in active data arrays. Data discarded."


    def process_pending_events(self):
        '''This function sends all occured events to the measurement loop and does some cleaning in the program'''

        if not self.measurement_loop_running and not self.measurement_running and self.close_program:
            # This if checks if the program should be closed
            l.info("Exiting GUI event loop")
            self.stop_GUI_loop = True # Stops the event loop

            QCoreApplication.instance().quit() # Stops the GUI
            l.info("Exiting GUI")


        #This function checks if updates of plots has been made and sets the variable back to False, so that no unnessesary plotting is done
        #Will be called as last update function
        if self.default_values_dict["Defaults"]["new_data"] and (self.default_values_dict["Defaults"]["update_counter"] > self.default_values_dict["Defaults"]["last_plot_update"]):
            self.default_values_dict["Defaults"]["last_plot_update"] = self.default_values_dict["Defaults"]["update_counter"]
            self.default_values_dict["Defaults"]["new_data"] = False

        self.default_values_dict["Defaults"]["update_counter"] += 1


