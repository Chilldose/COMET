import pyvisa as visa
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
            llock.error(
                "A lock could not be acquired in " + str(method.__name__), exc_info=True
            )
            # this is optional but sometime the raise does not work
            raise  # this raises the error with stack backtrace
        return result

    return with_lock  # here the member function timed will be called


# Opens a connection to a VISA resource device (GPIB, USB, RS232, IP)
class VisaConnectWizard:
    """
    This Class is for connecting RS232, GPIB, IP and USB devices via pyVisa.

    It can be called with arguments, which defines the specific resource you want to connect to.

    With the kwarg 'backend' you can define the backend. '\@py' uses the pyvisa-py backend or '\@sim' for PyVisa-sim,
    if you pass nothing the standard pyvisa with the NI-Visa bindings will be used.
    """

    # initialization
    def __init__(self, *arg, backend=None):
        """Constructs a new connection manager.

        Keyword arguments:
        - backend -- VISA backend, None for NI driver, '@py' for PyVISA-py or '@sim' for PyVisa-sim
        """

        # constants
        self.myInstruments = (
            []
        )  # contains list of all instruments connected to within this instance
        self.choose_default_instrument = False
        self.resource_names = []
        self.myInstruments_dict = (
            {}
        )  # contains a dict, in which only the devices are present, which responded to the IDN query value = resourse key = IDN
        self.GPIB_interface = None
        self.log = logging.getLogger(__name__)
        self.backend = backend or ""
        # Create resource manager
        self.rm = visa.ResourceManager(self.backend)
        # visa.log_to_screen()

        # Tries to connect to a GPIB interface if possible
        try:
            self.GPIB_interface = self.rm.open_resource("GPIB::INTFC")
            self.reset_GBIP_interface()
        except:
            self.log.debug("No GPIB interface could be found...")

        # Connects to an instrument given in arg (this function will be obsolete if no argument is given)
        try:
            if len(arg) > 0:
                self.choose_default_instrument = True
                # Important ----------------------------------------------------------------
                # Opens the Instruments for input and/or output
                self.myInstruments.append(self.rm.open_resource(arg[0]))
                # Important ----------------------------------------------------------------
        except:
            self.log.error(
                "Attempt to connect to visa resource " + str(arg[0]) + " failed.",
                exc_info=True,
            )

    def reset_GBIP_interface(self):
        """Resets the GPIB interface, if none is present nothing will happen, but a log will be written"""
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
            self.log.error("Reset of interface was not successfull.", exc_info=True)
            return False

    # Lists all connected resources (no sniff)
    def show_resources(self):
        """This function shows you all available resources currently connected to this machine.
        Warning: This resources must not be correctly configured and working. This is just the list
        the script as attached itself to!"""
        print(self.myInstruments)

    def get_connected_resources(self):
        """Returns all connected resources to this instance of VCW"""
        return self.myInstruments_dict

    # Looks for all Instruments in the network and shows them
    def search_for_instruments(self):
        """This function will search for instruments available to the machine and list them"""
        # Lists all available resources found
        self.log.info("All available visa resources:")
        self.resource_names = self.rm.list_resources()

        if self.resource_names == ():
            self.log.warning("No Visa resources found!")
            return False

        # enumerate and print all resources
        for i, j in enumerate(self.resource_names):
            self.log.info("{} {}".format(i, j))

    def reconnect_to_device(self, device_dict, resource_name=None):
        """
        This functions reconnects to a device

        :param device_dict: a device_dict object, containing the visa resource
        :param resource_name: If you have a specific VISA resource name present for this connection. E.g. if you changed something and want it know different connected
        :return: None
        """
        self.log.info("Try to reconnect to device: " + device_dict["Device_name"])
        if not resource_name and device_dict["Visa_Resource"]:
            try:
                resource_name = device_dict["Visa_Resource"].resource_name
            except visa.InvalidSession:
                resource_name = None

        if not resource_name:
            self.log.error("No valid resource name passed to reconnect to...")
            return

        # Closing connection to device
        try:
            self.close_connections(device_dict["Visa_Resource"])
        except Exception as err:
            self.log.critical(
                "An error happened while closing device: {}. This can happend if no resource was defined".format(
                    err
                )
            )

        # Change the state
        device_dict["State"] = "NOT CONNECTED"

        # Reopening connection to device
        try:
            resource = self.rm.open_resource(
                resource_name
            )  # Tries opening the connection to a device
        except visa.VisaIOError:
            try:
                resource = self.rm.get_instrument(
                    resource_name
                )  # If the connection was extablished before but failed somehow, usually this happens with socket connections
            except visa.VisaIOError as err:
                device_dict["State"] = "NOT CONNECTED"
                device_dict["Visa_Resource"] = None
                self.log.error(
                    "VISA resource {} could not be found in active resource or the connection attempt failed.".format(
                        resource_name
                    ),
                    exc_info=True,
                )
                return

        self.config_resource(resource, **device_dict.get("VISA_attributes", {}))
        IDN = device_dict["Device_IDN"]

        # Query the IDN
        try:
            IDN_query = resource.query(device_dict.get("device_IDN_query", "*IDN?"))
            if str(IDN) == str(IDN_query).strip():
                device_dict["Visa_Resource"] = resource
                device_dict["State"] = "CONNECTED"
                self.log.info(
                    "Connection to the device: "
                    + device_dict["Device_name"]
                    + "is now reestablished"
                )
            else:
                device_dict["State"] = "NOT CONNECTED"
                device_dict["Visa_Resource"] = None
                self.log.error(
                    "Connection to the device: "
                    + device_dict["Device_name"]
                    + "could not be reestablished , due to IDN query mismatch. Responded IDN was: '{}'".format(
                        str(IDN_query).strip()
                    )
                )
        except Exception as err:
            self.log.error(
                "Could not query device {}, if this error persists, please restart software...",
                exc_info=True,
            )

    def connect_to(self, device, IDN, device_IDN_query, **attributes):
        """
        This function connects to a specific device

        :param device: The Visa resource name like TCPIP0::192.168.130.131::inst0::INSTR etc.
        :param IDN: The identification string of the device
        :param device_IDN: The IDN query string (default: *IDN?)
        :return: resource or False
        """

        device_IDN_query = "*IDN?" if device_IDN_query == None else device_IDN_query
        try:
            self.log.debug("Try connecting to device: " + device)
            device_resource = self.rm.open_resource(
                device
            )  # Tries opening the connection to a device
            self.config_resource(device_resource, **attributes)
            self.myInstruments.append(
                device_resource
            )  # If valid, append it to the List, for now

            # Query the IDN from the device and match it with the it value
            if IDN:
                device_idn_return = str(
                    self.verify_ID(device_resource, command=device_IDN_query)
                ).strip()
                if IDN == device_idn_return:
                    self.myInstruments_dict.update(
                        {IDN: device_resource}
                    )  # Adds the device ID for each instrument into the dict
                    self.log.debug(
                        "Successfully connected to device {}".format(device_resource)
                    )
                    return device_resource  # this means success

                elif IDN in device_idn_return:
                    self.log.warning(
                        "Device output queue for device {} not empty but IDN string seems to be included. Wiping queue and retry...".format(
                            device_resource
                        )
                    )
                    device_idn_return = str(
                        self.verify_ID(device_resource, command=device_IDN_query)
                    ).strip()
                    if IDN == device_idn_return:
                        self.myInstruments_dict.update(
                            {IDN: device_resource}
                        )  # Adds the device ID for each instrument into the dict
                        self.log.debug(
                            "Successfully connected to device {}".format(
                                device_resource
                            )
                        )
                        return device_resource  # this means success

                if device_idn_return == "False":
                    self.log.error(
                        "Connection error happened during IDN query... Connection could not be established to device {}".format(
                            device_resource
                        )
                    )

                else:
                    self.log.error(
                        "Could not connect to device {} IDN string mismatch. Devices IDN return :'{}', does not match"
                        "the IDN '{}' this device should have.".format(
                            device_resource, device_idn_return, IDN
                        )
                    )
                    self.myInstruments.pop().close()  # removes the item from the list
                    return False
            else:
                self.log.warning(
                    "No IDN specified, for device {}, connection established but no checks performed.".format(
                        device_resource
                    )
                )
                return device_resource

        except Exception as err:
            self.log.error(
                "Attempt to connect to device: " + str(device) + " failed.",
                exc_info=True,
            )
            return False

    def config_resource(
        self, resource, **attributes
    ):  # For different types of connections different configurations can be done
        """
        Configs the resource for correct usage. Currently only RS232 devices are configured with this.
        All other devices config them self.

        :param resource: The resource object
        :param **attributes: VISA resource kwargs the device needs to be configured with (they must be VISA Attributes)
        :return: None
        """

        for att, value in attributes.items():
            try:
                setattr(resource, att, value)
            except AttributeError:
                self.log.error(
                    "Could not set VISA attribute {} due to an attribute error. Is the attribute valid?".format(
                        att
                    ),
                    exc_info=True,
                )
            except Exception as err:
                self.log.error(
                    "Could not set VISA attribute {}".format(att), exc_info=True
                )

    # Verifing the ID of connected resources typing -1 asks for all id of all resources
    def verify_ID(self, resource, command="*IDN?"):
        """
            Prints all IDN of all devices connected to this machine

            :param resource: the visa resource
            :param command: The IDN query
            :return: False or None
            """
        try:
            return resource.query(str(command))
        except TimeoutError:
            self.log.warning("The device " + str(resource) + " is not responding.")
            return False
        except Exception as err:
            self.log.warning("The device {} raised an error: {}".format(resource, err))
            return False

    def query(self, resource_dict, code, reconnect=True):
        """
        Makes a query to the resource (the same as first write then read)

        :param resource_dict: The device resource object (with the commands)
        :param code: The string to write to the device
        :param reconnect: If a timeout happens, if you want to reconnect
        :return: Response (str) or False
        """
        # Just check if a resource or object was passed and prepare everything
        try:
            resource = resource_dict["Visa_Resource"]
            # reconnect = True # if dict a reconection attempt is possible
        except KeyError:
            self.log.error(
                "Could not access Visa Resource for device: "
                + str(
                    resource_dict["Device_name"]
                    + ". This usually happens when the device is not connected."
                ),
                exc_info=True,
            )
            return False
        except TypeError:
            resource = resource_dict
        except Exception as e:
            self.log.exception(
                "An unknown error occured while accessing a Visa resource with error {}".format(
                    e
                )
            )
            return False

        try:
            query = str(resource.query(str(code)))  # try to query
            self.log.debug(
                "Query of: {} to device: {} was answered with: {}".format(
                    code, resource_dict["Device_name"], query.strip()
                )
            )
            return query

        except Exception as err:
            # Try to reconnect to the device if no answer comes from the device in the timeout
            self.log.error(
                "The query of device {} with query {} failed. ".format(
                    resource_dict["Device_name"], code
                ),
                exc_info=True,
            )

            if reconnect and type(resource_dict) == dict:
                self.log.warning(
                    "Trying to reconnect to device and reset interfaces..."
                )
                self.reset_GBIP_interface()
                self.reconnect_to_device(resource_dict)
                if "GPIB" not in str(resource):  # For all other devices
                    self.write(resource, "\r\n")  # tries to reset it this way
                query = self.query(
                    resource_dict["Visa_Resource"], code, reconnect=False
                )
                if query:
                    self.log.info(
                        "Query command: {} to: {} was answered with: {}".format(
                            code, resource_dict["Device_name"], query
                        )
                    )
                    return query
                else:
                    self.log.warning(
                        "Attempt to reconnect to device was not successful..."
                    )
                    return False
            else:
                return False  # if no response a -1 will be returned

    # @run_with_lock  # So only one talker and listener can be there
    def write(self, resource_dict, code):
        """
        Writes a value to a resource, if a list is passed instead of a string all in the list will be send, one after another

        :param resource_dict: The device resource object (with the commands)
        :param code: The string to write to the device
        :return: bool
        """

        if type(resource_dict) == dict:  # Checks if dict or only resource
            try:
                resource = resource_dict["Visa_Resource"]
            except KeyError:
                self.log.error(
                    "A key error occured in dict "
                    + str(
                        resource_dict["Device_name"]
                        + ". This usually happens when the device is not connected."
                    ),
                    exc_info=True,
                )
                return False
            except Exception as e:
                self.log.error(
                    "An unknown error occured while accessing a Visa resource "
                    + str(e),
                    exc_info=True,
                )
                return False
        else:
            resource = resource_dict

        try:
            # Now look if the code is a list or not
            if type(code) == list:
                self.list_write(resource_dict, code, delay=0)
                return True

            else:
                full_command = str(code)
                resource.write(full_command)
                self.log.debug(
                    "Write command: " + str(full_command) + " to: " + str(resource)
                )

                # Check if a read is necessary for the device
                if resource_dict.get("requires_read_on_set", False):
                    answer = self.read(resource_dict)
                    self.log.debug(
                        "Device {} with acc after write, answered with {}".format(
                            resource, answer.strip()
                        )
                    )
                return True
        except:
            return False

    # Reads a value from the resource
    def read(self, resource_dict):
        """
        Reads from a device

        :param resource_dict: The device resource object (with the commands)
        :return: Response (str) or False
        """
        try:
            return resource_dict["Visa_Resource"].read()
        except:
            return False

    # Closes the connection to all active resources and closes the visa resource manager
    def close_connections(self, inst=-1):
        """
        Closes the connection to a device

        :param inst: Either the visa device to close or -1 (default) for all devices
        :return: None
        """

        if inst == -1:
            for instrument in self.myInstruments_dict.keys():
                # self.initiate_instrument(self.myInstruments_dict[instrument], ["*RST"])
                self.log.info(
                    "Closed connection to device "
                    + str(self.myInstruments_dict[instrument])
                    + "."
                )
                self.myInstruments_dict[instrument].clear()
                self.myInstruments_dict[instrument].close()

            self.rm.close()

        else:  # Closes the connection to a specific resource
            inst.clear()
            inst.close()
            self.log.info("Closed connection to device " + str(inst) + ".")

    def list_write(
        self, resource, commands, delay=0.0
    ):  # Writes initiate commands to the device
        """
        Writes a list of commands to the device specified. Usually you dont need this function. User the normal
        write function, if you pass a list this function will automatically be called. This way it will also work nested

        :param resource: The device resource dictionary
        :param commands: A list of commands to write
        :param delay: A delay between the commands
        :return: None
        """
        for command in commands:
            self.write(resource, str(command))
            sleep(delay)  # A better way possible but gives the instrument its time
