#This class provides usefull functions for gernerall purposes

import os, sys, os.path, re
#sys.path.append(os.path.join( os.path.dirname(__file__), '..',))
from time import sleep, time
import time
import threading
import traceback
import yaml
import logging.config
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QDialog, QPushButton
import numpy as np
from numpy.linalg import inv
import datetime
import pyqtgraph as pg
import logging
from .engineering_notation import EngUnit
import json
import pandas as pd
from threading import Thread
import queue
from .globals import message_to_main, message_from_main, queue_to_GUI
#from __future__ import print_function # Needed for the rtd functions that its written in 3

l = logging.getLogger("utilities")
lock = threading.Lock()

def raise_exception(method):
    """
    Intended to be used as decorator for pyQt functions in the case that errors are not correctly passed to the python interpret
    """

    def raise_ex(*args, **kw):
        try:
            # Try running the method
            result = method(*args, **kw)
        # raise the exception and print the stack trace
        except Exception as error:
            l.error("Some error occured in the function {}. With Error: {}".format(method.__name__,error))  # this is optional but sometime the raise does not work
            raise  # this raises the error with stack backtrack
        return result

    return raise_ex  # here the memberfunction timed will be called

    # This function works as a decorator to raise errors if python interpretor does not do that automatically

class ErrorMessageBoxHandler:
    """This class shows an error message to the user which then can be quit"""

    def __init__(self, message=None, title="COMET encountered an Error", QiD=None):
        """
        If you pass a message to the init only this message will be shown. To accumulate several messages to prevent
        message spamming use the function new_message within the instance
        :param message:
        """
        self.last_message_time = time.time()
        self.message_buffer = ""
        self.timeout = 0.1 # seconds
        self.title = title
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.show_messages)
        self.error_dialog = QtWidgets.QErrorMessage(QiD)
        self.error_dialog.setModal(False)
        self.error_dialog.setWindowTitle(title)
        self.error_dialog.setGeometry((1920-450)/2, (1080-250)/2, 450, 250)
        self.start = time.time()

        if message:
            self.message_buffer = message
            self.show_messages()

    def new_message(self, message):
        """Adds a new message"""
        self.message_buffer += str(message) + "\n"
        display_message = True if (time.time()-self.last_message_time) >= self.timeout else False
        self.last_message_time = time.time()
        if display_message:
            self.show_messages()
        else:
            self.timer.start(int(self.timeout*1000))

    def show_messages(self):
        """Simply shows all messages"""
        #message = "".join(self.message_buffer)
        self.error_dialog.showMessage(self.message_buffer)
        self.error_dialog.activateWindow()
        self.message_buffer = ""

