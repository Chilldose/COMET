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
from .VisaConnectWizard import VisaConnectWizard
from .measurement_event_loop import (
    measurement_event_loop,
    message_to_main,
    message_from_main,
    queue_to_GUI
)
from PyQt5.QtWidgets import QApplication, QStyleFactory

def main():
    """Main application entry point."""

    # Create timestamp
    start_time = time.time()

    # Load Style sheet
    StyleSheet = utilities.load_QtCSS_StyleSheet("Qt_Style.css")

    # Create app
    app = QApplication(sys.argv)
    # Set Style of the GUI
    style = "fusion"
    app.setStyle(QStyleFactory.create(style))
    app.setStyleSheet(StyleSheet)
    app.setQuitOnLastWindowClosed(False)

    # Config the except hook
    new_except_hook = utilities.except_hook_Qt()

    # Initialize logger using configuration
    rootdir = os.path.dirname(os.path.abspath(__file__))
    config = os.path.join(rootdir, "loggerConfig.yml")
    utilities.LogFile(config)

    # Get logger
    log = logging.getLogger(__name__)
    log.info("Logfile initiated...")
    log.critical("Initializing programm:")

    # Loading all config files and default files, as well as Pad files
    log.critical("Loading setup files ...")
    stats = boot_up.loading_init_files()
    stats.default_values_dict = boot_up.update_defaults_dict(stats.configs["config"], stats.configs["config"].get("framework_variables", {}))

    # Initializing all modules
    log.critical("Initializing modules ...")
    vcw = VisaConnectWizard()


    # Tries to connect to all available devices in the network, it returns a dict of
    # a dict. First dict contains the the device names as keys, the value is a dict
    # containing key words of settings
    log.critical("Try to connect to devices ...")
    # Connects to all devices and initiates them and returns the updated device_dict
    # with the actual visa resources
    devices_dict = boot_up.connect_to_devices(vcw, stats.configs["config"]["settings"]["Devices"],
                                              stats.configs.get("device_lib", {}))
    devices_dict = devices_dict.get_new_device_dict()

    log.critical("Starting the event loops ... ")
    table = utilities.table_control_class(
        stats.configs["config"],
        devices_dict,
        message_to_main,
        vcw
    )
    if "Table_control" not in devices_dict:
        table = None
    switching = utilities.switching_control(
        stats.configs["config"],
        devices_dict,
        message_to_main,
    )

    # Gather auxiliary modules
    aux = {"Table": table, "Switching": switching,
           "VCW": vcw, "Devices": devices_dict,
           "rootdir": rootdir, "App": app,
           "Message_from_main": message_from_main, "Message_to_main": message_to_main,
           "Queue_to_GUI": queue_to_GUI, "Configs": stats.configs}

    # Starts a new Thread for the measurement event loop
    MEL = measurement_event_loop(aux)
    MEL.start()

    log.critical("Starting GUI ...")
    gui = GUI_classes(aux)
    # Init the framework for update plots etc.
    frame = utilities.Framework(gui.give_framework_functions)
    # Starts the timer
    frame.start_timer()

    log.critical("Start rendering GUI...")
    gui.app.exec_() # Starts the actual event loop for the GUI
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
