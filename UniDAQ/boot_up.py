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

class loading_init_files:
    '''This class is for loading all config files, pad files and default parameters.
    This class is crucial for the program to work. All works within the init function of this class.
    It generates three new dicts which can be accessed from the class as class attributes

    '''


    def __init__(self):

        self.log = logging.getLogger(__name__)

        # Get project path
        package_dir = os.path.dirname(os.path.realpath(__file__))
        init_dir = os.path.join(package_dir, "config")

        # Get data dirs
        data_dirs = [dirr for dirr in os.listdir(init_dir)]
        if "Setup_configs" in data_dirs: data_dirs.remove("Setup_configs")

        # Get all files in the directories
        # Look for yml files and translate them
        self.configs = {} # Dict for the final "folder" structure
        for data in data_dirs: # Data directories in parent dir
            con_name = data.split("\\")[-1] # How the subdir is called
            self.configs[con_name] = {} # Main name of the config (folder)
            for file in glob.glob(os.path.join(init_dir, data, "*.yml")): # Find all yml files, only yml files are allowed
                self.log.info("Try reading config file: " + str(file))
                new_device_dict = self.create_dictionary(file) # Create a dict out of the config
                if "Settings_name" in new_device_dict: # Looks for the name of the config
                    self.configs[con_name][new_device_dict["Settings_name"]] = new_device_dict # Updates the parent
                elif "Display_name" in new_device_dict: # Looks for the name of the config
                    self.configs[con_name][new_device_dict["Display_name"]] = new_device_dict # Updates the parent
                else:
                    self.log.error("No settings name found for config file: {!s}. File will be ignored.".format(file))

            # Load the pad files, this are the data with txt or dat ending
            subdir = os.path.join(init_dir, data)
            # Subdirectory structure is for project and pad files only
            for pad_dir in [d for d in os.listdir(subdir) if os.path.isdir(os.path.join(subdir, d))]:
                self.configs[con_name][pad_dir] = self.read_pad_files(os.path.join(subdir, pad_dir))

        self.config_device_notation() # Changes the names of the dicts key for the devives, so that they are independet inside the program

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

    def config_device_notation(self):
        '''This function renames the device dict, so that the measurement class has a common name declaration. It wont change the display name. Just for internal consistency purposes'''

        assigned_dicts = []
        new_assigned = self.configs["config"]["settings"].get("Aliases", {}).copy() #  Gets me the internal names of all stated devices in the default file (or the keys) (only for the defaults file)
        devices_d = self.configs.get("device_lib", {}).copy()
        # Searches for devices in the device list, returns false if not found (real device is the value dict of the device
        for device in devices_d:
            if devices_d[device].get("Display_name", "") in new_assigned.values() and devices_d[device].get("Display_name", "") not in assigned_dicts:
                # syntax for changing keys in dictionaries dictionary[new_key] = dictionary.pop(old_key)
                lKey = [key for key, value in new_assigned.items() if value == device][0]
                self.configs["device_lib"][lKey] = self.configs["device_lib"].pop(device)
                assigned_dicts.append(device)
                new_assigned.pop(lKey)

        for missing in new_assigned.values():
            for device in self.configs["device_lib"].copy():
                if missing in self.configs["device_lib"][device].get("Display_name", ""):
                    lKey = [key for key, value in new_assigned.items() if value == missing][0]
                    self.configs["device_lib"][lKey] = self.configs["device_lib"][device]


    def create_dictionary(self, filename="", filepath=""):
        '''Creates a dictionary with all values written in the file using yaml'''

        resource = os.path.join(filepath, filename)
        #self.log.info("Loading file:" + str(filename))
        with open(resource, "r") as fp:
            return yaml.safe_load(fp)


class connect_to_devices:
    '''This class simply handles the connections, generates a dictionary with all devices.
    This can be accessed via self.get_new_device_dict()'''

    def __init__(self, vcw, device_dict):
        """Actually does everythin on its own"""

        self.log = logging.getLogger(__name__)
        self.vcw = vcw
        self.device_dict = device_dict


        self.vcw.show_instruments() # Lists all devices which are connected to the PC

        for device in device_dict.keys():  # device_dict is a dictionary containing dictionaries

            try:
                device_IDN = device_dict[device]["Device_IDN"]  # gets me the IDN for each device loaded
                connection_type = device_dict[device].get("Connection_type", -1) # Gets me the type of the connection
                if "device_IDN_query" in device_dict[device]:
                    IDN_query = device_dict[device]["device_IDN_query"]
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
                        self.log.error("Serial instrument at port " + str(connection_type.split(":")[-1]) + " is not connected.")


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
                    # This maneges the connections for IP devices
                    pass

                # Add other connection types

                else:
                    self.log.info("No valid connection type found for device " + str(device) + ". Therefore no connection established. You may proceed but measurements will fail.")

            except KeyError:
                self.log.error("Device " + device_dict[device]["Display_name"] + " has no IDN.")



        # List all devices
        #vcw.connect_to_instruments() # Tries to connect to all available instruments
        #vcw.verify_ID()              # Tries to query the IDN from each instrument

        self.new_device_dict = self.append_resource_to_device_dict() # Appends the resources to the decice dict

    def get_new_device_dict(self):
        """Returns all connected devices."""
        return self.new_device_dict

    def append_resource_to_device_dict(self): #better way
        '''Appends all valid resources to the dictionaries for the devices'''

        valid_resources =  self.vcw.myInstruments_dict # gets me the dict with the resources which are currently connected

        for device in self.device_dict.keys(): # device_dict is a dictionary containing dictionaries

                device_IDN = "No IDN"

                try:
                    device_IDN = self.device_dict[device]["Device_IDN"] # gets me the IDN for each device loaded
                except KeyError:
                    self.log.error("Device " + self.device_dict[device]["Display_name"] + " has no IDN.")

                resource = valid_resources.get(str(device_IDN).strip(), "Not listed")
                # Some kind of hack, it searches for the device IDN if not found "not listed" is returned

                if resource != "Not listed":
                    self.device_dict[device].update({"Visa_Resource": resource})  # If resource was found with same IDN the resource gets appended to the dict
                    self.log.info("Device " + self.device_dict[device]["Display_name"] + " is assigned to " + str(resource) + " with IDN: " + str(device_IDN).strip())
                elif resource == "Not listed":
                    self.log.error("Device " + self.device_dict[device]["Display_name"] + " could not be found in active resources.")

        return self.device_dict
        # Check if every device dict has its resource added
        #for device in device_dict.keys():
        #    if "Visa_Resource" not in device_dict[device]:
        #        print("No Visa resources listed for device " + device_dict[device]["Display_name"] + ".")


def update_defaults_dict(dict, additional_dict):
        """
        Updates the defaults values dict
        :param dict: the dictionary which will be updated to the default values dict
        """
        if "Settings_name" in additional_dict:
            additional_dict.pop("Settings_name")
        return dict["settings"].update(additional_dict)