class QueueEmitHandler(logging.Handler):
    def __init__(self, queue):
        self.queue = eval(queue)
        self.level = 0
        self.log_LEVELS = {"NOTSET": 0, "DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        logging.Handler.__init__(self)

    def emit(self, record):
        if record.levelno >= self.level:
            msg = None
            if record.levelno == self.log_LEVELS["ERROR"]:
                msg = {"Error": record.message}
            elif record.levelno == self.log_LEVELS["CRITICAL"]:
                msg = {"CRITICAL": record.message}
            elif record.levelno == self.log_LEVELS["WARNING"]:
                msg = {"WARNING": record.message}
            if msg:
                self.queue.put(msg)

    def setLevel(self, level):
        """Warning this set level works different to the logging levels from the logging modules
        It only loggs the specific level!!!"""
        self.level = level

def exception_handler(exctype, value, tb):
    """Custom exception handler raising a dialog box.

    Example:
    >>> import sys
    >>> sys.excepthook = exception_handler
    """
    if exctype is not KeyboardInterrupt:
        tr = QtCore.QCoreApplication.translate
        # Prepare pretty stacktrace
        message = os.linesep.join(traceback.format_tb(tb))
        QtWidgets.QMessageBox.critical(None,
            tr("QMessageBox", "Uncaught exception occured"),
            tr("QMessageBox",
               "Exception type: {}\n"
               "Exception value: {}\n"
               "Traceback: {}").format(exctype.__name__, value, message)
        )
    # Pass on exception
    sys.__excepthook__(exctype, value, tb)

def get_available_setups(location):
    """Return list of available setups names (resembling setup directory names).
    A valid setup must provide at least the following file tree:

    <setup>/
      config/
        settings.yml

    Example:
    >>> get_available_setups('./config/setups')
    ['Bad Strip Analysis', 'QTC']
    """
    available = []
    for path in os.listdir(location):
        path = os.path.join(location, path)
        if os.path.isdir(path):
            # sanity check, contains a config/settings.yml file?
            if os.path.isfile(os.path.join(path, 'settings.yml')):
                available.append(os.path.basename(path))
    return available

def write_init_file( name, data, path = ""):
        """
        This function writes config files for devices and default files

        :param name: Name of the file to be written to
        :param data: Data in Dict format
        :param path: Path where to write
        :return:
        """

        # find the resource and exclude it from the file
        data = data.copy()

        #Removes the Visa resource if needed
        try:
            data.remove("Visa_Resource")
        except:
            pass

        if os.path.isfile(os.path.abspath(str(path) + str(name.split(".")[0]) + ".yaml")):

            os.remove(os.path.abspath(path + str(name.split(".")[0]) + ".yaml"))
            filename, version = create_new_file(str(name.split(".")[0]), path, os_file=False, suffix=".yaml")
            yaml.dump(data, filename, indent=4)
            close_file(filename)

        elif not os.path.isfile(os.path.abspath(path + str(name.split(".")[0]) + ".yaml")):

            #directory = path[:len(path) - len(path.split("/")[-1])]

            filename, version = create_new_file(str(name.split(".")[0]), path, os_file=False, suffix=".yaml")

            yaml.dump(data, filename, indent=4)

            close_file(filename)


            # Debricated
            #for items in data.items():
            #    if type(items[1]) != type([]):
            #        string = str(items[0]) + " = \"" + str(items[1]) + "\"\n"
            #        os.write(filename, str(string))
            #    else:
            #        string = str(items[0]) + " = \""
            #        for i in items[1]:
            #            string += str(i).strip("'").strip("[").strip("]") + ","
            #        string = string[:-1]
            #        string += "\"\n"
            #        print string
            #        os.write(filename, string)



        else:
            return -1

    # This function works as a decorator to measure the time of function to execute

def timeit( method):
        """
        Intended to be used as decorator for functions. It returns the time needed for the function to run

        :param method: method to be timed
        :return: time needed by method
        """

        def timed(*args, **kw):
            start_time = time.time()
            result = method(*args, **kw)
            end_time = time.time()

            exce_time = end_time-start_time

            return result, exce_time

        return timed # here the memberfunction timed will be called

    # These functions are for reading and writing to files------------------------------------
    #-----------------------------------------------------------------------------------------

    # This function works as a decorator to raise errors if python interpretor does not do that automatically



def run_with_lock( method):
        """
        Intended to be used as decorator for functions which need to be threadsave. Warning: all functions acquire the same lock, be carefull.


        """
        def with_lock(*args, **kw):
            try:
                # Try running the method
                with lock:
                    l.debug("Lock acquired by program: " + str(method.__name__))
                    result = method(*args, **kw)
                l.debug("Lock released by program: " + str(method.__name__))
            # raise the exception and print the stack trace
            except Exception as error:
                l.error("A lock could not be acquired in "  + str(method.__name__) +". With Error:", repr(error)) # this is optional but sometime the raise does not work
                raise  # this raises the error with stack backtrace
            return result

        return with_lock  # here the memberfunction timed will be called

    # Creates a new file

def create_new_file( filename="default.txt", filepath = "default_path", os_file=True, suffix = ".txt"):
        """
        Simply creates a file

        :param filename:
        :param filepath:
        :param os_file:
        :param suffix:
        :return: filepointer, fileversion
        """

        count = 1
        if filepath == "default_path":
            filepath = ""
        elif filepath == "":
            pass
        else:
            filepath += "/"

        filename = filename.split(".")[0]

        #First check if Filename already exists, if so, add a counter to the file.
        if os.path.isfile(os.path.abspath(filepath+filename+suffix)):
            l.warning("Warning filename " + str(filename) + " already exists!")
            filename = filename + "_" + str(count) # Adds suffix to filename
            while os.path.isfile(os.path.abspath(filepath+filename+suffix)):  # checks if file exists
                count += 1
                countlen = len(str(count))
                filename = filename[:-countlen] + str(count)
            l.info("Filename changed to " + filename + ".")

        filename += str(suffix)
        if os_file:
            fp = os.open(os.path.abspath(filepath+filename), os.O_WRONLY | os.O_CREAT) # Creates the file
        else:
            fp = open(os.path.abspath(filepath+filename), "w")

        l.info("Generated file: " + str(filename))

        return fp, count

    # Opens a file for reading and writing

def open_file( filename="default.txt", filepath="default_path"):
        """
        Just opens a file and returns the file pointer

        :return: File
        """

        if filepath == "default_path":
            filepath = ""

        try:
            fp = open(filepath + filename, 'r+') #Opens file for reading and writing
            return fp
        except IOError:
            l.error(str(filepath + filename) + " is not an existing file.")

    # Closes a file (just needs the file pointer)

def close_file( fp):
        """
        Closed the file specified in param fp

        """
        try:
            try:
                os.close(fp)
            except:
                fp.close()
        except GeneratorExit:
            l.error("Closing the file: " + str(fp) + " was not possible")
        except:
            l.error("Unknown error occured, while closing file " + str(fp) + "Error: ", sys.exc_info()[0])

    # This flushes a string to a file

def flush_to_file(fp, message):
        """
        Flushes data to a opend file
        Only strings or numbers allowed, Lists will work too but may cause data scrambling
        Only use this with created files from function 'create_new_file'
        """
        os.write(fp, str.encode(message)) #Writes the message to file
        os.fsync(fp) # ensures that the data is written on HDD

def write_to_file( content, filename="default.txt", filepath = "default_path"):
        """
        This writes content to a file. Be aware, input must be of type 'list' each entry containing the information of one line
        """

        fp = open_file(filename, filepath)

        try:
            for line in content:
                fp.write(str(line))
        except IOError:
            l.error("Writing to file " + filename + " was not possible")
        except:
            l.error("Unknown error occured, while writing to file " + str(filename) + "Error: ", sys.exc_info()[0])

        close_file(fp)

def read_from_file( filename="default.txt", filepath = "default_path"):
        """
        Gives you the content of the file in an list, each list entry is one line of the file (datatype=string)
        Warning: File gets closed after reading
        """

        fp = open_file(filename, filepath)

        try:
            return fp.readlines()
        except IOError:
            l.error("Could not read from file.")
            return []
        except:
            l.error("Unknown error occured, while reading from file " + str(filename) + "Error: ", sys.exc_info()[0])

        close_file(fp)

    # These functions are for reading and writing to files------------------------------------
    # -------------------------------------------------------------------------------------end

def ramp_voltage_job( queue, resource, order, voltage_Start, voltage_End, step, wait_time = 0.2, compliance=100e-6):
        """
        Only use this function for simple ramping for the main, never inside a measurement!!!
        """
        job = {"Measurement": {"ramp_voltage": {"Resource": resource,
                                "Order": order,
                                "StartVolt": voltage_Start,
                                "EndVolt": voltage_End,
                                "Steps": step,
                                "Wait": wait_time,
                                "compliance": compliance}}}
        queue.put(job)

def int2dt( ts, ts_mult = 1e3):
        """
        Convert seconds value into datatime struct which can be used for x-axis labeeling
        """
        return datetime.datetime.utcfromtimestamp(float(ts) / ts_mult)

def get_timestring_from_int( time_array, format = "%H:%M:%S"):
        """
        Converts int time to timestring
        """
        list = []
        for value in time_array:
            list.append((value, int2dt(value,1).strftime(format)))
        return list

def get_thicks_for_timestamp_plot( time_array, max_number_of_thicks = 10, format = "%H:%M:%S"):
        """
        This gives back a list of tuples for the thicks
        """
        final_thicks = []
        if len(time_array) <= max_number_of_thicks:
            final_thicks = get_timestring_from_int(time_array, format)
        else:
            length = len(time_array)
            delta = int(length/max_number_of_thicks)
            for i in range(0, length, delta):
                final_thicks.append((time_array[i], int2dt(time_array[i],1).strftime(format)))
        return final_thicks

class CAxisTime(pg.AxisItem):
        """Over riding the tickString method by extending the class"""

            # @param[in] values List of time.
            # @param[in] scale Not used.
            # @param[in] spacing Not used.
        def tickStrings( values, scale, spacing):
            """Generate the string labeling of X-axis from the seconds value of Y-axis"""
            # sending a list of values in format "HH:MM:SS.SS" generated from Total seconds.
            return [(int2dt(value).strftime("%H:%M:%S.%f"))[:-4] for value in values]

        def int2dt(ts, ts_mult=1e3):
            """Convert seconds value into datatime struct which can be used for x-axis labeeling"""
            return (datetime.utcfromtimestamp(float(ts) / ts_mult))

def change_axis_ticks( plot, stylesheet=None):
        """Changes the pen and style of plot axis and labels"""
        font = QtGui.QFont()
        font.setPointSize(stylesheet["pixelsize"])
        plot.getAxis("bottom").tickFont = font
        plot.getAxis("top").tickFont = font
        plot.getAxis("right").tickFont = font
        plot.getAxis("left").tickFont = font

def build_command(device, command_tuple, single_commands = False):
    """Builds the command which needs to be send to a device correctly
    single_commands = True means if a list is passed the return is also a list with command value pairs"""
    if isinstance(command_tuple, (str)):
        command_tuple = (command_tuple,"") # make da dummy command

    if command_tuple[0] in device:

        if isinstance(device[command_tuple[0]], dict):
            try:
                com = device[command_tuple[0]]["command"]
            except:
                l.error("Dict command structure recognised but no actual command found for passed order {}".format(command_tuple))
                return None
        else:
            com = device[command_tuple[0]]

        if isinstance(command_tuple[1], (str, float, int)):
            try:
                return com.format(command_tuple[1])
            except IndexError:
                l.error("You attempted to send a command with the wrong number of parameters the command structure is: {}"
                               " but you passed: [{}] as parameter(s)".format(com, command_tuple[1]))

        elif single_commands:
            if isinstance(command_tuple[1], list) or isinstance(command_tuple[1], tuple) :
                return [com.format(single) for single in command_tuple[1]]
            else:
                l.error("In order to build a list command, a list has to be passed!")
                return None

        elif isinstance(command_tuple[1], list) or isinstance(command_tuple[1], tuple):
            # Find occurance of {} in string if list is as long as occurance of {} then just pass otherwise join a string
            brackets_count = device[command_tuple[0]].count("{}")
            if len(command_tuple[1]) == brackets_count:
                return com.format(*command_tuple[1])
            elif brackets_count == 1 and len(command_tuple[1]) > brackets_count:
                sep = device.get("separator", " ")
                return com.format(sep.join([str(x) for x in command_tuple[1]]))
            elif len(command_tuple[1]) > brackets_count or len(command_tuple[1]) < brackets_count and brackets_count != 1:
                l.error("Could not build command for input length {}"
                        " and input parameters length {}. Input parameters must be of same length"
                        " as defined in config or 1".format(len(command_tuple[1]),
                                                                brackets_count))
                return None
    else:
        l.error("Could not find command {} in command list of device: {}".format(command_tuple[0],
                                                                                        device["Device_name"]))

def build_command_depricated(device_dict, command_tuple):
        """
        This function correctly builds the command structure for devices.
        You must pass the device object dictionary with all parameters and a command tuple, consisting of:
        Command: A command specified in the device object.
        Value: A string or a list of commands which are the value the command is send with. (Also possible '[a,b,c]' etc.)

        If a syntax key is present in the device object like: 'syntax': '(@###)' the char between the # will be pre and appended, to the values, respectively
        If a key has a corresponing CSV prepended, like get_position = pos and CSV_get_position = x,y,z, the value passed need
        to have at least as much values, or the missing values WILL be filled with 0. (the CSV is actually not needed, this is for security reasons, so you dont forget something)
        Furthermore, if a seperator key is present, you can specify how the CSV command is seperated, standard is a single space.
        If the key command_order is specified either with 1 or -1 the logical order of the command is reversed, so with -1
        the values are comming first then the actual command. When nothing is specified a 1 is assumed

        If you pass a list in values, all of these will be generate a return list with each list values a complete command, even when you have a different separator specified
        If you want a correct one specify a CSV command. Non list object will be ignored and alle appended to a long command

        If you just pass a string, not a tuple only the command will be returned

        If a terminator key is in the object, this will be automatically be appended

        If the key: no_syntax_with_single_commmand is prevalent, the command build (when only a string is passed)will only return the command without syntax (if specified)

        Return value is usually a string with the command. Except if your command consists of a list e.g you want:
        device_dict[command] => ["comA", "comB"], then both commands will be build with the values and a list of both commands will be returned


        :param device: device dictionary
        :param command_tuple: (command, value), can also be a string for a final command
        :return string or list, depending if dict[command] is a list or a string
        """
        command = " " # The final command which should be send in the end
        return_list = [] # Is list of commands which can be returned if need be
        only_command = False # Flag if only a command was passed, important if such a command doesnt need syntax!

        if type(command_tuple) == type(u"Unicode") or type(command_tuple)== str or type(command_tuple)== float or type(command_tuple)== int:
            command_tuple = (str(command_tuple),"") # so only tuple are now prevelent
            only_command = True
        elif type(command_tuple[1]) == list:
            command_tuple = (command_tuple[0], [str(x) for x in command_tuple[1]]) # so no unicode is present

        # Preparations
        # look for a syntax (paranteses and so on)
        if "syntax" in device_dict:
            syntax = str(device_dict["syntax"])
            syntax = syntax.split("###")
            if not syntax[0]:
                syntax = ["", ""]  # Most devices have no paranteses or whatsoever
        else:
            syntax = ["",""] # Most devices have no paranteses or whatsoever

        #Looks if a separator is needed to sepatare mulitple orders
        if "separator" in device_dict:
            sepa = str(device_dict["separator"])
        else:
            sepa = " " # This should be the standard for most devices


        if command_tuple[0] in device_dict:
            # here all the magic happens
            # First look if the order is swichted or not (command value, or value command)

            # Check if multiple commands so list or so
            if type(device_dict[command_tuple[0]]) == str or type(device_dict[command_tuple[0]]) == type(u"Unicode"):
                command_list = [device_dict[command_tuple[0]]]
            else:
                command_list = device_dict[command_tuple[0]]

            for command_item in command_list:
                command_item = str(command_item)
                command = ""

                # Value -> Command
                if int(device_dict.get("command_order", 1)) == -1:
                    # Now look if a csv structure is necessary for the command to work
                    start_ind = command_tuple[0].find("_")  # finds the index of the command, to search for
                    if "CSV" + command_tuple[0][start_ind:] in device_dict:  # looks if an actual csv-command is there
                        # Todo: test CSV command
                        csv_commands = device_dict["CSV" + str(command_tuple[0])[start_ind:]]
                        csv_commands = csv_commands.strip().strip("(").strip(")").strip("[").strip("]").strip()  # get rid of some caracters which should not be there
                        csv_commands = csv_commands.split(",")  # now split it for easy access

                        # Make sure you always got a list of the next commandblock will fail
                        if type(command_tuple[1]) == list or type(command_tuple[1]) == tuple:
                            value_list = command_tuple[1]
                        elif type(command_tuple[1]) == str or type(command_tuple) == type(u"Unicode"):
                            value_list = command_tuple[1].strip().strip("(").strip(")").strip("[").strip("]").strip().replace(" ", "")
                            value_list = value_list.split(",")

                        csv_list = ",".join(map(str,value_list)).strip().strip("(").strip(")").strip("[").strip("]").strip()
                        csv_list = csv_list.split(",")

                        for i, com in enumerate(csv_list):
                            # here the input will be checked if enough parameters are passed for this command.
                            # If not a 0 will be entered and a warning will be printed
                            command += str(csv_list[i]).strip() + sepa

                        if i+1 < len(csv_commands) and len(csv_commands)>1:
                            for j in range(i+1, len(csv_commands)):  # Fill the rest of the missing paramters
                                l.error("Warning: Not enough parameters passed for function: " + str(command_item) + " the command must consist of " + str(csv_commands) + " '" + str(csv_commands[j]) + "' is missing! Inserted 0 instead.")
                                command += "0" + sepa

                        command = command.strip(" ").strip(",")  # to get rid of last comma

                    else:  # So if no CSV was found for this command, just build the command with the value and the separator
                        # First check if a List is present or so
                        if type(command_tuple[1]) == list or type(command_tuple[1]) == tuple:
                            string = ""
                            for item in command_tuple[1]:
                                command =  syntax[1] + str(item) + " " + command_item
                                command = command.strip()
                                # Add a command terminator if one is needed and the last part of the syntax
                                command += device_dict.get("execution_terminator", "")
                                return_list.append(command)
                            return return_list

                        else: # If only a command was passed
                            string = str(command_tuple[1])
                            command += syntax[1] + str(string).strip()

                            if only_command and device_dict.get("no_syntax_with_single_commmand", False) and syntax[1]!= " " and syntax[0]!= " ":
                                command = command.replace(syntax[1], "")
                                command = command.replace(syntax[0], "")

                    #command += " " + str(device_dict[str(command_item)]).strip() + syntax[0]  # adds the order to the command
                    command += " " + str(command_item).strip() + syntax[0]  # adds the order to the command
                    # Add a command terminator if one is needed and the last part of the syntax
                    command = command.strip()
                    command += device_dict.get("execution_terminator", "")
                    #command += syntax[0]  # adds the order to the command
                    return_list.append(command)

                #Command -> Value
                else:
                    command += str(command_item).strip() + " " + syntax[0] # adds the order to the command

                    # Now look if a csv structure is necessary for the command to work
                    start_ind = command_tuple[0].find("_") # finds the index of the command, to search for
                    if "CSV" + command_tuple[0][start_ind:] in device_dict: # looks if an actual csv-command is there
                        #Todo: test CSV command
                        csv_commands = device_dict["CSV" + str(command_tuple[0])[start_ind:]]
                        csv_commands = csv_commands.strip().strip("(").strip(")").strip("[").strip("]").strip() # get rid of some caracters which should not be there
                        csv_commands = csv_commands.split(",")  # now split it for easy access

                        # Make sure you always got a list of the next commandblock will fail
                        if type(command_tuple[1]) == list or type(command_tuple[1]) == tuple:
                            value_list = command_tuple[1]
                        elif type(command_tuple[1])==str or type(command_tuple)==type(u"Unicode"):
                            value_list = command_tuple[1].strip().strip("(").strip(")").strip("[").strip("]").strip().replace(" ", "")
                            value_list = value_list.split(",")


                        csv_list = ",".join(map(str,value_list)).strip().strip("(").strip(")").strip("[").strip("]").strip()
                        csv_list = csv_list.split(",")

                        for i, com in enumerate(csv_list):
                            # here the input will be checked if enough parameters are passed for this command.
                            # If not a 0 will be entered and a warning will be printed
                            command += str(csv_list[i]).strip() + sepa + " "

                        if i+1 < len(csv_commands) and len(csv_commands)>1:
                            for j in range(i+1, len(csv_commands)):# Fill the rest of the missing paramters
                                l.warning("Not enough parameters passed for function: " + str(command_tuple[0]) + " the command must consist of " + str(csv_commands) + " '" + str(csv_commands[j]) + "' is missing! Inserted 0 instead.")
                                command += " " + "0" + sepa

                        command = command.strip(" ").strip(",") # to get rid of last comma and space at the end if csv
                        command +=  syntax[1]

                    else: # So if no CSV was found for this command, just build the command with the value and the separator
                        # First check if a List is present or so
                        if type(command_tuple[1]) == list or type(command_tuple[1]) == tuple:
                            string = ""
                            for item in command_tuple[1]:
                                command = str(item) + " " + command_item + syntax[1]
                                command = command.strip()
                                # Add a command terminator if one is needed and the last part of the syntax
                                command += device_dict.get("execution_terminator", "")
                                return_list.append(command)
                            return return_list

                        else: # If its just one value or no value
                            string = str(command_tuple[1])
                            command += string.strip() + syntax[1]
                            command = command.strip()

                            if only_command and device_dict.get("no_syntax_with_single_commmand", False) and syntax[1]!= " " and syntax[0]!= " ":
                                command = command.replace(syntax[1], "")
                                command = command.replace(syntax[0], "")

                            # Add a command terminator if one is needed and the last part of the syntax
                            command += device_dict.get("execution_terminator", "")
                    return_list.append(command.strip())
        else:
            # If the command is not found in the device only command tuple will be send
            l.error("Command " + str(command_tuple[0]) + " was not found in device! Unpredictable behavior may happen. No commad build!")
            return ""

        # Add a command terminator if one is needed and the last part of the syntax
        #command += device_dict.get("execution_terminator","")



        # Todo: multiple commands return
        if len(return_list) > 1:
            return return_list
        else:
            return str(return_list[0])

#class newThread(threading.Thread):  # This class inherite the functions of the threading class
class newThread(QtCore.QThread):  # This class inherite the functions of the threading class
    '''Creates new threads easy, it needs the thread ID a name, the function/class,
    which should run in a seperated thread and the arguments passed to the object'''

    def __init__(self, threadID, name, object__, *args):  # Init where the threadID and Thread Name are defined
        """
        :param threadID: ID the thread should have
        :param name: Give the thread a name you want
        :param object__: The object which should run in the new thread
        :param args: Arguments passed to object__
        """

        QtCore.QThread.__init__(self)  # Opens the threading class

        self.threadID = threadID
        self.name = name
        self.object__= object__
        self.args = args
        self.log = logging.getLogger(__name__)
        self.log.info("Initialized new thread with ID: {!s}, Name: {!s} and Object: {!s}".format(
            self.threadID, self.name, self.object__))

    def run_process(self, object__, args): # Just for clarification, not necessary.
        """
        """
        return object__(*args)


    def run(self):
        """Starts running the thread"""
        self.log.info("Starting thread: " + self.name)
        self.object__ = self.run_process(self.object__, self.args)

    def get(self):
        '''returns the Object'''
        return self.object__

class newThread_(QtCore.QThread):  # This class inherite the functions of the threading class
    '''Creates new threads easy, it needs the thread ID, a name, the function/class, which should run in a seperated thread
    This is the same thing like newThread but instead QTCore modules are used.'''

    def __init__(self, threadID, name, object__, *args):  # Init where the threadID and Thread Name are defined

        QtCore.QThread.__init__(self)  # Opens the threading class

        self.threadID = threadID
        self.name = name
        self.object__= object__
        self.args = args
        self.log = logging.getLogger(__name__)

    def run_process(self, object__, args): # Just for clarification, not necessary.
        return object__(*args)

    def run(self):
        # run() is a member function of Thread() class. This will be called, when object thread will be started via thread.start()
        self.log.info("Starting thread: " + self.name)
        self.object__ = self.run_process(self.object__, self.args)

    @staticmethod
    def get():
        '''returns the Object''' # Not working, do not use
        newThread_.object__()

class LogFile:
    """
    This class handles the Logfile for the whole framework
    """
    def __init__(self, path='logger.yml', default_level=logging.INFO, env_key='LOG_CFG'):
        """
        Initiates the logfile with the logging level
        :param path: Path to logger file
        :param logging_level: None, debug, info, warning, error critical
        :param env_key: env_key
        """


        value = os.getenv(env_key, None)
        if value:
            path = value
        if os.path.exists(os.path.normpath(path)):
            with open(path, 'rt') as f:
                config = yaml.safe_load(f.read())
                # If directory is non existent create it
                # Todo: Here a dir will be made after installation, so if this prohibited go to the other dir
                pathtologfile = config["handlers"]["file"]["filename"].split("/")
                if not os.path.isdir(os.path.join(os.getcwd(),*pathtologfile[:-1])):
                    os.mkdir(os.path.join(os.getcwd(),*pathtologfile[:-1]))
            logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=default_level)

        self.log_LEVELS = {"NOTSET": 0, "DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

        self.welcome_string =  "\n" \
                               "\t\t\t\t\t\t\t\t  __         ______     ______     ______   __     __         ______           ______     ______   ______\n  \
                               /\ \       /\  __ \   /\  ___\   /\  ___\ /\ \   /\ \       /\  ___\         /\  __ \   /\__  _\ /\  ___\ \n   \
                              \ \ \____  \ \ \/\ \  \ \ \__ \  \ \  __\ \ \ \  \ \ \____  \ \  __\         \ \ \/\_\  \/_/\ \/ \ \ \____ \n  \
                                \ \_____\  \ \_____\  \ \_____\  \ \_\    \ \_\  \ \_____\  \ \_____\        \ \___\_\    \ \_\  \ \_____\ \n \
                                  \/_____/   \/_____/   \/_____/   \/_/     \/_/   \/_____/   \/_____/         \/___/_/     \/_/   \/_____\n\n\n"

        # Create a logger Object
        self.LOG = logging.getLogger("Logfile")
        # Print welcome message
        self.LOG.info(self.welcome_string)

class Framework:
    """
    Generall class for handling all Framework related tasks, like updating the GUI etc.
    """

    def __init__(self, values_from_GUI):
        """
        :param values_from_GUI: A tuple of (list of functions, udate intervall)
        """

        self.functions, self.update_interval = values_from_GUI()
        self.timer = None
        self.log = logging.getLogger("Framework")

    def start_timer(self):  # Bug timer gets not called due to a lock somewhere else
        """
        Simply starts the timer

        :return: timer
        """
        self.log.info("Framework initialized...")
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update_)
        timer.start(self.update_interval)
        self.timer = timer
        return timer

    def update_(self):
        """
        Periodically updates the functions in self.functions list

        :return: None
        """
        for function in self.functions:
            try:
                function()
            except Exception as err:
                self.log.critical("While updating the framework an error happend in function {} with error: {}".format(function, err))
                raise

