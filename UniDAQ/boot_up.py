#This modules are for boot up purposes.
# -It checks the validity of the installation and installs missing packages on its own
# -Loads the config files for the instrumentds etc.
# -Connects to all system relevant instruments
# -Initialize statistics and state control

import importlib, os, threading, yaml
import logging
import numpy as np
import glob
import sys

from .core.config import Setup
from .core.config import DeviceLib

class SetupLoader(object):
    '''This class is for loading all config files, pad files and default parameters.
    This class is crucial for the program to work. All works within the init function of this class.
    It generates three new dicts which can be accessed from the class as class attributes

    '''

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.configs = {}

    def load(self, name):
        self.configs = {}

        # Get project path
        package_dir = os.path.dirname(os.path.realpath(__file__))
        config_dir = os.path.join(package_dir, "config")
        setup_dir = os.path.join(config_dir, 'Setup_configs', name)
        device_dir = os.path.join(config_dir, 'device_lib')

        if not os.path.isdir(setup_dir):
            raise RuntimeError("No such setup '{}'".format(setup_dir))


        # Todo: look what is correcter here
        # bernhard
        device_lib = DeviceLib()
        device_lib.load(os.path.join(config_dir, 'device_lib'))

        # Get data dirs and device lib
        # Domi
        config_files = glob.glob(os.path.join(setup_dir, "*.yml"))
        device_files = glob.glob(os.path.join(device_dir, "*.yml"))
        config_files.extend(device_files)

        # Todo: Look which is correct
        # Load setup
        # bernhard
        path = os.path.join(setup_dir)
        setup = Setup()
        setup.load(path)
        # TODO HACK attach common device_lib
        setup.device_lib = device_lib.devices
        self.configs = setup


        # Domi
        # Get all files in the directories
        # Look for yml files and translate them
        self.configs = {"config": {}, "device_lib": {}, "additional_files": {}} # Dict for the final "folder" structure
        for data in config_files: # Data directories in parent dir
            name = os.path.basename(data).split(".")[0]
            self.log.info("Try reading config file: {}".format(data))
            new_device_dict = self.create_dictionary(data) # Create a dict out of the config
            if "Settings_name" in new_device_dict: # Looks for the name of the config
                self.configs["config"][new_device_dict["Settings_name"]] = new_device_dict # Updates the parent
            elif "Device_name" in new_device_dict: # Looks for the name of the config
                self.configs["device_lib"][new_device_dict["Device_name"]] = new_device_dict # Updates the parent
            else:
                self.log.error("No settings name found for config file: {!s}. File will be ignored.".format(name))

        # Load additional files, this are the data with txt or dat ending in subfolder
        additional_dirs = [d for d in os.listdir(setup_dir) if os.path.isdir(os.path.join(setup_dir, d))]
        for dir in additional_dirs:
            self.gen_directory_tree(self.configs["additional_files"], os.path.join(setup_dir, dir), self.read_file)

    def gen_directory_tree(self, parent_dict, path, function, pattern="*.txt",):
        """Loads all files (as txt files into the specified directory with key = filename
        function is the object which will be applied to the """
        further_dir = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        parent_dict[os.path.basename(path)] = {}
        parent_dict = parent_dict[os.path.basename(path)]

        for child_path in further_dir:
            self.gen_directory_tree(parent_dict, os.path.join(path, child_path), function, pattern)

        for file in glob.glob(os.path.join(path, pattern)):
            # apply a function to the datafile
            try:
                parent_dict[os.path.basename(file).split(".")[0]] = {}
                # Create a raw data entry, so other parts can parse them as they please
                parent_dict[os.path.basename(file).split(".")[0]]["raw"] = function(file)
            except Exception as err:
                self.log.error("An error occured while applying function {} to path {}".format(str(function), file))

    def read_file(self, path):
        with open(path) as f:
            return f.read()

    def read_pad_files(self, path):
        '''This function reads the pad files and returns a dictionary with the data'''

        # First get list of all pad files in the folder
        all_pad_files = {}
        list_of_files = os.listdir(path)
        header = []
        data = []
        for filename in list_of_files:
            with open(os.path.join(path, filename), "r") as f:
                read_data = f.readlines()

            # first find the header
            for i, lines in enumerate(read_data):
                if "strip" in lines: # Can be done better
                    header = read_data[:i+1]
                    data = read_data[i+1:]
                    break

            # Find the reference pads in the header and strip length
            reference_pad_list = []
            new_param = {}
            for i, lines in enumerate(header):
                if "reference pad" in lines:
                    reference_pad_list.append(int(lines.split(":")[1]))

                # Find additional parameters
                elif ":" in lines:
                    new_param.update({lines.split(":")[0].strip(): lines.split(":")[1].strip()})

            # Now make the data look shiny
            data_list = []
            for lines in data:
                data_list.append([self.confloattry(x) for x in lines.split()])

            final_dict = {"reference_pads" : reference_pad_list, "header": header, "data": data_list}
            final_dict.update({"additional_params": new_param})
            all_pad_files.update({str(filename.split(".")[0]): final_dict})

        return all_pad_files

    def confloattry(self, value):
        """This function trys to convert a string to a float, else string is returned"""

        try:
            return float(value)
        except:
            return value

    def config_device_notation(self, devices):
        '''This function renames the device dict, so that the measurement class has a common name declaration. It wont change the display name. Just for internal consistency purposes'''

        assigned_dicts = []
        new_assigned = self.configs["config"]["settings"].get("Aliases", {}).copy() #  Gets me the internal names of all stated devices in the default file (or the keys) (only for the defaults file)
        # Searches for devices in the device list, returns false if not found (real device is the value dict of the device
        for device in devices.copy():
            if devices[device].get("Device_name", "") in new_assigned.values() and devices[device].get("Device_name", "") not in assigned_dicts:
                # syntax for changing keys in dictionaries dictionary[new_key] = dictionary.pop(old_key)
                lKey = [key for key, value in new_assigned.items() if value == device][0]
                devices[lKey] = devices.pop(device)
                assigned_dicts.append(devices[lKey]["Device_name"])
                new_assigned.pop(lKey)

        # Add missing devices with aliases
        for key, missing in new_assigned.copy().items():
            for devic in devices.copy():
                if missing in devices[devic]["Device_name"]:
                    devices[key] = devices[devic].copy()
                    new_assigned.pop(key)

        if new_assigned:
            self.log.warning("The devices aliases {} have been specified but where never used".format(new_assigned))
        return devices


    def create_dictionary(self, filename="", filepath=""):
        '''Creates a dictionary with all values written in the file using yaml'''

        resource = os.path.join(filepath, filename)
        #self.log.info("Loading file:" + str(filename))
        with open(resource, "r") as fp:
            return yaml.safe_load(fp)


