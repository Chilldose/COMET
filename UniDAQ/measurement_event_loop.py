# This starts the event loop for conducting measurements

# Python2 compatible import for package queue
try: import queue
except ImportError: import Queue as queue

from .utilities import *
from .measurements import *
from .VisaConnectWizard import *
import logging
from threading import Thread
from .globals import message_to_main, message_from_main, queue_to_GUI


class measurement_event_loop(Thread):
    ''' This class is for starting and managing the event loop fro the measurements. It starts the syncronised connection betweent ifself and the
        GUI event loop. Message based on dictionaries. '''


    def __init__(self, framework_modules):
        ''' Here all initializations can be done. '''

        Thread.__init__(self)
        #Getting the queue objects for safe data exchange
        self.message_to_main = message_to_main
        self.message_from_main = message_from_main
        self.queue_to_GUI = queue_to_GUI
        self.log = logging.getLogger(__name__)

        # Generall state control of the measurement setup
        self.framework = framework_modules
        self.humidity_history = []
        self.temperatur_history = []
        self.dry_air_on = "unknown"
        self.measurement_running = False
        self.stop_measurement = False
        self.stop_measurement_loop = False
        self.measurements_to_conduct = {}
        self.status_query = {}
        self.status_requests = ["CLOSE", "GET_STATUS", "ABORT_MEASUREMENT", "MEASUREMENT_FINISHED"]
        self.update_time = 50 # Milli Seconds
        self.order_types = ["Measurement", "Status", "Remeasure", "Alignment", "Sweep"]
        self.events = {}
        self.default_dict = framework_modules["Configs"]["config"]["settings"] #defaults_dict
        self.vcw = framework_modules["VCW"]
        self.skip_init = False
        self.devices = framework_modules["Devices"]
        self.temphum_plugin = None

    def run(self):
        # Init devices
        self.init_devices()

        # Start Continuous measurements temphum control
        if "temphum_controller" in self.devices:
            self.load_temphum_plugin(self.framework["Configs"]
                                    ["config"]["settings"].get("temphum_plugin", "NoPlugin"))
            self.temphumhread = getattr(self.temphum_plugin, self.framework["Configs"]
                                        ["config"]["settings"].get("temphum_plugin", "NoPlugin"))\
                                        (self, self.framework, self.framework["Configs"]
                                    ["config"]["settings"].get("temphum_update_intervall:", 5000))
            self.temphumhread.start() # Starts the thread

        # This starts the loop to get the messages from the main thread
        self.start_loop()

        # Reinitalize all devices when shutting down
        self.init_devices()

        self.log.info("Stoped measurement event loop")
        self.message_to_main.put({"MEASUREMENT_EVENT_LOOP_STOPED": True})


    def start_loop(self):
        ''' This function actually starts the event loop. '''
        self.log.info("Measurement event loop started.")
        while not self.stop_measurement_loop or self.measurement_running:

            message = message_from_main.get() # This function waits until a message is received from the main!
            # Message must be a dict {str Type: {Orders}}

            self.translate_message(message) # This translates the message got from the main
            self.process_message() # Here the message will be processed
            self.process_pending_events() # If errors or other things happened while processing the messages


    def translate_message(self, message):
        '''This function converts the message to a measurement list which can be processed'''
        try:
                if self.order_types[0] in message: # So if Measurments should be conducted
                    try:
                        self.measurements_to_conduct.update(message[self.order_types[0]]) # Assign the dict for the measurements
                    except:
                        self.log.error("Data type error while translating message for measurement event loop")

                elif self.order_types[1] in message: # Status
                    try:
                        self.status_query.update(message[self.order_types[1]])
                    except:
                        self.log.error("Data type error while translating message for measurement event loop")
                else:
                    self.log.error("Wrong order delivered to measurement event loop. Order: " + "\"" + str(message) + "\"")
        except Exception as err:
            self.log.error("An unknown error occcured while translating the message: {} with error {}".format(message, err))

    def process_message(self):
        '''This function will do some actions in case of a valid new operation'''

        # All things which has something to do with the measurements----------------------------------------------------
        #---------------------------------------------------------------------------------------------------------------
        if self.measurements_to_conduct != {} and not self.measurement_running: # If the dict is not empty and no measurement is running
            if any(x in self.default_dict["measurement_order"] for x in list(self.measurements_to_conduct.keys())):
                self.measurement_running = True # Prevents new that new measurement jobs are generated
                self.default_dict["Measurement_running"] = True
                self.stop_measurement = False
                self.skip_init = self.measurements_to_conduct.get("skip_init", False)
                self.events.update({"MEASUREMENT_STATUS": self.measurement_running})  # That the GUI knows that a Measuremnt is running

                if not self.skip_init:
                    self.init_devices() # Initiates the device anew (defined state)
                # Starts a thread for measuring
                measthread = measurement_class(self, self.framework, self.measurements_to_conduct.copy())
                measthread.start()
                self.log.info("Sended new measurement job. Orders: " + str(self.measurements_to_conduct))
                self.measurements_to_conduct.clear() # Clears the measurement dict

        if self.measurements_to_conduct != {} and self.measurement_running:
            self.log.error("Tried making a new measurement. Measurement is running, no new job generation possible.")
            self.measurements_to_conduct.clear()


    def process_pending_events(self):
        '''This function sends all occured events back to the main'''


        #All things which has something to do with status of the thread ------------------------------------------------
        #---------------------------------------------------------------------------------------------------------------
        if self.status_query != {}:
            # Here all actions are processed which can occur in the status query request

            if "CLOSE" in self.status_query: # Searches for a key and take actions, like closing all threads
                self.stop_measurement = True # Sets flag
                self.stop_measurement_loop = True # Bug: measurement_loop closes while the measurement thread proceed till it has finished it current task and then shuts down
                if self.measurement_running:
                    self.events.update({"MEASUREMENT_STATUS": self.measurement_running})
                    self.stop_measurement_loop = False
                else:
                    self.events.update({"Shutdown": True})
                self.log.info("Closing all measurements and shutdown program.")

            elif "MEASUREMENT_FINISHED" in self.status_query: # This comes from the measurement class
                self.measurement_running = False # Now new measurements can be conducted
                self.stop_measurement = False
                if not self.skip_init:
                    self.init_devices()
                self.events.update({"MEASUREMENT_STATUS": self.measurement_running})
                self.default_dict["Measurement_running"] = False

            elif "MEASUREMENT_STATUS" in self.status_query: # Usually asked from the main to get status
                self.events.update({"MEASUREMENT_STATUS": self.measurement_running})

            elif "ABORT_MEASUREMENT" in self.status_query: # Ask if Measurement should be aborted
                self.stop_measurement = True  # Sets flag, but does not check

            else:
                self.log.error("Status request not recognised " + str(self.status_query))

        self.message_to_main.put(self.events.copy())  #
        self.events.clear()  # Clears the dict so that new events can be written in
        self.status_query.clear() #Clears the status query Dict

    def init_devices(self):
        '''This function makes the necessary configuration for all devices before any measurement can be conducted'''
        # Not very pretty
        self.message_to_main.put({"Info": "Initializing of instruments..."})

        for device, device_obj in self.devices.items(): # Loop over all devices
            if "Visa_Resource" in self.devices[device]: # Looks if a Visa resource is assigned to the device.
                self.log.info("Resetting instrument: {!s}".format(self.devices[device].get("Device_name", "NoName")))

                # Sends the resets commands to the device
                if "reset_device" in device_obj:
                    self.vcw.write(device_obj, list(self.devices[device]["reset_device"]))
                else:
                    self.vcw.list_write(device, ["*rst", "*cls"], delay=0.1)

                # Beginn sending commands from te reset list
                if "reset" in device_obj:
                    for comm in device_obj["reset"]:
                        command, values = list(comm.items())[0]
                        command_list = self.build_init_command(device_obj, command, values)
                        self.vcw.list_write(device_obj, command_list, delay=0.05)


        self.message_to_main.put({"Info": "Initializing DONE!"})


    def build_init_command(self, device_obj, order, values):
        '''This function builds the correct orders together, it always returns a list, if a order needs to be sended several times with different values
        It differs to the normal build command function, it takes, exactly the string or list and sends it as it is.'''
        if type(values) != list: # ensures we have a list
            values_list = [values]
        else:
            values_list = values

        full_command_list = []
        if "set_" + order in device_obj:
            for item in values_list:
                    command = device_obj["set_" + order]
                    try:
                        full_command_list.append(command.format(str(item).strip()))
                    except Exception as err:
                        self.log.error("An error happend while constructing init command"
                                       " for device {device}. Attempted build was {command} and value {value}"
                                       " with error: {error}".format(device=device_obj["Device_name"],
                                                                     command=command, value=item, error=err))
        else:
            self.log.error("Could not find set command for reset parameter:"
                               " {} in device {}".format(order, device_obj["Device_name"]))
        return full_command_list

    def ask_to_stop(self): # Just a simple return function if a measurement should be stopped
        return self.stop_measurement

    #def load_measurement_plugins(self):
    #    '''Loads the measurments plugins from a folder'''

    def load_temphum_plugin(self, plugin_name):
        # Loads the temperature and humidity plugin
        all_measurement_functions = os.listdir(os.path.join(self.framework["rootdir"], "measurement_plugins"))
        all_measurement_functions = list(set([modules.split(".")[0] for modules in all_measurement_functions]))

        try:
            if plugin_name in all_measurement_functions:
                self.temphum_plugin = importlib.import_module("UniDAQ.measurement_plugins." + plugin_name)
                self.log.info("Imported module: {}".format(plugin_name))
                return self.temphum_plugin
            else:
                self.log.error("Could not load temperature and humidity control module: {}. "
                               "It was specified in the settings but"
                                " no module matches this name.".format(plugin_name))
                return None
        except Exception as err:
            self.log.error("An error happend while importing module: {}. "
                           "With error: ".format(plugin_name, err))
            return None