class transformation:
    """Class which handles afine transformations in 3 dimensions for handling sensor to jig coordinate systems"""

    def __init__(self):
        self.log = logging.getLogger(__name__)

    @raise_exception
    def transformation_matrix(self, s1, s2, s3, t1, t2 ,t3):
        """Calculates the transformation matrix of the system.
        Via the equation T = P^-1 Q where P and Q are coming from the linear system s*T + V0 = v
        si are the corresponding vectors (coordinates) in the sensor system, ti are those from the table system.
        They must be numpy arrays.
        """

        s1 = np.array(s1)
        s2 = np.array(s2)
        s3 = np.array(s3)
        t1 = np.array(t1)
        t2 = np.array(t2)
        t3 = np.array(t3)

        Q = np.array([
                    [t2[0] - t1[0], t2[1] - t1[1], t2[2] - t1[2]],
                    [t3[0] - t1[0], t3[1] - t1[1], t3[2] - t1[2]]
        ])

        P = np.array([
                    [s2[0] - s1[0], s2[1] - s1[1]],
                    [s3[0] - s1[0], s3[1] - s1[1]]
        ])


        try:
            # Invert the P matrix
            Pinv = inv(P)

            # Build the dot product
            T = np.dot(Pinv, Q)

            # Offset
            V0 = np.subtract(t2,np.transpose(s2[0:2]).dot(T))
        except Exception as e:
            self.log.error("An error occured during the transformation with error: " + str(e))
            return -1, -1

        return T, V0

    def vector_trans(self, v, T, V0):
        """This function transforms a Vector from the sensor system to the table system by vs*T+V0=vt"""
        v = np.array(v)
        return np.add(v[0:2].dot(T),V0)

