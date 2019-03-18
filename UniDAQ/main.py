#!/usr/bin/env python

"""
UniDAQ

This program is developed for IV/CV measurements as well as strip scan
measurements for the QTC setup at HEPHY Vienna.
All rights are to the Programmer(s) and the HEPHY Vienna.
Distributing/using this software without permission of the programmer will be
punished!
 - Punishments: Death by hanging, Decapitation and/or ethernal contemption
 - Should the defendant demand trail by combat, than the combat will be three
   rounds of "rock-paper-scissors-lizard-spock".
   If the defendant should win, he/she can use the software as he/she wishes,
   otherwise he/she will be punished as described before.
"""

import logging
import time
import sys
import os

from . import utilities
from . import boot_up
from .GUI_classes import GUI_classes
from .cmd_inferface import DAQShell
from .VisaConnectWizard import VisaConnectWizard
from .measurement_event_loop import (
    measurement_event_loop,
    message_to_main,
    message_from_main,
    queue_to_GUI
)

def main():
    """Main application entry point."""

    # Create timestamp
    start_time = time.time()

    # Initialize logger using configuration
    rootdir = os.path.dirname(os.path.abspath(__file__))
    config = os.path.join(rootdir, "loggerConfig.yml")
    utilities.LogFile(config)

    # Get logger
    log = logging.getLogger(__name__)
    log.info("Logfile initiated...")
    log.critical("Initializing programm:")

    # Creating help functions
    hfs = utilities.help_functions()

    # Checking installation
    #boot_up.check_installation()

    # Loading all config files and default files, as well as Pad files
    log.critical("Loading setup files ...")
    stats = boot_up.loading_init_files(hfs)
    stats.default_values_dict = boot_up.update_defaults_dict(stats.configs["config"], stats.configs["config"].get("framework_variables", {}))

    # Initializing all modules
    log.critical("Initializing modules ...")
    shell = DAQShell()
    vcw = VisaConnectWizard()


    # Tries to connect to all available devices in the network, it returns a dict of
    # a dict. First dict contains the the device names as keys, the value is a dict
    # containing key words of settings
    log.critical("Try to connect to devices ...")
    # Connects to all devices and initiates them and returns the updated device_dict
    # with the actual visa resources
    devices_dict = boot_up.connect_to_devices(vcw, stats.configs.get("device_lib",{})).get_new_device_dict()

    log.critical("Starting the event loops ... ")
    table = utilities.table_control_class(
        stats.configs["config"],
        devices_dict,
        message_to_main,
        shell,
        vcw
    )
    if "Table_control" not in devices_dict:
        table = None
    switching = utilities.switching_control(
        stats.configs["config"],
        devices_dict,
        message_to_main,
        shell
    )

    # Holds all active threads started from the main
    threads = []

    # Starts a new Thread for the measurement event loop
    thread = utilities.newThread(
        1,
        "Measurement event loop",
        measurement_event_loop,
        devices_dict,
        stats.configs["config"],
        stats.configs.get("Pad_files"),
        vcw,
        table,
        switching,
        shell
    )
    # Add threads to thread list and starts running it
    threads.append(thread)

    # Starts all threads (this starts correspond to the threading class!!!)
    for thread in threads:
        thread.start()

    log.critical("Starting GUI ...")
    gui = GUI_classes(
        message_from_main,
        message_to_main,
        devices_dict,
        stats.configs["config"],
        stats.configs.get("Pad_files"),
        hfs,
        vcw,
        queue_to_GUI,
        table,
        switching,
        shell
    )
    # Init the framework for update plots etc.
    frame = utilities.Framework(gui.give_framework_functions)
    # Starts the timer
    frame.start_timer()

    #log.critical("Starting shell...")
    #shell.start()

    log.critical("Start rendering GUI...")
    gui.app.exec_() # Starts the actual event loop for the GUI

    # Wait for all threads to complete
    log.critical("Joining threads...")
    # Close the shell by sending the by command
    #shell.onecmd("bye")
    for thread in threads:
        thread.join() # Synchronises the threads so that they finish all at ones.

    end_time = time.time()

    log.critical("Run time: %s seconds.", round(end_time-start_time, 2))
    log.critical("Reset all devices...")

    # Reset all devices
    utilities.reset_devices(devices_dict, vcw)

    log.critical("Close visa connections...")
    vcw.close_connections()
    log.critical("Exiting Main Thread")
    sys.exit(0)

if __name__ == '__main__':
    main()
