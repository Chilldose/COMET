# This starts the event loop for conducting measurements

import Queue
from utilities import *
from measurements import *
import threading
import numpy as np
from time import sleep
import pyqtgraph as pg
from VisaConnectWizard import *
import logging
l = logging.getLogger(__name__)

# Defining the Queue Objects for data sharing need to be here, than the main knows them to!!!
message_to_main = Queue.Queue()
message_from_main = Queue.Queue()
queue_to_GUI = Queue.Queue()



class measurement_event_loop:
    ''' This class is for starting and managing the event loop fro the measurements. It starts the syncronised connection betweent ifself and the
        GUI event loop. Message based on dictionaries. '''


    def __init__(self, device_dict, settings, pad_files, visa_connect, table, switching, shell):
        ''' Here all initializations can be done. '''

        #Getting the Queue objects for safe data exchange
        self.message_to_main = message_to_main
        self.message_from_main = message_from_main
        self.queue_to_GUI = queue_to_GUI
        self.shell = shell

        # Generall state control of the measurement setup
        self.humidity_history = []
        self.temperatur_history = []
        self.dry_air_on = "unknown"
        self.measurement_running = False
        self.alignment = False
        self.stop_measurement = False
        self.stop_measurement_loop = False
        self.measurements_to_conduct = {}
        self.status_query = {}
        self.status_requests = ["CLOSE", "GET_STATUS", "ABORT_MEASUREMENT", "MEASUREMENT_FINISHED"]
        self.update_time = 50 # Milli Seconds
        self.order_types = ["Measurement", "Status", "Remeasure", "Alignment", "Sweep"]
        self.events = {}
        self.default_dict = settings #defaults_dict
        self.pad_files = pad_files
        self.vcw = visa_connect
        self.table = table
        self.switching = switching
        self.skip_init = False

        # Devices possible
        self.devices = device_dict

        # Init devices
        sleep(1)
        self.init_devices()

        self.shell.add_cmd_command(self.init_devices)

        # Start Continuous measurements like temphum control
        #self.data_from_continous_measurements = Queue.Queue() # Creates a queue object for the data transfer
        if "temphum_controller" in self.devices:
            self.measthread = newThread(2, "Temperatur and humidity control", self.temperatur_and_humidity, self.message_to_main, self.devices["temphum_controller"], self.devices["temphum_controller"]["enviroment_query"], self.default_dict["Defaults"]["temphum_update_intervall"])
            self.measthread.start() # Starts the thread

        # Create the measurement object
        #self.measurements = measurement_class(self.message_to_main)

        # This starts the loop to get the messages from the main thread
        self.start_loop()

        # Reinitalize all devices when shutting down
        self.init_devices()

        l.info("Stoped measurement event loop")
        self.message_to_main.put({"MEASUREMENT_EVENT_LOOP_STOPED": True})




    def start_loop(self):
        ''' This function actually starts the event loop. '''
        l.info("Measurement event loop started.")
        while not self.stop_measurement_loop or self.measurement_running:

            message = message_from_main.get() # This function waits until a message is received from the main!
            # Message must be a dict {str Type: {Orders}}

            self.translate_message(message) # This translates the message get from the main
            self.process_message() # Here the message will be processed
            self.process_pending_events() # If errors or other things happened while processing the messages


    def translate_message(self, message):
        '''This function converts the message to a measurement list which can be processed'''
        try:
                if message.has_key(self.order_types[0]): # So if Measurments should be conducted
                    try:
                        self.measurements_to_conduct.update(message[self.order_types[0]]) # Assign the dict for the measurements
                    except:
                        l.error("Data type error while translating message for measurement event loop")
                        self.events.update({"DataError": "Data type error while translating message for measurement event loop"})

                elif message.has_key(self.order_types[1]): # Status
                    try:
                        self.status_query.update(message[self.order_types[1]])
                    except:
                        l.error("Data type error while translating message for measurement event loop")
                        self.events.update({"DataError": "Data type error while translating message for measurement event loop"})

                else:
                    l.error("Wrong order delivered to measurement event loop. Order: " + "\"" + str(message) + "\"")
                    self.events.update({"DataError": "Wrong order delivered to measurement event loop. Order: " + "\"" + str(message) + "\""})


        except:
            l.error("Wrong order delivered to measurement event loop. Order: " + "\"" + str(message)+ "\"")
            self.events.update({"DataError": "Wrong order delivered to measurement event loop. Order: " + "\"" + str(message)+ "\""})

    def process_message(self):
        '''This function will do some actions in case of a valid new operation'''


        # All things which has something to do with the measurements----------------------------------------------------
        #---------------------------------------------------------------------------------------------------------------
        if self.measurements_to_conduct != {} and not self.measurement_running: # If the dict is not empty and no measurement is running

            if "stripscan" in self.measurements_to_conduct and not self.default_dict["Defaults"]["Alignment"]:  # if not only IV or CV should be done
                self.events.update({"MeasError": "Alignement is missing! "})
                self.measurements_to_conduct.clear()

            if self.measurements_to_conduct:
                self.measurement_running = True # Prevents new that new measurement jobs are generated
                self.stop_measurement = False
                self.skip_init = self.measurements_to_conduct.get("skip_init", False)
                self.events.update({"MEASUREMENT_STATUS": self.measurement_running})  # That the GUI knows that a Measuremnt is running
                self.default_dict["Defaults"]["Measurement_running"] = True
                if not self.skip_init:
                    self.init_devices() # Initiates the device anew (defined state)
                measthread = newThread(3, "Conduct measurement", measurement_class, self, self.default_dict, self.pad_files, self.devices, self.message_to_main, self.message_from_main,  self.measurements_to_conduct.copy(), self.queue_to_GUI, self.table, self.switching, self.ask_to_stop) # Starts a thread for measuring
                measthread.start()
                l.info("Sended new measurement job. Orders: " + str(self.measurements_to_conduct))
                self.measurements_to_conduct.clear() # Clears the measurement dict

        if self.measurements_to_conduct != {} and self.measurement_running:
            l.warning("Tried making a new measurement. Measurement is running, no new job generation is possible.")
            self.events.update({"MeasError": "Tried making a new measurement. Measurement is running, no new job generation possible."})
            self.measurements_to_conduct.clear()


    def process_pending_events(self):
        '''This function sends all occured events back to the main'''


        #All things which has something to do with status of the thread ------------------------------------------------
        #---------------------------------------------------------------------------------------------------------------
        if self.status_query != {}:
            # Here all actions are processed which can occur in the status query request

            if self.status_query.has_key("CLOSE"): # Searches for a key and take actions, like closing all threads
                self.stop_measurement = True # Sets flag
                self.stop_measurement_loop = True # Bug: measurement_loop closes while the measurement thread proceed till it has finished it current task and then shuts down
                # TODO: Done? wait until the measurement has shut down and than proceed
                if self.measurement_running:
                    self.events.update({"MEASUREMENT_STATUS": self.measurement_running})
                    self.stop_measurement_loop = False
                else:
                    self.events.update({"Shutdown": True})

                l.info("Closing all measurements and shutdown program.")

            elif self.status_query.has_key("MEASUREMENT_FINISHED"): # This comes from the measurement class
                self.measurement_running = False # Now new measurements can be conducted
                self.stop_measurement = False
                if not self.skip_init:
                    self.init_devices()
                self.events.update({"MEASUREMENT_STATUS": self.measurement_running})
                self.default_dict["Defaults"]["Measurement_running"] = False

            elif self.status_query.has_key("MEASUREMENT_STATUS"): # Usually asked from the main to get status
                self.events.update({"MEASUREMENT_STATUS": self.measurement_running})

            elif self.status_query.has_key("ABORT_MEASUREMENT"): # Ask if Measuremnt should be aborted
                self.stop_measurement = True  # Sets flag, but does not check

            else:
                l.warning("Status request not recognised " + str(self.status_query))
                self.events.update({"RequestError": "Status request not recognised " + str(self.status_query)})

        self.message_to_main.put(self.events.copy())  #
        self.events.clear()  # Clears the dict so that new events can be written in
        self.status_query.clear()#Clears the status query Dict


    def temperatur_and_humidity(self, queue_to_main, resource, query, update_intervall = 5000):
        '''This starts the background and continuous tasks like humidity and temperature control'''

        resource = resource
        query = query
        update_intervall = float(update_intervall)
        queue_to_main = queue_to_main

        # First try if visa_resource is valid
        success = False
        try:
            first_try = vcw.query(resource["Visa_Resource"], query)
            if first_try:
                success = True

        except Exception, e:
            l.error("The temperature and humidity controller seems not to be responding. Error:" + str(e))

        #@hf.run_with_lock
        def update_environement():
            '''This is the update function for temp hum query'''
            if not self.stop_measurement_loop:
                try:
                    values = vcw.query(resource["Visa_Resource"], query)
                    values = values.split(",")
                    self.humidity_history.append(float(values[1])) #todo: memory leak since no values will be deleted
                    self.temperatur_history.append(float(values[0]))
                    # Write the pt100 and light status and environement in the box to the global variables
                    self.default_dict["Defaults"]["chuck_temperature"] =  float(values[3])
                    self.default_dict["Defaults"]["internal_lights"] = True if int(values[2]) == 1 else False
                    queue_to_main.put({"temperature": [float(time.time()), float(values[0])], "humidity": [float(time.time()), float(values[1])]})
                except:
                    l.error("The temperature and humidity controller seems not to be responding.")
                threading.Timer(update_intervall/1000., update_environement).start() # This ensures the function will be called again

        if success:
            update_environement()

            l.info("Humidity and temp control started...")
        else:
            l.info("Humidity and temp control NOT started...")


    def init_devices(self, args=None):
        '''This function makes the necessary configuration for all devices before any measurement can be conducted'''
        # Not very pretty
        self.message_to_main.put({"Info": "Initializing of instruments..."})

        #sended_commands = [] #list over all sendet commands, to prevent double sending
        for device in self.devices: # Loop over all devices
            sended_commands = []  # list over all sended commands, to prevent double sending
            if self.devices[device].has_key("Visa_Resource"): # Looks if a Visa resource is assigned to the device.

                # Initiate the instrument and resets it
                if "reset_device" in self.devices[device]:
                    self.vcw.initiate_instrument(self.devices[device]["Visa_Resource"], self.devices[device]["reset_device"], self.devices[device].get("execution_terminator", ""))
                else:
                    self.vcw.initiate_instrument(self.devices[device]["Visa_Resource"], ["*rst", "*cls"], self.devices[device].get("execution_terminator", ""))

                # Search for important commands which need to be sendet first
                for keys in self.devices[device]: # Looks up every key in the device
                    if "imp:" in keys: # Looks if a important default value is defined somewhere

                        command = self.devices[device].get("set_" + keys.split("_", 1)[1], "no value")  # gets the command to set the desired default value, or if not defined returns no value
                        command = command.strip()  # Strips whitespaces from the string

                        if command == "no value":
                            l.warning("Default value " + keys.split("_", 1)[1] + " defined for " + device + " but no command for setting this value is defined")

                        elif command != "no value" and command not in sended_commands:
                            sended_commands.append(command)

                            full_command = self.build_init_command(command, self.devices[device][keys], self.devices[device].get("command_order", 1))

                            for command in full_command:
                                self.vcw.write(self.devices[device]["Visa_Resource"], command, self.devices[device].get("execution_terminator",""))  # Writes the command to the device
                                sleep(0.05)  # Waits a bit for the device to config itself

                            l.info("Device " + self.devices[device]["Display_name"] + str(command) + " to " + str(self.devices[device][keys]) + ".")

        # Change the state of the device to Configured

                # Send all other commands
                for keys in self.devices[device]:  # Looks up every key in the device
                    if "default_" in keys: # Looks if a default value is defined somewhere

                        command = self.devices[device].get("set_" + keys.split("_", 1)[1], "no value") # gets the command to set the desired default value, or if not defined returns no value
                        command = command.strip() # Strips whitespaces from the string

                        if command == "no value":
                            l.warning("Default value " + keys.split("_", 1)[1] + " defined for " + device + " but no command for setting this value is defined")

                        elif command != "no value" and command not in sended_commands:
                            sended_commands.append(command)
                            full_command = self.build_init_command(command, self.devices[device][keys], self.devices[device].get("command_order", 1))

                            for command in full_command:
                                self.vcw.write(self.devices[device]["Visa_Resource"], command, self.devices[device].get("execution_terminator", "")) # Writes the command to the device
                                sleep(0.05)  # Waits a bit for the device to config itself

                            l.info("Device " + self.devices[device]["Display_name"] + " " + str(command) + " to " + str(self.devices[device][keys]) + ".")

        self.message_to_main.put({"Info": "Initializing DONE!"})


    def build_init_command(self, order, values, command_order = 1):
        '''This function builds the correct orders together, it always returns a list, if a order needs to be sended several times with different values
        It difffers to the normal build command function, it takes, exactly the string or list and sends it as it is.'''
        if type(values) != list: # ensures we have a list
            values_list = [values]
        else:
            values_list = values

        full_command_list = []
        if int(command_order) == 1:
            for item in values_list:
                full_command_list.append(str(order)+ " " + str(item).strip())
            return full_command_list

        elif int(command_order) == -1:
            for item in values_list:
                full_command_list.append(str(item) + " " + str(order))
            return full_command_list

        else:
            l.error("Something went wrong with the building of the init command!")

    def ask_to_stop(self): # Just a simple return function if a measurement should be stopped
        return self.stop_measurement

    #def load_measurement_plugins(self):
    #    '''Loads the measurments plugins from a folder'''