def connection_test(schemes, switching, vcw, device, target_resistance=1, abs_err=0.1, set_command="set_meas_resistance"):
    """
    Switches to the passed switching schemes and conducts and measures the resistance. Is it not close to the passed
     one an error will be generated in the logs and a tuple with the scheme names and the resistance will be returned.
    :param schemes: A list/tuple of switching names
    :param switching: The switching class which takes str input for switching
    :param vcw: VCW instance to be used
    :param device: VCW device object
    :param target_resistance: The resistance it should have
    :param abs_err: the error it can have
    :param set_command: The command to set the device to, usually its set_meas_resistance
    :return: True if all is fine, a tuple of the schemes names which failed the connection test
    """
    command = build_command(device, set_command)
    read = build_command(device, "get_read")
    vcw.write(device, command)
    res = []
    # Switch on the output of the device and do some other configs
    outputON = build_command(device, ("set_output", "1"))
    outputOFF = build_command(device, ("set_output", "0"))
    mode = build_command(device, ("set_resistance_mode", "AUTO"))
    wire2 = build_command(device, ("set_resitance_state", "OFF"))
    readingMode = build_command(device, ("set_reading_mode", "RES"))
    readingModeOLD = build_command(device, ("set_reading_mode", "CURR"))
    setrear = build_command(device, ("set_terminal", "REAR"))
    setfront = build_command(device, ("set_terminal", "FRONT"))
    vcw.write(device, setrear)
    vcw.write(device, mode)
    vcw.write(device, wire2)
    vcw.write(device, readingMode)
    vcw.write(device,  outputON)
    for name in schemes:
        switching.switch_to_measurement(name)
        res.append(float(vcw.query(device, read)))
        l.debug("Resistances of Needle {}: {} Ohms".format(name, res[-1]))
    vcw.write(device, readingModeOLD)
    vcw.write(device, outputOFF)
    vcw.write(device, setfront)
    closeness = np.isclose([target_resistance for x in res], res, rtol=0, atol=abs_err)

    if np.all(closeness):
        return True
    else:
        return np.array(schemes)[~closeness]






