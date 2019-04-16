#  KeyboardInputDemoQt.py  (c) Kari Laitinen

#  http://www.naturalprogramming.com

#  2009-12-02  File created.
#  2009-12-09  Last modification.

#  This program shows how to react to key pressings
#  in a Qt program.

#  http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/html/qkeyevent.html


import os, sys, os.path, re
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
#from .VisaConnectWizard import VisaConnectWizard
import logging
#from .engineering_notation import EngUnit
import queue
#from .globals import message_to_main, message_from_main, queue_to_GUI



class KeyboardInputDemoWindow(QtGui.QWidget):
    def __init__(self, parent=None):

        QtGui.QWidget.__init__(self, parent)

        self.setGeometry(100, 200, 800, 400)

        self.setWindowTitle("PRESS THE KEYS OF YOUR KEYBOARD")

        self.code_of_last_pressed_key = 63  # The question mark ?

        #self.large_font = QtCore.Qt.QFont("SansSerif", 20)

        # The following statement may help to get keyboard input
        # to this window.

        #self.setFocusPolicy(Qt.StrongFocus)

    #  The following methods will be called by the program
    #  execution system whenever keys of the keyboard are pressed.
    #  They receive a QKeyEvent object as a parameter.


    def keyPressEvent(self, event):

        self.code_of_last_pressed_key = event.key()

        self.update()

    def keyReleaseEvent(self, event):

        pass
        # print  "key release event"   #  This is Python 2.x statement.
        # print( "key release event" )  #  Python 3.x statement.

    def paintEvent(self, event):

        painter = QtCore.Qt.QPainter()

        painter.begin(self)

        painter.setFont(self.large_font)

        #  The format specifier %c treats an integer value as a character,
        #  but the integer value must be less than 256.
        #  %s converts an object to a string.
        #  %X shows an integer in hexadecimal form.

        if self.code_of_last_pressed_key < 256:

            text_to_show_as_string = "Last pressed key: %c %X %d" % \
                                     (self.code_of_last_pressed_key,
                                      self.code_of_last_pressed_key,
                                      self.code_of_last_pressed_key)
        else:

            text_to_show_as_string = "Last pressed key: %s %X %d" % \
                                     (self.code_of_last_pressed_key,
                                      self.code_of_last_pressed_key,
                                      self.code_of_last_pressed_key)

        painter.drawText(100, 200, text_to_show_as_string)

        if self.code_of_last_pressed_key == QtCore.Qt.Key_F1:

            painter.drawText(100, 250, "You pressed the F1 key")

        elif self.code_of_last_pressed_key == QtCore.Qt.Key_Up:

            painter.drawText(100, 250, "You pressed the Arrow Up key")

        elif self.code_of_last_pressed_key == QtCore.Qt.Key_Down:

            painter.drawText(100, 250, "You pressed the Arrow Down key")

        painter.end()


# The main program begins.

this_application = QApplication(sys.argv)

application_window = KeyboardInputDemoWindow()

application_window.show()

this_application.exec_()
