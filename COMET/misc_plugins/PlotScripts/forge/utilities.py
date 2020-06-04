"""This module provides some basic tools for the plotting to work"""


import os, sys, os.path
from time import time
import time
import ast
import yaml, json
from copy import deepcopy
import logging.config
import datetime
import logging
import traceback
import re
import importlib

l = logging.getLogger("utilities")


def get_image_size(fname):
    """Determine the image type of fhandle and return its size.
    from draco"""
    import struct
    import imghdr

    with open(fname, "rb") as fhandle:
        head = fhandle.read(24)
        if len(head) != 24:
            return
        if imghdr.what(fname) == "png":
            check = struct.unpack(">i", head[4:8])[0]
            if check != 0x0D0A1A0A:
                return
            width, height = struct.unpack(">ii", head[16:24])
        elif imghdr.what(fname) == "gif":
            width, height = struct.unpack("<HH", head[6:10])
        elif imghdr.what(fname) == "jpeg":
            try:
                fhandle.seek(0)  # Read 0xff next
                size = 2
                ftype = 0
                while not 0xC0 <= ftype <= 0xCF:
                    fhandle.seek(size, 1)
                    byte = fhandle.read(1)
                    while ord(byte) == 0xFF:
                        byte = fhandle.read(1)
                    ftype = ord(byte)
                    size = struct.unpack(">H", fhandle.read(2))[0] - 2
                # We are at a SOFn block
                fhandle.seek(1, 1)  # Skip `precision' byte.
                height, width = struct.unpack(">HH", fhandle.read(4))
            except Exception:  # IGNORE:W0703
                return
        else:
            return
        return width, height


def line_intersection(line1, line2):
    """Usage: line_intersection((A, B), (C, D))"""
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        l.warning("Lines does not intersect...")
        return None

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y


def reload_plugins(plugins):
    """Reloads plugins"""
    l.debug("Reloading analysis plugins...")
    for module in plugins.values():
        importlib.reload(module)


def load_plugins(settings, rootdir):
    # Load all measurement functions
    to_ignore = ["__init__", "__pycache__"]
    all_measurement_functions = os.listdir(os.path.join(rootdir, "analysis_scripts"))
    all_measurement_functions = list(
        set([modules.split(".")[0] for modules in all_measurement_functions])
    )

    all_plugins = {}

    l.debug("All plugin scripts found: " + str(all_measurement_functions) + ".")

    # import all modules specified in the measurement order, so not all are loaded
    for modules in settings["Analysis"]:
        if modules in all_measurement_functions:
            all_plugins.update(
                {modules: importlib.import_module("analysis_scripts." + modules)}
            )
            l.debug("Imported module: {}".format(modules))
        else:
            if modules not in to_ignore:
                l.error(
                    "Could not load module: {}. It was specified in the settings but"
                    " no module matches this name.".format(modules)
                )
    return all_plugins


def sanatise_measurement(measurement):
    """Sanatises measurements from brackets etc."""
    final_units = []
    expr = re.compile(r"^(\w+)\W?")
    for unit in measurement:
        new_unit = re.findall(expr, unit)
        if len(new_unit) >= 1:
            final_units.append(new_unit[0])
    return final_units


def sanatise_units(units):
    """Sanatises units from brackets etc."""
    final_units = []
    expr = re.compile(r"\w*\s?\W?(\w+)")
    for unit in units:
        new_unit = re.findall(expr, unit)
        if len(new_unit) >= 1:
            final_units.append(new_unit[0])
    return final_units


def exception_handler(exctype, value, tb):
    """Custom exception handler raising a dialog box.

    Example:
    >>> import sys
    >>> sys.excepthook = exception_handler
    """
    if exctype is not KeyboardInterrupt:
        # Prepare pretty stacktrace
        message = os.linesep.join(traceback.format_tb(tb))
        log = logging.getLogger("Exception raised")
        if log:
            log.error(
                "\nException type: {}\n"
                "Exception value: {}\n"
                "Traceback: {}".format(exctype.__name__, value, message)
            )
    # Pass on exception
    sys.__excepthook__(exctype, value, tb)