class table_control_class:
    '''This class handles all interactions with the table. Movement, status etc.
    This class is designed to be running in different instances.

    :param main_variables: Defaults dict
    :param device: The VISA device object
    :param queue_to_GUI: Queue object to the main
    :param vcw: A VISA connect wizard instance
    '''

    # Todo: Currently only for corvus typed tables with the venus command structure.

    def __init__(self, main_variables, devices, queue_to_GUI, vcw):
        """

        :param main_variables: Defaults dict
        :param device: The VISA device object
        :param queue_to_GUI:
        :param vcw: A VISA connect wizard instance
        """
        self.variables = main_variables["settings"]
        self.devices = devices
        self.device = devices.get("Table_control", None)
        self.table_ready = self.variables.get("table_ready", False)
        self.queue = queue_to_GUI
        self.vcw = vcw
        self.build_command = build_command
        self.log = logging.getLogger("Table_control")
        self.pos_pattern = re.compile(r"(-?\d+.\d+)\s+(-?\d+.\d+)\s+(-?\d+.\d+)")
        self.lifting = 800
        self.previous_xloc = 0
        self.previous_yloc = 0
        self.previous_zloc = 0

        # Some variables which are needed
        self.variables["Alignment"] = False
        self.variables["trans_matrix"] = None
        self.variables["V0"] = None
        self.variables["Table_state"] = True # Means he is up
        self.variables["Table_stay_down"] = True # Means he is up
        self.variables["joystick"] = False
        self.variables["table_ready"] = False
        self.variables["zlock"] = True
        self.variables["table_is_moving"] = False

        if not "height_movement" in self.variables:
            self.log.warning("No height_movement for table specified, defaulting to 800")
            self.variables["height_movement"] = 800

        if not "clearance" in self.variables:
            self.log.warning("No clearance for table specified, defaulting to 200")
            self.variables["clearance"] = 200

        if "Table_control" in self.devices:
            if self.devices["Table_control"].get("Visa_Resource", None):
                self.visa_resource = self.devices["Table_control"]["Visa_Resource"]
                self.table_ready = True
                self.variables["table_ready"] = True
                self.zmove = self.variables["height_movement"]
            else:
                self.table_ready = False
                self.log.error("Table control could not be initialized! Visa Resource missing")
        else:
            self.table_ready = False

    def move_table_to_edge(self, axis, minimum=True, lifting=800, **kwargs):
        """
        Moves the table to the edge of the axis, the minimum indicates 0 or maximum possible value
        :param axis: Axis to move
        :param minimum: 0 (True, default) value of table or maximum
        :return: bool after finished
        """

        # Get the current position
        pos = self.get_current_position()
        if pos:
            self.previous_xloc = pos[0]
            self.previous_yloc = pos[1]
            self.previous_zloc = pos[2]

        # Move to the edge
        var = "table_{}{}".format(axis, "min" if minimum else "max")
        if var in self.devices["Table_control"]:
            pos = self.devices["Table_control"][var]

            if axis == "x":
                pos = [pos, self.previous_yloc, self.previous_zloc]
            elif axis == "y":
                pos = [self.previous_xloc, pos, self.previous_zloc]
            elif axis == "z":
                pos = [self.previous_xloc, self.previous_yloc, pos]
            else:
                pos = [self.previous_xloc, self.previous_yloc, self.previous_zloc]
                self.log.error("Table position recognition error. Table pos could not be determined correctly")

        else:
            self.log.error("Key for table maxima not included: {}".format(var))

        # Moves the table and reports back
        return self.move_to(pos, True, lifting, **kwargs)


    def move_previous_position(self, lifting=800, **kwargs):
        """Moves to the previous position, after the last move command. Only move commands from this class are taken into
        account. So if you move with the joystick. This will have no effect."""

        return self.move_to([self.previous_xloc, self.previous_yloc, self.previous_zloc], True, lifting, **kwargs)

    def new_previous_position(self, pos):
        """Stores the list of positions to the previous position variables"""
        self.previous_xloc = pos[0]
        self.previous_yloc = pos[1]
        self.previous_zloc = pos[2]
        return True

    def store_current_position_as_previous(self):
        """Stores the current position of the table, as the 'previous' one."""
        pos = self.get_current_position()
        self.previous_xloc = pos[0]
        self.previous_yloc = pos[1]
        self.previous_zloc = pos[2]
        return pos


    def get_current_position(self):
        '''Queries the current position of the table and writes it to the state machine'''
        if self.table_ready:
            max_attempts = 0
            while max_attempts < 3: # Loop as long as there is a valid position from the corvus
                try:
                    string = "Error"
                    command = self.build_command(self.device, "get_position")
                    string = self.vcw.query(self.device, command).strip()
                    pos = self.pos_pattern.findall(string)[0]
                    self.device["x_pos"] = float(pos[0])
                    self.device["y_pos"] = float(pos[1])
                    self.device["z_pos"] = float(pos[2])
                    return [float(i) for i in pos]
                except:
                    self.log.error("The corvus has replied with a non valid position string: " + str(string))
                    max_attempts += 1

    def check_if_ready(self, timeout = 0, maxcounter = -1):
        '''
        This function checks if the movement of the table is done or not

        :param timeout: Timeout how long to wait between the attempts
        :param maxcounter: How often does the function try to get an answer, -1 infinite
        :return: 0 if ok error if not
        '''
        # Alot of time can be wasted by the timeout of the visa read order
        ready_command = self.build_command(self.device, "get_all_done")
        counter = 0 # counter how often the read attempt will be carried out
        cal_not_done = True
        self.vcw.write(self.device, ready_command)
        while cal_not_done:
            done = self.vcw.read(self.device)
            if done:
                try:
                    done = float(done.strip())
                except:
                    self.log.error("Table status query failed to interpret: {} must be a float convertible".format(done))
                    done = -1
            else:
                sleep(0.1)
                continue

            if maxcounter != -1:
                counter += 1
                if counter > maxcounter:
                    cal_not_done = False #exits the loop after some attempts

            # todo: very bad coding here
            elif done == False and str(done) != "0.0":
                pass

            elif done == 1.: # motors are in movement
                self.vcw.write(self.device, ready_command) # writes the command again

            elif done%2==1.:
                self.vcw.write(self.device, ready_command)  # writes the command again
                self.log.critical("Table status has reported several status messages besides table moving. Additional Status: {}".format((done-1.)))
                done = done-1.

            if done == 2.: # joystick active
                self.log.error("Joystick of table control is active.")
                return False

            elif done == 4.: # joystick active
                self.log.error("Table control is not switched on.")
                return False

            elif done == 32.:
                self.log.debug("Table reported Status code 32, which means IN-Window.")
                #return False

            elif done > 4.: # joystick active
                self.log.error("The table control reported an unknown error, with errorcode: " + str(done) + ". Please see the manual.")
                return False

            elif done == -1: # when corvus fucked up
                return False

            elif done == 0.: # when corvus is read again
                return True

            QApplication.processEvents() # Updates the GUI, maybe after some iterations
            sleep(timeout)

    def initiate_table(self):
        '''
        This function triggers the table initiation

        :return: False if ok error if not
        '''
        if self.table_ready and not self.variables["table_is_moving"]:
            self.variables["table_is_moving"] = True
            self.set_axis([True, True, True])
            commands = self.device["calibrate_motor"]
            for order in commands:
                self.vcw.write(self.device, order)
                success = self.check_if_ready()
                if success:
                    pos = self.get_current_position()
                    if commands[0] == order:
                        self.device["table_xmin"] = float(pos[0])
                        self.device["table_ymin"] = float(pos[1])
                        self.device["table_zmin"] = float(pos[2])
                    else:
                        self.device["table_xmax"] = float(pos[0])
                        self.device["table_ymax"] = float(pos[1])
                        self.device["table_zmax"] = float(pos[2])

                else:
                    self.variables["table_is_moving"] = False
                    return success
            self.variables["table_is_moving"] = False
            self.set_axis([True, True, False])
            return True
        else:
            self.log.error("An error occured while trying to initiate the table. This can happen if either no "
                           "Table is connected to the setup OR the table is currently moving.")
            self.set_axis([True, True, False])
            return False

    def check_position(self, desired_pos):
        '''
        This function checks if two positions are equal or not

        :param desired_pos: The position it should be
        :return: True if ok
        '''
        new_pos = self.get_current_position()
        for i, pos in enumerate(new_pos):
            if abs(float(pos) - float(desired_pos[i])) > 0.5: # up to a half micrometer
                self.log.error("Table movement failed. Position: " + str(new_pos) + " is not equal to desired position: " + str(desired_pos))
                return False
        return True

    def __already_there(self, pad_file, strip, transfomation_class, T, V0):
        '''
        Checks if we are already at the strip we want to move to

        :param pad_file:
        :param strip:
        :param transfomation_class:
        :param T:
        :param V0:
        :return: True if at strip
        '''
        pos = self.get_current_position()  # table position
        pad_pos = [float(x) for x in pad_file["data"][str(strip)]]  # where it should be in sensor system
        table_pos = transfomation_class.vector_trans(pad_pos, T, V0)  # Transforms the vektor to the right basis
        deltapos = [abs(x1 - x2) for (x1, x2) in zip(pos, table_pos)]

        for delta in deltapos:
            if delta >= 0.5:  # Checks if the position is correct in a range of 0.5 um
                return False
        return True


    def move_to_strip(self, pad_file, strip, transfomation_class, T, V0, height_movement, **kwargs):
        '''
        Moves to a specific strip

        :param transfomation_class:
        :param height_movement: How much should the table move down
        :return: None or errorcode
        '''

        if transformation != []:
            if not self.__already_there(pad_file, strip, transfomation_class, T, V0):
                pad_pos = pad_file["data"][str(strip)]
                self.log.info("Moving to strip: {} at position {},{},{}.".format(strip, pad_pos[0], pad_pos[1], pad_pos[2]))
                table_abs_pos = list(transfomation_class.vector_trans(pad_pos, T, V0))
                success = self.move_to(table_abs_pos, move_down=True, lifting = height_movement, **kwargs)
            else:
                return True

            self.variables["current_strip"] = strip
            return success
        else:
            self.log.error("No Transformation Matrix found! Is the alignment done?")
            return False


    def relative_move_to(self, position, move_down = True, lifting = 800, **kwargs):
        '''
        This function moves the table to the desired position (relative). position is a list of coordinates
        The move down parameter can prohibit a down and up movement with the move, !!!!USE WITH CARE!!!!

        :return: none or error code
        '''
        success = self.move_to(position, move_down, lifting, True, **kwargs)
        return success


    def move_to(self, position, move_down=True, lifting=800, relative_move=False, clearance=0.0):
        """
        This function moves the table to the desired position. position is a list of coordinates
        The move down parameter can prohibits a down and up movement with the move, !!!!USE WITH CARE!!!!


        :param position: A position list in form of [x,y,z]
        :param move_down: If the table must be moved down by lifting
        :param lifting: the height how far down to move
        :param relative_move: If the position is a relative movement
        :param clearence: If move_down, instead of moving up the full lifting, the height movement ist lifting-clearance
        :return: None or errorcode
        """
        self.log.debug("Try moving table to {!s}".format(position))
        if self.table_ready and not self.variables["table_is_moving"]:
            # get me the current position
            old_pos = self.get_current_position()
            if move_down: # So only parent move orders are stored and not every height movement
                self.new_previous_position(old_pos)
            desired_pos = position[:]

            # If the table is somehow moving or reported an error before, so check if all errors have vanished
            #success = self.check_if_ready()

            #Move the table down if necessary
            if move_down:
                success = self.move_down(lifting)
                if not relative_move:
                    desired_pos[2] -= lifting # To counter the down movement
                if not success:
                    return False

            # Change the state of the table
            self.variables["table_is_moving"] = True

            # Move the table to the position
            if relative_move:
                move_command = self.build_command(self.device, ("set_relative_move_to", desired_pos))
            else:
                move_command = self.build_command(self.device, ("set_move_to", desired_pos))
            self.vcw.write(self.device, move_command)
            success = self.check_if_ready()
            if not success:
                return False

            # State that the table is not moving anymore
            self.variables["table_is_moving"] = False

            # Move the table back up again
            if move_down:
                success = self.move_up(lifting-clearance)
                position[2] -= clearance # Adapt the position to make sure the check works
                if not success:
                    return False

            # Finally make sure the position is correct
            if relative_move:
                success = self.check_position([sum(x) for x in zip(old_pos, position)])
                if success:
                    self.log.debug("Successfully moved table relative to {!s}".format(position))
            else:
                success = self.check_position(position)
                if success:
                    self.log.debug("Successfully moved table to {!s}".format(position))
            if not success:
                return False

            self.variables["table_is_moving"] = False

            return True

        elif self.variables["table_is_moving"]:
            self.log.warning("Table is currently moving, no new move order can be placed...")
        else:
            self.log.error("Table could not be moved due to an error. This usually happens if no table is connected to"
                           " the setup")
            return False

    def move_up(self, lifting, **kwargs):
        '''
        This function moves the table up

        :param lifting:  hight movement
        :return: none or errorcode
        '''
        self.log.debug("Moving table up by {!s} microns".format(lifting))
        if not self.variables["Table_state"]:
            success = self.move_to([0,0,lifting], False, 0, True, **kwargs)
            if success:
                self.variables["Table_state"] = True # true means up
            return success
        else:
            self.queue.put({"Info": "Table already in the up position..."})
        return True

    def move_down(self, lifting, **kwargs):
        '''
        This function moves the table down

        :param lifting:  hight movement
        :return: none or errorcode
        '''
        self.log.debug("Moving table down by {!s} microns".format(lifting))
        if self.variables["Table_state"]:
            success = self.move_to([0,0,-lifting], False, 0, True, **kwargs)
            if success:
                self.variables["Table_state"] = False
            return success
        else:
            self.queue.put({"Info": "Table already in the down position..."})
        return True

    def set_joystick(self, bool):
        '''This enables or disables the joystick'''
        if self.table_ready:
            if bool:
                command = self.build_command(self.device, ("set_joystick", "1"))
            else:
                command = self.build_command(self.device, ("set_joystick", "0"))
            self.vcw.write(self.device, command)

    def set_joystick_speed(self, speed):
        '''This sets the speed for the joystick'''
        if self.table_ready:
            command = self.build_command(self.device, ("set_joy_speed", str(speed)))
            self.vcw.write(self.device, command)

    def set_axis(self, axis_list):
        '''This sets the axis on or off. axis_list must contain a list of type [x=bool, y=bool, z=bool]'''
        if self.table_ready:
            final_axis_list = []
            for i, axis in enumerate(axis_list):
                if axis:
                    final_axis_list.append("1 " + str(i+1))
                else:
                    final_axis_list.append("0 " + str(i+1))

            command = self.build_command(self.device, ("set_axis", final_axis_list), single_commands=True)
            self.vcw.write(self.device, command)


    def stop_move(self):
        '''This function stops the table movement immediately'''
        if self.table_ready:
            command = self.build_command(self.device, "abort_movement")
            self.vcw.write(self.device, command)

