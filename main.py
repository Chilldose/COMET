

#import os
#os.system("conda info --envs")

__author__  = "Dominic Bloech"
__email__   = "dominic.bloech@oeaw.ac.at"
__date__    = "15.09.2017"
__beta__    = "20.12.2017"
__release__ = "28.05.2018"
__version__ = "0.10.0"

#---------------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------------
# This program is developed for IV/CV measurements as well as strip scan measurements for the QTC setup at HEPHY Vienna.
# All rights are to the Programmer(s) and the HEPHY Vienna.
# Distributing/using this software without permission of the programmer will be punished!
# - Punishments: Death by hanging, Decapitation and/or ethernal contemption
# - Should the defendant demand trail by combat, than the combat will be three rounds of "rock-paper-scissors-lizard-spock"
#   If the defendant should win, he/she can use the software as he/she wishes, otherwise he/she will be punished as described before.
#---------------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------------

import time
start_time = time.time()
threads = [] # List all active threads started from the main

print("Initializing programm, version {} ...".format(__version__))
from UniDAQ.utilities import *
log = LogFile("INFO") #Initiates the log file
l = logging.getLogger(__name__) # gets me the logger
l.info("Logfile initiated")
from UniDAQ.boot_up import *

# Checking installation
check_installation()

# Loading all modules
sys.stdout.write("Loading modules ... ")
import os, visa, scipy, PyQt5, datetime, threading, sys, yaml, importlib, re, types
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget
import datetime
from UniDAQ.VisaConnectWizard import *
from UniDAQ.GUI_event_loop import *
from UniDAQ.GUI_classes import *
from UniDAQ.measurement_event_loop import *
from UniDAQ.measurements import *
from UniDAQ.cmd_inferface import *
from UniDAQ.bad_strip_detection import *
from threading import Thread
from UniDAQ.engineering_notation import *
from UniDAQ.GUI_classes import *
from UniDAQ.measurement_event_loop import *
from UniDAQ.measurements import *
from UniDAQ.cmd_inferface import *
from UniDAQ.bad_strip_detection import *

print("Done \n")


# Loading all init files and default files, as well as Pad files
print("Loading setup files ...")
stats = loading_init_files(hf)
stats.default_values_dict = update_defaults_dict().update(stats.default_values_dict)
print("Done \n")

# Initializing all modules
sys.stdout.write("Initializing modules ... ")
shell = DAQShell()
hf = help_functions()
vcw = VisaConnectWizard.VisaConnectWizard()
print("Done \n")




# Tries to connect to all available devices in the network, it returns a dict of a dict
# First dict contains the the device names as keys, the value is a dict containing key words of settings
print("Try to connect to devices ...")
devices_dict = connect_to_devices(vcw, stats.devices_dict).get_new_device_dict() # Connects to all devices and initiates them and returns the updated device_dict with the actual visa resources
print("Done \n")

print("Starting the event loops ... ")
table = table_control_class(stats.default_values_dict, devices_dict, message_to_main, shell, vcw)
if "Table_control" not in devices_dict:
    table = None
switching = switching_control(stats.default_values_dict, devices_dict, message_to_main, shell)
thread1 = newThread(1, "Measurement event loop", measurement_event_loop, devices_dict, stats.default_values_dict, stats.pad_files_dict, vcw, table, switching, shell) # Starts a new Thread for the measurement event loop
# Add threads to thread list and starts running it
threads.append(thread1)

# Starts all threads in the list of threads (this starts correspond to the threading class!!!)
for thread in threads:
    thread.start()
print("Done\n")

print("Starting GUI ...")
GUI = GUI_classes(message_from_main, message_to_main, devices_dict, stats.default_values_dict, stats.pad_files_dict, hf, vcw, queue_to_GUI, table, switching, shell)
frame = Framework(GUI.give_framework_functions) # Init the framework for update plots etc.
timer = frame.start_timer() # Starts the timer

print("Starting shell...")
shell.start()

print("Start rendering GUI...")
GUI.app.exec_() # Starts the actual event loop for the GUI

# Wait for all threads to complete
l.info("Joining threads...")
# Close the shell by sending the by command
shell.onecmd("bye")
for t in threads:
    t.join() # Synchronises the threads so that they finish all at ones.

end_time = time.time()

message = "Run time: {} seconds.".format(round(end_time - start_time, 2))
print(message)
l.info(message)

message = "Reset all devices..."
print(message)
l.info(message)

for device in devices_dict:  # Loop over all devices
    if "Visa_Resource" in devices_dict[device]:  # Looks if a Visa resource is assigned to the device.

        # Initiate the instrument and resets it
        if "reset_device" in devices_dict[device]:
            vcw.initiate_instrument(devices_dict[device]["Visa_Resource"], devices_dict[device]["reset_device"], devices_dict[device].get("execution_terminator", ""))
        else:
            vcw.initiate_instrument(devices_dict[device]["Visa_Resource"], ["*rst", "*cls", "TRAC:CLE"],devices_dict[device].get("execution_terminator", ""))

message = "Close visa connections..."
print(message)
l.info(message)
vcw.close_connections()

#print("Save current settings...")
#try:
#    os.remove(os.path.join(os.path.dirname(os.path.realpath(__file__)), "init", "default", "defaults.yaml"))
#except Exception as e:
#    print(e)
#for keys in update_defaults_dict().to_update().keys():
#    if keys in stats.default_values_dict["Defaults"]:
#        stats.default_values_dict["Defaults"].pop(keys)
#hf.write_init_file("defaults", stats.default_values_dict["Defaults"], os.path.join(os.path.dirname(os.path.realpath(__file__)), "init", "default"))

message = "Exiting Main Thread"
print(message)
l.info(message)

sys.exit(0)