class connect_to_devices:
    '''This class simply handles the connections, generates a dictionary with all devices.
    This can be accessed via self.get_new_device_dict()'''

    def __init__(self, vcw, device_dict, device_lib):
        """

        :param vcw: The connect wizard class
        :param connect_to: A dictionary containing the information how to connect to a device
        :param device_lib: All devices
        """

        self.log = logging.getLogger(__name__)
        self.vcw = vcw
        self.device_dict = device_dict
        self.device_lib = device_lib

        for device in device_dict:  # device_dict is a dictionary containing dictionaries
            # Check if device is present in the device lib
            if device_dict[device]["Device_name"] not in device_lib:
                self.log.error("No additional parameters for device {} found! This may result in further errors".format(device))
            try:
                device_IDN = device_dict[device]["Device_IDN"]  # gets me the IDN for each device loaded
                connection_type = device_dict[device].get("Connection_type", -1) # Gets me the type of the connection
                if "device_IDN_query" in device_lib[device_dict[device]["Device_name"]]:
                    IDN_query = device_lib[device_dict[device]["Device_name"]]["device_IDN_query"]
                else:
                    IDN_query = "*IDN?"
                if "GPIB" in str(connection_type).upper():
                    # This manages the connections for GBIP devices

                    if ("GPIB0::"+str(connection_type.split(":")[-1]) + "::INSTR") in self.vcw.resource_names: # Searches for a match in the resource list
                        success = self.vcw.connect_to(self.vcw.resource_names.index("GPIB0::"+str(connection_type.split(":")[-1]) + "::INSTR"), device_IDN, device_IDN=IDN_query) # Connects to the device Its always ASRL*::INSTR
                        if success:
                            self.log.info("Connection established to device: " + str(device) + " at ")
                        else:
                            self.log.error("Connection could not be established to device: " + str(device))
                    else:
                        self.log.error("GPIB instrument at port " + str(connection_type.split(":")[-1]) + " is not connected.")
                elif "RS232" in str(connection_type).upper():
                    # This maneges the connections for Serial devices
                    if ("ASRL"+str(connection_type.split(":")[-1]) + "::INSTR") in self.vcw.resource_names: # Searches for a match in the resource list
                        #print(self.device_dict[device].get("Baud_rate", 57600))
                        success = self.vcw.connect_to(self.vcw.resource_names.index("ASRL"+str(connection_type.split(":")[-1]) + "::INSTR"), device_IDN, baudrate=self.device_dict[device].get("Baud_rate", 57600), device_IDN=IDN_query) # Connects to the device Its always ASRL*::INSTR
                        if success:
                            self.log.info("Connection established to device: " + str(device) + " at ")
                        else:
                            self.log.error("Connection could not be established to device: " + str(device))
                    else:
                        self.log.error("Serial instrument at port " + str(connection_type.split(":")[-1]) + " is not connected.")
                elif "IP" in str(connection_type).upper():
                    # This manages the connections for IP devices
                    self.log.error("The software is currently not capable of to connect to IP devices!")
                # Add other connection types
                else:
                    self.log.info("No valid connection type found for device " + str(device) + ". "
                                "Therefore no connection established. You may proceed but measurements will fail.")
            except KeyError:
                self.log.error("Device " + device_dict[device]["Device_name"] + " has no IDN.")

        self.new_device_dict = self.append_resource_to_device_dict() # Appends the resources to the device dict



    def get_new_device_dict(self):
        """Returns all connected devices."""
        return self.new_device_dict

    def append_resource_to_device_dict(self):
        '''Appends all valid resources to the dictionaries for the devices'''

        valid_resources =  self.vcw.myInstruments_dict # gets me the dict with the resources which are currently connected
        for device, values in self.device_dict.items(): # device_dict is a dictionary containing dictionaries
                device_IDN = "No IDN"
                try:
                    device_IDN = self.device_dict[device]["Device_IDN"] # gets me the IDN for each device loaded
                except KeyError:
                    self.log.error("Device " + self.device_dict[device]["Device_name"] + " has no IDN.")

                resource = valid_resources.get(str(device_IDN).strip(), "Not listed")

                if resource != "Not listed":
                    self.device_lib[values["Device_name"]].update({"Visa_Resource": resource})  # If resource was found with same IDN the resource gets appended to the dict
                    self.log.info("Device " + self.device_dict[device]["Device_name"] + " is assigned to " + str(resource) + " with IDN: " + str(device_IDN).strip())
                elif resource == "Not listed":
                    self.log.error("Device " + self.device_dict[device]["Device_name"] + " could not be found in active resources.")

                # Append all infos from the config as well
                self.device_lib[values["Device_name"]].update(self.device_dict[device])

        return self.device_lib


def update_defaults_dict(dict, additional_dict):
        """
        Updates the defaults values dict
        :param dict: the dictionary which will be updated to the default values dict
        """
        if "Settings_name" in additional_dict:
            additional_dict.pop("Settings_name")
        return dict["settings"].update(additional_dict)