def parse_args(config=None):

    import argparse

    # parent_parser = argparse.ArgumentParser(add_help=False)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        "--f",
        "--config",
        "--con",
        "--c",
        help="The init file with all the configs as a yaml styled file",
    )
    parser.add_argument(
        "--dont_show",
        help="Show the plots or not, default is True",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "--save",
        "--s",
        help="Save the plots, default is False",
        action="store_true",
        default=False,
    )
    args = parser.parse_args(config)

    return args


class LogFile:
    """
    This class handles the Logfile for the whole framework
    """

    def __init__(
        self, path="logger.yml", default_level=logging.INFO, env_key="LOG_CFG"
    ):
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
            with open(path, "rt") as f:
                config = yaml.safe_load(f.read())
                # If directory is non existent create it
                # Todo: Here a dir will be made after installation, so if this prohibited go to the other dir
                pathtologfile = config["handlers"]["file"]["filename"].split("/")
                if not os.path.isdir(os.path.join(os.getcwd(), *pathtologfile[:-1])):
                    os.mkdir(os.path.join(os.getcwd(), *pathtologfile[:-1]))
            logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=default_level)

        self.log_LEVELS = {
            "NOTSET": 0,
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
        }

        self.welcome_string = "PlotScripts by Dominic Bloech started...."

        # Create a logger Object
        self.LOG = logging.getLogger("Logfile")
        # Print welcome message
        self.LOG.info(self.welcome_string)


def int2dt(ts, ts_mult=1e3):
    """
    Convert seconds value into datatime struct which can be used for x-axis labeeling
    """
    return datetime.datetime.utcfromtimestamp(float(ts) / ts_mult)


def get_timestring_from_int(time_array, format="%H:%M:%S"):
    """
    Converts int time to timestring
    """
    list = []
    for value in time_array:
        list.append((value, int2dt(value, 1).strftime(format)))
    return list


def get_thicks_for_timestamp_plot(
    time_array, max_number_of_thicks=10, format="%H:%M:%S"
):
    """
    This gives back a list of tuples for the thicks
    """
    final_thicks = []
    if len(time_array) <= max_number_of_thicks:
        final_thicks = get_timestring_from_int(time_array, format)
    else:
        length = len(time_array)
        delta = int(length / max_number_of_thicks)
        for i in range(0, length, delta):
            final_thicks.append(
                (time_array[i], int2dt(time_array[i], 1).strftime(format))
            )
    return final_thicks


class CAxisTime:  # pg.AxisItem):
    """Over riding the tickString method by extending the class"""

    # @param[in] values List of time.
    # @param[in] scale Not used.
    # @param[in] spacing Not used.
    def tickStrings(values, scale, spacing):
        """Generate the string labeling of X-axis from the seconds value of Y-axis"""
        # sending a list of values in format "HH:MM:SS.SS" generated from Total seconds.
        return [(int2dt(value).strftime("%H:%M:%S.%f"))[:-4] for value in values]

    def int2dt(ts, ts_mult=1e3):
        """Convert seconds value into datatime struct which can be used for x-axis labeeling"""
        return datetime.utcfromtimestamp(float(ts) / ts_mult)


def create_new_file(
    filename="default.txt", filepath="default_path", os_file=True, suffix=".txt"
):
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

    # First check if Filename already exists, if so, add a counter to the file.
    if os.path.isfile(os.path.abspath(filepath + filename + suffix)):
        l.warning("Warning filename " + str(filename) + " already exists!")
        filename = filename + "_" + str(count)  # Adds suffix to filename
        while os.path.isfile(
            os.path.abspath(filepath + filename + suffix)
        ):  # checks if file exists
            count += 1
            countlen = len(str(count))
            filename = filename[:-countlen] + str(count)
        l.info("Filename changed to " + filename + ".")

    filename += str(suffix)
    if os_file:
        fp = os.open(
            os.path.abspath(filepath + filename), os.O_WRONLY | os.O_CREAT
        )  # Creates the file
    else:
        fp = open(os.path.abspath(filepath + filename), "w")

    l.info("Generated file: " + str(filename))

    return fp, count