class switching_control:
    """
        This class handles all switching actions, for all switching devices

        :param settings: default settings ( state machine )
        :param devices: devices dict
        :param queue_to_main: The queue object to the main
        :param vcw: A visa connect wizard instance
        """

    def __init__(self, settings, devices, queue_to_main, vcw):
        """
        This class handles all switching actions

        :param settings: default settings ( state machine )
        :param devices: devices dict
        :param queue_to_main: The queue object to the main
        :param vcw: A visa connect wizard instance
        """
        self.settings = settings
        self.message_to_main = queue_to_main
        self.devices = devices
        self.vcw = vcw
        self.switching_systems = []
        self.build_command = build_command
        self.settings["settings"]["current_switching"] = {}
        self.log = logging.getLogger(__name__)

        # Find all switching relays and store them for easy access
        for dev in self.devices.values():
            if "Switching relay" in dev.get("Device_type","None") and "Visa_Resource" in dev:
                self.settings["settings"]["current_switching"][dev["Device_name"]] = []
                self.switching_systems.append(dev)

    def reset_switching(self, device="all"):
        '''
        This function resets all switching or one device switching

        :param device: all oder device object:
        '''
        if device == "all": # opens all switches in all relays
            for dev in self.switching_systems:
                configs = self.build_command(dev, "set_open_channel_all")
                self.vcw.write(dev, configs)
                self.check_all_closed_channel(dev, [])
        else:
            configs = self.build_command(device, "set_open_channel_all")
            self.vcw.write(device, configs)
            self.check_all_closed_channel(device, [])

    def check_switching_action(self):
        """Checks what channels are closed on all switching devices"""
        current_switching = {}
        for devices in self.switching_systems:
            command = self.build_command(devices, "get_closed_channels")
            switching = str(self.vcw.query(devices, command)).strip()
            switching = self.pick_switch_response(devices, switching)
            current_switching.update({devices["Device_name"]: switching})
            self.settings["settings"]["current_switching"][devices["Device_name"]] = current_switching
        return current_switching

    def apply_specific_switching(self, switching_dict):
        """
        This function takes a dict of type {"Switching": [/switch nodes], ....} and switches to these specific type

        :param switching_dict: What to switch
        :return: bool
        """
        found_any = False
        for device in self.devices:
            if device in switching_dict.keys():
                found_any = True
                if not self.change_switching(self.devices[device], switching_dict[device]):
                    self.log.error("Manual switching was not possible for device {}".format(device))
                    return False
        if not found_any:
            self.log.error("Could not find switching device: {}. It may not be connected or specified.".format(device))
            return False
        return True

    #@check_if_switching_possible
    def switch_to_measurement(self, measurement):
        '''
        This function switches all switching systems to a specific measurement type

        :param measurement: string e.g. "IV", "CV" must be defined in the switching dict
        :return: true or false, so if switching was successfull or not
        '''

        if not self.switching_systems:
            self.log.critical("No switching systems defined but attempt to switch to measurement {}. "
                              "Returning dummy True".format(measurement))
            return True

        #Todo: Brandbox is sended twice due to double occurance (humidity controller), but maybe its for the best, since the thing isnt working properly
        #First find measurement
        switching_success = False
        self.log.debug("Switching to measurement: {!s}".format(str(measurement)))
        if measurement in self.settings["Switching"]["Switching_Schemes"]:
            # When measurement was found
            for device in self.settings["Switching"]["Switching_devices"]:
                if device in self.settings["Switching"]["Switching_Schemes"][measurement]:
                    if device in self.devices:
                        switch_list = self.settings["Switching"]["Switching_Schemes"][measurement][device]
                        if not switch_list:
                            switch_list = []
                        if not self.change_switching(self.devices[device], switch_list):
                            self.log.error("Switching to {} was not possible".format(switch_list))
                            return False
                    else:
                        self.log.error("Switching device: {} was not found in active resources. No switching done!".format(device))
                        return False
                else:
                    if device in self.devices:
                        switch_list = []
                        if not self.change_switching(self.devices[device], switch_list):
                            self.log.error("Switching to {} was not possible".format(switch_list))
                            return False
                    else:
                        self.log.error(
                            "Switching device: {} was not found in active resources. No switching done!".format(device))
                        return False
            return True
        else:
            self.log.error("Measurement {} switching could not be found in defined switching schemes.".format(measurement))
            return False

    def __send_switching_command(self, device, order, list_of_commands):
        """Sends a switching command"""
        if list_of_commands:
            if list_of_commands[0]:
                command = self.build_command(device, (order, list_of_commands))
                if command: #If something dont work with the building of the command, no None will be send
                    self.vcw.write(device, command)  # Write new switching
        else:
            command = self.build_command(device, (order, ""))
            if command:  # If something dont work with the building of the command, no None will be send
                self.vcw.write(device, command)  # Write new switching

    def pick_switch_response(self, device, current_switching):
        '''
        This function picks the string response and returns a list.
        This function searches for a separator in the device dict and uses it to discect the message, standard is ','

        :device: The device object
        :param current_switching: is a string containing the current switching
        '''

        if current_switching == "nil":
            return []


        #syntax_list = device.get("syntax", "")
        #if syntax_list:
        #    syntax_list = syntax_list.split("###")# gets me header an footer from syntax

        sep = device.get("separator", ",")
        return current_switching.strip().split(sep)


        # Warning 7001 keithley sometimes seperates values by , and sometimes by : !!!!!!!!!
        # Sometimes it also happens that it mixes everything -> this means that the channel from to are closed etc.
        # LEGACY CODE
        # if ":" in current_switching:
        #     self.log.error("The switching syntax for this is not yet implemented, discrepancies do occure from displayed to actually switched case. TODO")
        #     if "," in current_switching: # if this shitty mix happens
        #         current_switching = current_switching.replace(",", ":")
        #     if len(syntax_list) > 1:
        #         current_switching = current_switching[len(syntax_list[0]): -len(syntax_list[1])]
        #         return current_switching.strip().split(":")  # now we have the right commands
        #     else:
        #         return current_switching.strip().split(":")  # now we have the right commands
        #
        # if "," in current_switching:
        #     if ":" in current_switching: # if this shitty mix happens
        #         current_switching = current_switching.replace(":", ",")
        #     if len(syntax_list) > 1:
        #         current_switching = current_switching[len(syntax_list[0]): -len(syntax_list[1])]
        #         #current_switching = current_switching.split(syntax_list[0]).split(syntax_list[1])
        #         return current_switching.strip().split(",")  # now we have the right commands
        #     else:
        #         return current_switching.strip().split(",")  # now we have the right commands
        #
        # elif "@" in current_switching: # if no switching at all happens
        #     if len(syntax_list) > 1:
        #         current_switching = current_switching[len(syntax_list[0]): -len(syntax_list[1])]
        #         return current_switching.strip().split()  # now we have the right commands
        #     else:
        #         return current_switching.strip().split()  # now we have the right commands
        # else:
        #     return current_switching.strip().split()  # now we have the right commands

    def change_switching(self, device, config): # Has to be a string command or a list of commands containing strings!!

        '''
        Fancy name, but just sends the swithing command

        :device: The device object
        :param config: the list of nodes which need to be switched
        '''
        # Check if only a string is passed and not a list and convert into list if need be
        if isinstance(config, str):
            configs = [config]
        else:
            configs = config

        if device.get("Visa_Resource", None): #Searches for the visa resource
            resource = device
        else:
            self.log.error("The VISA resource for device " + str(device["Device_name"]) + " could not be found. No switching possible.")
            return False

        if device.get("device_exclusive_switching", False):
            self.log.debug("Device exclusive switching used...")
            return self.device_exclusive_switching(device, configs)
        else:
             #Normal switching
             return self.manual_switching(device, configs, BBM = True)

    def device_exclusive_switching(self, device, configs):
        """
        Switching will be done exclusivly by the device itself. Warning make sure the device is correctly configured if
        you are using this routine

        :param device:  The device
        :param configs:  The configs dict
        :return: bool
        """
        self.__send_switching_command(device, "set_exclusive_close_channel", configs)
        # Check if switching is done
        return self.check_all_closed_channel(device, configs)


    def manual_switching(self, device, configs, BBM = True):
        """
        Manual switching, so opening and closing of channels is done via this software. Old keithley will need this
        Newer devices can do exclusive opening and closing.
        BBM or Break-before-make is the order how to switch, if False make-before-break is used. This is not
        recommended since it can dry weld the switches.

        :param device:  The device
        :param configs:  The configs dict
        :param BBM: Break before make or make before break,
        :return: bool
        """
        command = self.build_command(device, "get_closed_channels")
        current_switching = str(self.vcw.query(device, command)).strip()  # Get current switching
        current_switching = self.pick_switch_response(device, current_switching)

        to_open_channels = list(set(current_switching) - (set(configs)))  # all channels which need to be closed
        to_close_channels = configs

        if BBM:
            comm = ["set_open_channel", "set_close_channel"]
            channels = [to_open_channels, to_close_channels]
        else:
            comm = ["set_close_channel", "set_open_channel"]
            channels = [to_close_channels, to_open_channels]

        # Close channels
        self.__send_switching_command(device, comm[0], channels[0])

        # Open channels
        self.__send_switching_command(device, comm[1], channels[1])

        # Check if switching is done (basically the same proceedure like before only in the end there is a check
        return self.check_all_closed_channel(device, configs)

    def check_all_closed_channel(self, device, to_be):
        """
        Checks if all channels are correctly closed

        :param device: The device
        :param to_be: the to be state of the relays for this device
        :return: bool
        """
        device_not_ready = True
        counter = 0
        opc_command = self.build_command(device, "get_operation_complete")
        opc_success = str(device["get_operation_complete"].get("success", "1"))
        all_closed_command = self.build_command(device, "get_closed_channels")

        while device_not_ready:
            all_done = str(self.vcw.query(device, opc_command)).strip()
            if all_done == opc_success:
                current_switching = str(self.vcw.query(device, all_closed_command)).strip()
                current_switching = self.pick_switch_response(device, current_switching)
                self.settings["settings"]["current_switching"][device["Device_name"]] = current_switching
                command_diff = list(set(to_be).difference(set(current_switching)))
                if len(command_diff) != 0:  #Checks if all the right channels are closed
                    self.log.error("Switching to {}  was not possible. Difference read:{}".format(to_be, current_switching))
                    return False
                return True
            if counter > 5:
                device_not_ready = False
            counter += 1

        self.log.error("No response from switching system: " + device["Device_name"])
        return False

