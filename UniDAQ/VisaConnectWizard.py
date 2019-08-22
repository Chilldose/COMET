import visa
import logging
import threading
from time import sleep

lock = threading.Lock()
llock = logging.getLogger("ThreadLock")


def run_with_lock(method):
    """
    Intended to be used as decorator for functions which need to be threadsave. Warning: all functions acquire the same lock, be carefull.
    """

    def with_lock(*args, **kw):
        try:
            # Try running the method
            with lock:
                llock.debug("Lock acquired by program: " + str(method.__name__))
                result = method(*args, **kw)
            llock.debug("Lock released by program: " + str(method.__name__))
        # raise the exception and print the stack trace
        except Exception as error:
            llock.error("A lock could not be acquired in " + str(method.__name__), exc_info=True)
            # this is optional but sometime the raise does not work
            raise  # this raises the error with stack backtrace
        return result

    return with_lock  # here the memberfunction timed will be called

#Opens a connection to a VISA resource device (GPIB, USB, RS232, IP)
class VisaConnectWizard:
    '''
    This Class is for connecting Rs232, GPIB, IP and USB devices via pyVisa.

    It can be called with an argument, which defines the specific resource you want to connect to.
    Basic Functions are:
    connect_to_instruments(bool) - no argument: connects to all resources, False: lists all resources and let you decide which to connect to
    show_instruments - gathers list of all resources
    show_resources - lists all resources (needs show_instruments first)
    verify_ID(int) - shows ID of int device, no argument, shows all devices ID
    close_connections - closes all open connections
    '''


    # initialization
    def __init__(self,*arg, backend=None):
        """Constructs a new connection manager.

        Keyword arguments:
        - backend -- VISA backend, None for NI driver, '@py' for PyVISA-py or '@sim' for PyVisa-sim
        """

        # constants
        self.myInstruments = [] #contains list of all instruments connected to
        self.choose_default_instrument = False
        self.resource_names = []
        self.myInstruments_dict = {} #contains a dict, in which only the devices are present, which responded to the IDN query value = resourse key = IDN
        self.baud_rate = 57600
        self.xonoff = True
        self.GPIB_interface = None
        self.log = logging.getLogger(__name__)
        self.backend = backend or ''
        # Create resource manager
        self.rm = visa.ResourceManager(self.backend)
        #visa.log_to_screen()

        # Tries to connect to a GPIB interface if possible
        try:
            self.GPIB_interface = self.rm.open_resource('GPIB::INTFC')
            self.reset_interface()
        except:
            self.log.warning("No GPIB interface could be found")


        #Connects to an instrument given in arg (this function will be obsolete if no argument is given)
        try:
            if len(arg)>0:
                self.choose_default_instrument=True
                # Important ----------------------------------------------------------------
                # Opens the Instruments for input and/or output
                self.myInstruments.append(self.rm.open_resource(arg[0]))
                # Important ----------------------------------------------------------------
        except:
            self.connection_error(arg[0])

    def reset_interface(self):
        '''Resets the interfaces'''
        try:
            if self.GPIB_interface:
                self.log.warning("Resetting the interface...")
                self.GPIB_interface.send_ifc()
                self.log.info("Reset of interface was successfull.")
                return True
            else:
                self.log.info("No GPIB interface to reset...")
                return True
        except Exception as e:
            self.log.error("Reset of interface was not successfull. Error: " + str(e))
            return False



    #If connections fails this will be called
    def connection_error(self, failed_resource):
        self.log.error("Attemp to connect to visa resource " + str(failed_resource) + " failed.")


    #Lists all connected resources (no sniff)
    def show_resources(self):
        print(self.myInstruments)

    #Looks for all Instruments in the network and shows them
    def show_instruments(self):
        # Lists all available resources found
        self.log.info("All available visa resources:")
        self.resource_names = self.rm.list_resources()

        if self.resource_names == ():
            self.log.warning("No Visa resources found!")
            return False

        # enumerate and print all resources
        for i, j in enumerate(self.resource_names):
            self.log.info("{} {}".format(i, j))


    def reconnect_to_device(self, device_dict):
        '''This functions reconnects to a device'''
        self.log.info("Try to solve error on device: " + device_dict["Device_name"])
        resource_name = device_dict["Visa_Resource"].resource_name

        # Closing connection to device
        try:
            self.close_connections(device_dict["Visa_Resource"])
        except Exception as err:
            self.log.critical("An error happend while closing device: {}".format(err))

        # Reopening connection to device
        resource = self.rm.open_resource(resource_name)  # Tries opening the connection to a device

        self.config_resource(resource_name, resource, device_dict.get("Baudrate", None))
        IDN = device_dict["Device_IDN"]

        # Query the IDN
        IDN_query = resource.query(device_dict.get("device_IDN_query", "*IDN?"))
        if str(IDN) == str(IDN_query).strip():
            device_dict["Visa_Resource"] = resource
            self.log.info("Connection to the device: " + device_dict["Device_name"] + "is now reestablished")
        else:
            self.log.error("Connection to the device: " + device_dict["Device_name"] + "could not be reestablished")



    def connect_to(self, device, IDN, baudrate = 57600, device_IDN = "*IDN?"):
        '''This function connects to a specific device'''

        try:
            self.log.debug("Try connecting to device: " + self.resource_names[device])
            device_resource = self.rm.open_resource(self.resource_names[device])# Tries opening the connection to a device
            self.myInstruments.append(device_resource)  # If valid, append it to the List, for now
            self.config_resource(self.resource_names[device], device_resource, baudrate)

            if IDN == str(self.verify_ID(len(self.myInstruments)-1, command=device_IDN)).strip(): # So that the last added device will be queried
                self.myInstruments_dict.update({IDN: device_resource})  # Adds the device ID for each instrument into the dict
                self.log.info(str(device_resource) + " => " + IDN.strip("\n"))
                return True # this means success

            else:
                self.log.error("Device IDN for " + str(self.resource_names[device]) + " does not match with IDN from input Device " + str(self.myInstruments[-1]))
                self.log.error(str(IDN) + " != " + str(self.verify_ID(len(self.myInstruments))))
                self.myInstruments.pop()  # removes the item from the list
                return False

        except:
            self.log.error("Attempt to connect to device: " + str(self.resource_names[device]) + " failed.")
            return False


    #Connects to a instrument or all instruments available in the network
    def connect_to_instruments(self, connect_to_all=True, connect_to=[]): # If no args are given it will try to connect to all available resourses
        '''Debricated'''
        if connect_to_all:

            self.show_instruments()  # Lists all resourses

            for instrument in self.resource_names: # Loop over all resoruses
                try:
                    self.rm.open_resource(instrument) # Tries opening the resourse
                    self.myInstruments.append(self.rm.open_resource(instrument)) # If valid, append it to the List
                    self.config_resource(instrument, self.myInstruments[-1]) # Makes a first configuration of the instrument (not for all resource types necessary)
                    #Warning: this are only preset values, they may differ to config files now
                except:
                    self.connection_error(instrument)

        elif connect_to != [] and connect_to_all == False: # Connection type for another case

            for instrument in connect_to:
                try:
                    self.myInstruments.append(self.rm.open_resource(self.resource_names[instrument]))
                    self.config_resource(self.resource_names[instrument], self.myInstruments[-1])
                except:
                    self.connection_error(self.resource_names[instrument])


        else:
            dummy = input("Choose resource from list above: \nTyping -1 will try to connect to all available instruments \n")

            if dummy == -1:


                for instrument in self.resource_names:
                    try:
                        self.myInstruments.append(self.rm.open_resource(instrument))
                        self.config_resource(instrument, self.myInstruments[-1])
                    except:
                        self.connection_error(instrument)

            else:
                try:
                    self.myInstruments.append(self.rm.open_resource(self.resource_names[dummy]))
                    self.config_resource(self.resource_names[dummy], self.myInstruments[-1])
                except:
                    self.connection_error(self.resource_names[dummy])


    def config_resource(self, resources_name, resource, baudrate = 9600): # For different types of connections different configurations can be done
        # ASRL type resourses are RS232 they usually need some additional configuration
        # Furthermore this function is for a primitive configuration, we cannot know by now which device has which configuration. IDN is necessary for that,
        # but we can only ask for IDN if connection is valid.

        if resources_name[:4] == 'ASRL':
            # Additional Parameters for rs232, usually the baudrate is the only configuration needed, pyvisa will do the rest
            resource.baud_rate = int(baudrate)
            #resource.values_format.is_binary = False
            #resource.values_format.datatype = 'd'w e
            #resource.StopBit=visa.constants.StopBits.one
            #resource.Parity=visa.constants.Parity.even
            #resource.SerialTermination=visa.constants.SerialTermination.termination_break
            #resource.write_terminator = visa.constants.SerialTermination.termination_char
            #resource.read_terminator = visa.constants.SerialTermination.termination_char
            resource.xoxoff = self.xonoff
            #resource.write_termination = '\r\n'
            #resource.read_termination = '\r\n'
            #resource.values_format.is_big_endian = False

    #No response function
    def no_response(self, instrument):
        self.log.warning('The device ' + str(instrument) + " is not responing.")


    #Verifing the ID of connected resources typing -1 asks for all id of all resources
    def verify_ID(self, number=-1, command = "*IDN?"):

            if number == -1:

                self.log.info("All IDN of devices:")
                for instrument in self.myInstruments:
                    try:
                        device_IDN = instrument.query(str(command)) #Gets me the IDN for the device
                        self.myInstruments_dict.update({device_IDN: instrument}) # Adds the device ID for each instrument into the dict
                        self.log.info(str(instrument) + " => " + device_IDN.strip("\n"))
                    except:
                        self.no_response(str(instrument))
                        #self.close_connections(instrument) # Closes the connection to the not responding instruments
                return 0


            else:
                try:
                    return self.myInstruments[number].query(str(command))
                except:
                    self.no_response(self.myInstruments[number])
                    return False

    #@run_with_lock # So only one talker and listener can be there
    def query(self, resource_dict, code, reconnect = True):
        """Makes a query to the resource (the same as first write then read)"""
        #Just check if a resource or object was passed and prepare everything
        try:
            resource = resource_dict["Visa_Resource"]
            #reconnect = True # if dict a reconection attempt is possible
        except KeyError:
            self.log.error("Could not access Visa Resource for device: " + str(resource_dict["Device_name"] +
                       ". This usually happens when the device is not connected."))
            return False
        except TypeError:
            resource = resource_dict
        except Exception as e:
            self.log.exception("An unknown error occured while accessing a Visa resource with error {}".format(e))
            return False


        try:
            query = str(resource.query(str(code))) # try to query
            self.log.info("Query of: {} to device: {} was answered with: {}".format(code, resource_dict["Device_name"], query.strip()))
            return query

        except Exception as err:
            # Try to reconnect to the device if no answer comes from the device in the timeout
            self.log.error("The query of device {} with query {} failed with error: {}".format(resource_dict["Device_name"],
                                                                                               code, err))

            if reconnect and type(resource_dict) == dict:
                self.log.warning("Trying to reconnect to device and reset interfaces...")
                self.reset_interface()
                self.reconnect_to_device(resource_dict)
                if "GPIB" not in str(resource): # For all other devices
                    self.write(resource, "\r\n") # tries to reset it this way
                query = self.query(resource_dict["Visa_Resource"], code, reconnect=False)
                if query:
                    self.log.info("Query command: {} to: {} was answered with: {}".format(code, resource_dict["Device_name"], query))
                    return query
                else:
                    self.log.warning("Attempt to reconnect to device was not successful...")
                    return False
            else:
                return False # if no response a -1 will be returned

    #@run_with_lock  # So only one talker and listener can be there
    def write(self, resource_dict, code):
        """Writes a vlaue to a resource, if a list is passed insted of a string all in the list will be send, one after another"""

        if type(resource_dict) == dict: # Checks if dict or only resource
            try:
                resource = resource_dict["Visa_Resource"]
            except KeyError:
                self.log.error("A key error occured in dict " + str(resource_dict["Device_name"] + ". This usually happens when the device is not connected."))
                return False
            except Exception as e:
                self.log.error("An unknown error occured while accessing a Visa resource " + str(e))
                return False
        else:
            resource = resource_dict

        try:
            # Now look if the code is a list or not
            if type(code) == list:
                self.list_write(resource_dict, code, delay = 0)
                return True

            else:
                full_command = str(code)
                resource.write(full_command)
                self.log.info("Write command: " + str(full_command) + " to: " + str(resource))
                return True
        except:
            return False

    #Reads a value from the resource
    def read(self, resource_dict):
        try:
            return resource_dict["Visa_Resource"].read()
        except:
            return False

    #Closes the connection to all active resources and closes the visa resource manager
    def close_connections(self, inst = -1):

        if inst == -1:
            for instrument in self.myInstruments_dict.keys():
                #self.initiate_instrument(self.myInstruments_dict[instrument], ["*rst"])
                self.log.info("Closed connection to device " + str(self.myInstruments_dict[instrument]) + ".")
                self.myInstruments_dict[instrument].clear()
                self.myInstruments_dict[instrument].close()

            self.rm.close()

        else: # Closes the connection to a specific resource
            inst.clear()
            inst.close()
            self.log.info("Closed connection to device " + str(inst) + ".")


    def list_write(self, resource, commands, delay=0.): # Writes initiate commands to the device
        """Writes a list of commands to the device specified. Usually you dont need this function. User the normal
        write function, if you pass a list this function will automatically be called. This way it will also work nested"""
        for command in commands:
            self.write(resource, str(command))
            sleep(delay) #A better way possible but gives the instrument its time


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
