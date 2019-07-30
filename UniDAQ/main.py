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
import glob
import argparse
import logging
import signal
import time
import sys
import os

from PyQt5 import QtCore
from PyQt5 import QtWidgets

#sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from . import utilities
from . import boot_up
from .core.config import DeviceLib
from .core.config import Setup
from .gui.PreferencesDialog import PreferencesDialog
from .GUI_classes import GUI_classes
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

    # Load Style sheet
    StyleSheet = utilities.load_QtCSS_StyleSheet("Qt_Style.css")

    # Create app
    app = QtWidgets.QApplication(sys.argv)

    # Create application settings.
    app.setOrganizationName("HEPHY")
    app.setOrganizationDomain("hephy.at")
    app.setApplicationName("comet")

    # Init global settings.
    QtCore.QSettings()

    # Set Style of the GUI
    style = "Fusion"
    app.setStyle(QtWidgets.QStyleFactory.create(style))
    app.setStyleSheet(StyleSheet)
    app.setQuitOnLastWindowClosed(False)

    # Terminate application on SIG_INT signal.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Create a custom exception handler
    sys.excepthook = utilities.exception_handler

    # Initialize logger using configuration
    rootdir = os.path.dirname(os.path.abspath(__file__))
    config = os.path.join(rootdir, "loggerConfig.yml")
    utilities.LogFile(config)

    # Get logger
    log = logging.getLogger(__name__)
    log.info("Logfile initiated...")
    log.critical("Initializing programm:")

    # Parse Arguments
    args = utilities.parse_args()

    # Loading all config files
    active_setup = QtCore.QSettings().value('active_setup', None)
    # The reinit is a overwrite, so the window can be called after e.g. failure with a gui.
    if active_setup is None or args.reinit:
        dialog = PreferencesDialog(None)
        dialog.exec_()
        del dialog
        # Re-load active setup after configuration dialog.
        active_setup = QtCore.QSettings().value('active_setup', None)

    log.critical("Loading setup '%s'...", active_setup)
    # TODO load config
    path = os.path.join(rootdir, 'config', 'device_lib')
    device_lib = DeviceLib()
    device_lib.load(path)

    path = os.path.join(rootdir, 'config', 'Setup_configs', active_setup)
    setup = Setup()
    setup.load(path)

    setup_loader = boot_up.SetupLoader()
    setup_loader.load(active_setup) # TODO
    setup_loader.default_values_dict = boot_up.update_defaults_dict(setup_loader.configs["config"], setup_loader.configs["config"].get("framework_variables", {}))

    # Initializing all modules
    log.critical("Initializing modules ...")
    try:
        vcw = VisaConnectWizard()
    except:
        log.critical("NI-VISA backend could not be loaded, trying with pure python backend for VISA!")
        vcw = VisaConnectWizard("@py")


    # Tries to connect to all available devices in the network, it returns a dict of
    # a dict. First dict contains the the device names as keys, the value is a dict
    # containing key words of settings
    log.critical("Try to connect to devices ...")
    # Connects to all devices and initiates them and returns the updated device_dict
    # with the actual visa resources
    # Cut out all devices which are not specified in the settings
    devices = []
    if "Devices" in setup_loader.configs["config"]["settings"]:
        for to_connect in setup_loader.configs["config"]["settings"]["Devices"].values():
            devices.append(to_connect["Device_name"])
        cuted_device_lib = {x: v for x, v in setup_loader.configs.get("device_lib", {}).items() if x in devices}
        devices_dict = boot_up.connect_to_devices(vcw, setup_loader.configs["config"]["settings"]["Devices"],
                                                  cuted_device_lib)
        devices_dict = devices_dict.get_new_device_dict()
        devices_dict = setup_loader.config_device_notation(devices_dict)
    else:
        devices_dict = {}

    log.critical("Starting the event loops ... ")
    table = utilities.table_control_class(
        setup_loader.configs["config"],
        devices_dict,
        message_to_main,
        vcw
    )
    if "Table_control" not in devices_dict:
        table = None
    switching = utilities.switching_control(
        setup_loader.configs["config"],
        devices_dict,
        message_to_main,
        vcw
    )

    # Gather auxiliary modules
    aux = {"Table": table, "Switching": switching,
           "VCW": vcw, "Devices": devices_dict,
           "rootdir": rootdir, "App": app,
           "Message_from_main": message_from_main, "Message_to_main": message_to_main,
           "Queue_to_GUI": queue_to_GUI, "Configs": setup_loader.configs, "Django": None, "Server": None,
           "Client": None}

    # Starts a new Thread for the measurement event loop
    MEL = measurement_event_loop(aux)
    MEL.start()

    log.critical("Starting GUI ...")
    gui = GUI_classes(aux)
    # Init the framework for update plots etc.
    frame = utilities.Framework(gui.give_framework_functions)
    # Starts the timer
    frame.start_timer()

    # Starting Django Server if need be
    if "Django_server" in aux["Configs"]["config"]["settings"]:
        if aux["Configs"]["config"]["settings"]["Django_server"].get("Start_Server", False):
            log.info("Starting Django server...")
            try:
                config = aux["Configs"]["config"]["settings"]["Django_server"]
                import subprocess
                # Import Server and Client class for communication with the Django server
                from .socket_connections import Client_, Server_
                path = os.path.normpath(config["Path"])#
                Django = subprocess.Popen(["python", path, "runserver", str(config["Port"])], shell=True)
                Server = Server_()
                Server.run() # Starts the Server thread
                Client = Client_()
                aux["Django"] = Django
                aux["Server"] = Server
                aux["Client"] = Client
            except Exception as err:
                log.error("Django server could not be started. Error: {}".format(err))


    log.critical("Start rendering GUI...")
    gui.app.exec_() # Starts the actual event loop for the GUI
    end_time = time.time()

    log.critical("Run time: %s seconds.", round(end_time-start_time, 2))
    log.critical("Reset all devices...")

    log.critical("Close visa connections...")
    vcw.close_connections()
    log.critical("Exiting Main Thread")
    sys.exit(0)

if __name__ == '__main__':
    main()