def load_QtCSS_StyleSheet(path):
    """Loads the QtCSS style sheet"""
    with open(path, 'rt') as f:
        lines = f.read()
    return lines

class show_cursor_position:
    """This class provides a simple way to tooltip a plot item of type pyqtgraph plots (not yet finished)"""

    def __init__(self, plotobject):
        """

        :param plotobject: The Plot object
        """

        self.plotItem = plotobject.getPlotItem()
        self.tooltip_text = pg.TextItem(text='', color=(176, 23, 31))
        self.tooltip_text.hide()
        plotobject.addItem(self.tooltip_text, ignoreBounds=True)
        self.proxy = pg.SignalProxy(plotobject.scene().sigMouseMoved, rateLimit=30, slot=self.onMove)
        self.log = logging.getLogger(__name__)

    def onMove(self, pos):
        mousePoint = self.plotItem.vb.mapSceneToView(pos[0])
        #self.plotItem.mapToDevice(mousePoint)
        if mousePoint:
            self.tooltip_text.setText("     x={!s}\n     y={!s}".format(int(round(mousePoint.x(),0)), EngUnit(mousePoint.y())))
            self.tooltip_text.setPos(mousePoint)
            self.tooltip_text.show()

        else:
            self.tooltip_text.hide()

def reset_devices(devices_dict, vcw):
    """Reset all devices."""
    l.critical("You are using a depricated reset devices function please remove it from your code")
    for device in devices_dict:
        # Looks if a Visa resource is assigned to the device.
        if devices_dict[device].get("Visa_Resource", None):

            # Initiate the instrument and resets it
            if "reset_device" in devices_dict[device]:
                vcw.initiate_instrument(
                    devices_dict[device]["Visa_Resource"],
                    devices_dict[device]["reset_device"],
                    devices_dict[device].get("execution_terminator", "")
                )
            else:
                vcw.initiate_instrument(
                    devices_dict[device]["Visa_Resource"],
                    ["*RST", "*CLS", "TRAC:CLE"],
                    devices_dict[device].get("execution_terminator", "")
                )

