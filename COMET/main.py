#!/usr/bin/env python

"""
COMET

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
import signal
import time
import sys
import os
from . import utilities
from . import boot_up
from .measurement_event_loop import (
    measurement_event_loop,
    message_to_main,
    message_from_main,
    queue_to_GUI,
)

from .gui.PreferencesDialog import PreferencesDialog
from .GUI_classes import GUI_classes

from PyQt5 import QtCore
from PyQt5 import QtWidgets

try:
    # QtWebEngineWidgets must be imported before a QCoreApplication instance is created, but not all systems have it installed
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from .VisaConnectWizard import VisaConnectWizard
except:
    pass


def main():
    """Main application entry point."""

    # Add some pathes to make things easier
    sys.path.append(os.path.abspath("COMET/"))
    sys.path.append(os.path.abspath("COMET/resources"))
    sys.path.append(os.path.abspath("COMET/misc_plugins"))

    # Parse Arguments
    args = utilities.parse_args()

    # Create timestamp
    start_time = time.time()
    rootdir = os.path.dirname(os.path.abspath(__file__))

    # Load Style sheet
    config = os.path.join(rootdir, "resources/Qt_Style.css")
    StyleSheet = utilities.load_QtCSS_StyleSheet(config)

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

    # Initialize logger using configuration
    config = os.path.join(rootdir, "loggerConfig.yml")
    utilities.LogFile(config)

    # Get logger
    log = logging.getLogger(__name__)
    log.info("Logfile initiated...")
    log.critical("Initializing program:")

    # Check the environment if something has changed
    if args.update:
        log.critical("Try getting Git remote repo...")
        try:
            import git

            repo = git.Repo()
            o = repo.remotes.origin
            log.info(o.fetch())
            log.info(o.pull())
        except Exception as err:
            log.error(
                "An error happened while updating COMET source code.", exc_info=True
            )

        log.critical("Checking conda environment requirements...")
        try:
            osType = sys.platform
            if "win" in osType.lower():
                version = "COMET/resources/requirements_Winx86.yml"
            elif "linux" in osType.lower():
                version = "COMET/resources/requirements_LINUX_x86_64.yml"
            else:
                version = "COMET/resources/requirements_MacOS.yml"
            os.system(
                "conda env update --prefix ./env --file {}  --prune".format(version)
            )
        except Exception as err:
            log.error(
                "An error happened while updating COMET environment.", exc_info=True
            )

        log.critical("Please restart COMET for the updates to have an effect!")
        sys.exit(0)

    # Create a custom exception handler
    if not args.minimal:
        try:
            sys.excepthook = utilities.exception_handler
        except Exception as err:
            log.critical(
                "Except hook handler could not be loaded! Error: {}".format(err)
            )

    # Loading all config files
    if args.loadGUI:
        QtCore.QSettings().setValue("active_setup", args.loadGUI)

    active_setup = QtCore.QSettings().value("active_setup", None)
    # The reinit is a overwrite, so the window can be called after e.g. failure with a gui.
    if active_setup is None or args.reinit:
        dialog = PreferencesDialog(None)
        dialog.exec_()
        del dialog
        # Re-load active setup after configuration dialog.
        active_setup = QtCore.QSettings().value("active_setup", None)

    log.critical("Loading setup '%s'...", active_setup)

    setup_loader = boot_up.SetupLoader()
    setup_loader.load(active_setup)  # TODO
    setup_loader.default_values_dict = boot_up.update_defaults_dict(
        setup_loader.configs["config"],
        setup_loader.configs["config"].get("framework_variables", {}),
    )

    # Initializing all modules
    log.critical("Initializing modules ...")
    try:
        vcw = VisaConnectWizard()
    except:
        try:
            log.critical(
                "NI-VISA backend could not be loaded, trying with pure python backend for VISA!"
            )
            vcw = VisaConnectWizard("@py")
        except:
            log.critical(
                "Pure python backend for VISA backend could not be loaded either. No ConnectWizard initiated..."
            )
            vcw = None

    # Tries to connect to all available devices in the network, it returns a dict of
    # a dict. First dict contains the the device names as keys, the value is a dict
    # containing key words of settings
    log.critical("Try to connect to devices ...")
    # Connects to all devices and initiates them and returns the updated device_dict
    # with the actual visa resources
    # Cut out all devices which are not specified in the settings
    devices = []
    if "Devices" in setup_loader.configs["config"]["settings"]:
        for to_connect in setup_loader.configs["config"]["settings"][
            "Devices"
        ].values():
            devices.append(to_connect["Device_name"])
        # cuted_device_lib = {x: v for x, v in setup_loader.configs.get("device_lib", {}).items() if x in devices}
        devices_dict = boot_up.connect_to_devices(
            vcw,
            setup_loader.configs["config"]["settings"]["Devices"],
            setup_loader.configs.get("device_lib", {}),
        )
        devices_dict = devices_dict.get_new_device_dict()
        devices_dict = setup_loader.config_device_notation(devices_dict)
    else:
        devices_dict = {}
        log.warning("No devices specified in the settings...")

    log.critical("Starting the event loops ... ")

    if "Table_control" not in devices_dict or args.minimal:
        table = None
    else:
        table = utilities.table_control_class(
            setup_loader.configs["config"], devices_dict, message_to_main, vcw
        )

    switching = utilities.switching_control(
        setup_loader.configs["config"], devices_dict, message_to_main, vcw
    )

    # Gather auxiliary modules
    aux = {
        "Table": table,
        "Switching": switching,
        "VCW": vcw,
        "Devices": devices_dict,
        "rootdir": rootdir,
        "App": app,
        "Message_from_main": message_from_main,
        "Message_to_main": message_to_main,
        "Queue_to_GUI": queue_to_GUI,
        "Configs": setup_loader.configs,
        "Django": None,
        "Server": None,
        "Client": {},
        "background_Env_task": None,
        "args": args,
    }

    # Starts a new Thread for the measurement event loop
    MEL = measurement_event_loop(aux)
    aux["MEL"] = MEL
    MEL.start()

    # Starting Django Server if need be
    if "Django_server" in aux["Configs"]["config"]["settings"]:
        if aux["Configs"]["config"]["settings"]["Django_server"].get(
            "Start_Server", False
        ):
            log.info(
                "Starting Django server at {}:{}...".format(
                    aux["Configs"]["config"]["settings"]["Django_server"]["IP"],
                    aux["Configs"]["config"]["settings"]["Django_server"]["Port"],
                )
            )
            try:
                config = aux["Configs"]["config"]["settings"]["Django_server"]
                import subprocess

                # Import Server and Client class for communication with the Django server

                path = os.path.normpath(config["Path"])  #
                Django = subprocess.Popen(
                    [
                        "python",
                        path,
                        "runserver",
                        str(config["IP"]) + ":" + str(config["Port"]),
                    ],
                    shell=True,
                )
                aux["Django"] = Django

            except Exception as err:
                log.error("Django server could not be started.", exc_info=True)

    if "Socket_connection" in aux["Configs"]["config"]["settings"]:
        from .misc_plugins.ServerClientApp.socket_connections import Client_, Server_

        config_socket = aux["Configs"]["config"]["settings"]["Socket_connection"]
        try:
            if "Host" in config_socket:
                Server = Server_(
                    HOST=config_socket["Host"]["IP"], PORT=config_socket["Host"]["Port"]
                )
                Server.start()  # Starts the Server thread
                aux["Server"] = Server
        except:
            log.error("TCP server connection could not be started.", exc_info=True)
        try:
            if "Client" in config_socket:
                aux["Client"] = {}
                for name, client in config_socket["Client"].items():
                    Client = Client_(HOST=client["IP"], PORT=client["Port"])
                    aux["Client"][name] = Client
        except:
            log.error(
                "Some TCP clients connection could not be started.", exc_info=True
            )

    log.critical("Starting GUI ...")
    gui = GUI_classes(aux)
    aux["GUI"] = gui
    # Init the framework for update plots etc.
    frame = utilities.Framework(gui.give_framework_functions)
    aux["framework_functions"] = frame
    # Starts the timer
    frame.start_timer()

    log.critical("Start rendering GUI...")
    if args.fullscreen:  # Shows the app in fullscreen mode
        gui.main_window.showFullScreen()
        log.critical("App started in fullscreen mode...")
    gui.app.exec_()  # Starts the actual event loop for the GUI
    end_time = time.time()

    log.critical("Run time: %s seconds.", round(end_time - start_time, 2))
    log.critical("Reset all devices...")

    log.critical("Close visa connections...")
    vcw.close_connections()
    log.critical("Exiting Main Thread")
    sys.exit(0)


if __name__ == "__main__":
    main()