# Opens a file for reading and writing


def open_file(filename="default.txt", filepath="default_path"):
    """
    Just opens a file and returns the file pointer

    :return: File
    """

    if filepath == "default_path":
        filepath = ""

    try:
        fp = open(filepath + filename, "r+")  # Opens file for reading and writing
        return fp
    except IOError:
        l.error(str(filepath + filename) + " is not an existing file.")


# Closes a file (just needs the file pointer)


def close_file(fp):
    """
    Closed the file specified in param fp

    """
    try:
        try:
            os.close(fp)
        except:
            fp.close()
    except GeneratorExit:
        l.error("Closing the file: " + str(fp) + " was not possible", exc_info=True)
    except:
        l.error("Unknown error occured, while closing file " + str(fp), exc_info=True)


# This flushes a string to a file


def flush_to_file(fp, message):
    """
    Flushes data to a opend file
    Only strings or numbers allowed, Lists will work too but may cause data scrambling
    Only use this with created files from function 'create_new_file'
    """
    os.write(fp, str.encode(message))  # Writes the message to file
    os.fsync(fp)  # ensures that the data is written on HDD


def write_to_file(content, filename="default.txt", filepath="default_path"):
    """
    This writes content to a file. Be aware, input must be of type 'list' each entry containing the information of one line
    """

    fp = open_file(filename, filepath)

    try:
        for line in content:
            fp.write(str(line))
    except IOError:
        l.error("Writing to file " + filename + " was not possible", exc_info=True)
    except:
        l.error(
            "Unknown error occured, while writing to file " + str(filename),
            exc_info=True,
        )

    close_file(fp)


def read_from_file(filename="default.txt", filepath="default_path"):
    """
    Gives you the content of the file in an list, each list entry is one line of the file (datatype=string)
    Warning: File gets closed after reading
    """

    fp = open_file(filename, filepath)

    try:
        return fp.readlines()
    except IOError:
        l.error("Could not read from file.", exc_info=True)
        return []
    except:
        l.error(
            "Unknown error occured, while reading from file " + str(filename),
            exc_info=True,
        )

    close_file(fp)


# These functions are for reading and writing to files------------------------------------
# -------------------------------------------------------------------------------------end


def load_yaml(path):
    """Loads a yaml file and returns the dict representation of it"""
    with open(os.path.normpath(path), "r") as stream:
        try:
            yaml.add_constructor(
                "!regexp", lambda l, n: re.compile(l.construct_scalar(n))
            )  # For regex
            data = yaml.load(stream, Loader=yaml.FullLoader)
            if isinstance(data, str):
                data = json.loads(data)
            return data
        except yaml.YAMLError as exc:
            l.error(
                "While loading the yml file {} the error: {} happend.".format(path, exc)
            )


def timeit(method):
    """
    Intended to be used as decorator for functions. It returns the time needed for the function to run

    :param method: method to be timed
    :return: time needed by method
    """

    def timed(*args, **kw):
        start_time = time.time()
        result = method(*args, **kw)
        end_time = time.time()

        exce_time = end_time - start_time

        return result, exce_time

    return timed  # here the memberfunction timed will be called


def run_with_lock(method):
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
            l.error(
                "A lock could not be acquired in " + str(method.__name__), exc_info=True
            )  # this is optional but sometime the raise does not work
            raise  # this raises the error with stack backtrace
        return result

    return with_lock  # here the memberfunction timed will be called