def parse_args():

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reinit", help="Calls the init window to initialize the setups",
                        action="store_true")
    parser.add_argument("--noGUI", help="If the GUI should be displayed or not",
                        action="store_true")
    parser.add_argument("--fullscreen", help="Shows the app in fullscreen mode",
                        action="store_true")
    parser.add_argument("--loadGUI", help="Load a specific GUI",
                        type=str)

    args = parser.parse_args()

    return args

def convert_to_df(to_convert, abs = False):
    """
    Converts a dict to panda dataframes for easy manipulation etc.
    :param data: Dictionary with data
    :param abs: if the data returned will be the absolute value of the data
    :return: pandas data frame object
    """
    # Convert all data to panda data frames
    index = list(to_convert.keys())
    columns = list(to_convert[index[0]]["data"].keys())
    return_dict = {"All": pd.DataFrame(columns=columns), "keys": index, "columns":columns}
    for key, data in to_convert.items():
        return_dict[key] = data
        try:
            if abs:
                for meas, arr in data["data"].items():
                    data["data"][meas] = np.abs(arr)
            data["data"]["Name"] = [key for i in range(len(data["data"][list(data["data"].keys())[0]]))]
            df = pd.DataFrame(data=data["data"])
        except KeyError as err:
            l.error("In order to convert the data to panda dataframe, the data structure needs to have a key:'data'")
            raise err
        return_dict[key]["data"] = df
        return_dict["All"] = pd.concat([return_dict["All"],df], sort=True)

    return return_dict


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
           return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def save_dict_as_json(data, dirr, base_name):

    # Create a json dump
    json_dump = json.dumps(data, cls=NumpyEncoder)
    # Write the data to file, the whole dic
    with open(os.path.join(dirr, "{}.json".format(base_name)), 'w') as outfile:
        json.dump(json_dump, outfile)

    # Save the individual data files/measurements
    if "data" in data:
        pass
        # If only one data set is present save each indvidual mesaurement array
        # I dont like that therefor I excluded it, so far no one has complained
        #for key in data["data"]:
        #    with open(os.path.join(dirr, base_name, "data", "{}.json".format(key)), 'w') as outfile:
        #        json_dump = json.dumps(data["data"][key], cls=NumpyEncoder)
        #        json.dump(json_dump, outfile)
    else:
        #os.mkdir(os.path.join(dirr, base_name)) if not os.path.exists(os.path.join(dirr, base_name)) else True
        os.mkdir(os.path.join(dirr, "singledata")) if not os.path.exists(
            os.path.join(dirr, "singledata")) else True
        # If the data contains several measurement json files eg from the plotter
        for name, file in data.items():
             with open(os.path.join(dirr, "singledata", "{}.json".format(name)), 'w') as outfile:
                    json_dump = json.dumps(file, cls=NumpyEncoder)
                    json.dump(json_dump, outfile)

def save_dict_as_hdf5(data, dirr, base_name):
    df = convert_to_df(data)
    df["All"].to_hdf(os.path.join(dirr, base_name+".hdf5"), key='df', mode='w')
    os.mkdir(os.path.join(dirr, "singledata")) if not os.path.exists(
        os.path.join(dirr, "singledata")) else True
    for key in df.get("keys", []):
        data[key]["data"].to_hdf(os.path.join(dirr, "singledata", "{}.hdf5".format(key)), key='df', mode='w')

def save_dict_as_xml(data_dict, filepath, name):
    from json import loads
    from dicttoxml import dicttoxml
    from xml.dom.minidom import parseString
    """
    Writes out the data as xml file, for the CMS DB

    :param filepath: Filepath where to store the xml
    :param name: name of the file 
    :param data_dict: The data to store in this file. It has to be the dict representation of the xml file
    :return:
    """
    file = os.path.join(os.path.normpath(filepath), name.split(".")[0]+".xml")
    if isinstance(data_dict, dict):
        xml = dicttoxml(data_dict, attr_type=False)
        dom = parseString(xml) # Pretty print style
        with open(file, "w+") as fp:
            fp.write(dom.toprettyxml())
    elif isinstance(data_dict, str):
        xml = dicttoxml(loads(data_dict), attr_type=False)
        dom = parseString(xml)  # Pretty print style
        with open(file, "wb") as fp:
            fp.write(dom.toprettyxml())
    else:
        l.error("Could not save data as xml, the data type is not correct. Must be dict or json")

def send_TCP_message(client, action, message):
    """
    This function sends a message to a IP address. This function will run in a new thread. This way the framework
    will not be halted should the connection fail, or wait for a timeout
    :param client: The client instance from server_connections.py
    :param action: An action flag, can be used as identifier
    :param message: The Message to be sent to the server
    :return: bool, if successful or not
    """

    def func(client, action, message):
        try:
            l.info("Sending server request with action: {} and message: {}".format(action, message))
            response = client.send_request(str(action), message)
        except Exception as err:
            l.info("Server Error {}".format(err))
            return False
        l.info("Server responded with {}".format(response))
        if response:
            return True
        else:
            l.info("Server seems to be offline.".format(response))
            return False

    if client:
        x = Thread(target=func, args=(client, action, message))
        x.run()
    else:
        l.warning("No client defined for sending TCP packages. No message dispatched!")

def send_telegram_message(person, message, configs, client):
    """
    Searches for a TelegramBot entry in the configs and then searches for the person and sends a TCP packages
    to the telegram bot. Warning: This does not guarantee a successfull message dispatch!
    :param person: The person the message should be sent to
    :param message: The actuall message - the function handles the the parsing. All python data types are valid
    :param configs: The config dict
    :param client: The TCP client over which the message must be send
    :return: bool
    """
    # Telegram bot - Find user and its ID
    if "TelegramBot" in configs:
        if person in configs["TelegramBot"]:
            l.debug("Operator found to send telegram message to. Operator: {}".format(person))
            send_TCP_message(client, "TelegramBot", {str(configs["TelegramBot"][person]): message})
        else:
            l.debug("No telegram ID defined for Operator: {}. No message send. Message: {}".format(person, message))
            return False
    else:
        l.debug("Not TelegramBot entry in the configs, no message dispatch: Message: {}".format(message))
        return False
