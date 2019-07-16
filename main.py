

#import os
#os.system("conda info --envs")

__author__  = "Dominic Bloech"
__email__   = "dominic.bloech@oeaw.ac.at"
__date__    = "15.09.2017"
__beta__    = "20.12.2017"
__release__ = "28.05.2018"
__version__ = "0.9.15"

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



print "Initializing programm:"
from modules.utilities import *
log = LogFile("INFO") #Initiates the log file
l = logging.getLogger(__name__) # gets me the logger
l.info("Logfile initiated")
from modules.boot_up import *

# Checking installation
ci = check_installation()

# Loading all modules
print "Loading modules ... ",
import os, visa, scipy, PyQt5, datetime, threading, Queue, sys, yaml, importlib, re, types
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget
import datetime
from modules.VisaConnectWizard import *
from modules.GUI_event_loop import *
from modules.GUI_classes import *
from modules.measurement_event_loop import *
from modules.measurements import *
from modules.cmd_inferface import *
from modules.bad_strip_detection import *
from threading import Thread
from modules.engineering_notation import *
print "Done \n"


# Loading all init files and default files, as well as Pad files
print "Loading setup files ...",
stats = loading_init_files(hf)
stats.default_values_dict = update_defaults_dict().update(stats.default_values_dict)
print "Done \n"

# Initializing all modules
print "Initializing modules ...",
shell = DAQShell()
hf = help_functions()
vcw = VisaConnectWizard.VisaConnectWizard()
print "Done \n"


# Tries to connect to all available devices in the network, it returns a dict of a dict
# First dict contains the the device names as keys, the value is a dict containing key words of settings
print "Try to connect to devices ...",
devices_dict = connect_to_devices(vcw, stats.devices_dict).get_new_device_dict() # Connects to all devices and initiates them and returns the updated device_dict with the actual visa resources
print "Done \n"

print "Starting the event loops ... "
table = table_control_class(stats.default_values_dict, devices_dict, message_to_main, shell, vcw)
if "Table_control" not in devices_dict:
    table = None
switching = switching_control(stats.default_values_dict, devices_dict, message_to_main, shell)
thread1 = newThread(1, "Measurement event loop", measurement_event_loop, devices_dict, stats.default_values_dict, stats.pad_files_dict, vcw, table, switching, shell) # Starts a new Thread for the measurement event loop
# Add threads to thread list and starts running it
threads.append(thread1)

# Starts all threads in the list of threads (this starts correspond to the threading class!!!)
map(lambda thread: thread.start(), threads)
print "Done\n"


print "Starting GUI ..."
GUI = GUI_classes(message_from_main, message_to_main, devices_dict, stats.default_values_dict, stats.pad_files_dict, hf, vcw, queue_to_GUI, table, switching, shell)
frame = Framework(GUI.give_framework_functions) # Init the framework for update plots etc.
timer = frame.start_timer() # Starts the timer

print "Starting shell..."
shell.start()
#print dir(shell.__class__)
#shellThread = Thread(target= DAQShell)
#shellThread.start()
#threads.append(shellThread)




print "Start rendering GUI..."
GUI.app.exec_() # Starts the actual event loop for the GUI

# Wait for all threads to complete
l.info("Joining threads...")
# Close the shell by sending the by command
shell.onecmd("bye")
for t in threads:
    t.join() # Synchronises the threads so that they finish all at ones.


end_time = time.time()

print "Run time: " + str(round(end_time-start_time,2)) + " seconds."
l.info("Run time: " + str(round(end_time-start_time,2)) + " seconds.")

print "Reset all devices..."
l.info("Reset all devices...")

for device in devices_dict:  # Loop over all devices
    if devices_dict[device].has_key("Visa_Resource"):  # Looks if a Visa resource is assigned to the device.

        # Initiate the instrument and resets it
        if "reset_device" in devices_dict[device]:
            vcw.initiate_instrument(devices_dict[device]["Visa_Resource"], devices_dict[device]["reset_device"], devices_dict[device].get("execution_terminator", ""))
        else:
            vcw.initiate_instrument(devices_dict[device]["Visa_Resource"], ["*rst", "*cls", "TRAC:CLE"],devices_dict[device].get("execution_terminator", ""))

print "Close visa connections..."
l.info("Close visa connections...")
vcw.close_connections()

#print "Save current settings..."
#try:
#    os.remove(str(os.path.abspath(os.path.realpath(__file__)[:-8] + "/init/default/" + "defaults.yaml")))
#except Exception, e:
#    print e
#for keys in update_defaults_dict().to_update().keys():
#    if keys in stats.default_values_dict["Defaults"]:
#        stats.default_values_dict["Defaults"].pop(keys)
#hf.write_init_file("defaults", stats.default_values_dict["Defaults"], str(os.path.abspath(os.path.realpath(__file__)[:-8] + "/init/default/")))

print "Exiting Main Thread"
l.info("Exiting Main Thread")
sys.exit(0)