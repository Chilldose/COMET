import logging
import sys, os

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
import sys, os
from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5 import QtCore, QtGui
import glob
import yaml
from functools import partial

from .. import utilities

class QCometDialog(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(695, 294)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.OkButton = QtWidgets.QPushButton(self.centralwidget)
        self.OkButton.setGeometry(QtCore.QRect(90, 210, 542, 28))
        self.OkButton.setObjectName("OkButton")
        self.Title = QtWidgets.QLabel(self.centralwidget)
        self.Title.setGeometry(QtCore.QRect(90, 53, 542, 56))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.Title.setFont(font)
        self.Title.setAutoFillBackground(True)
        self.Title.setObjectName("Title")
        self.comboBox_config = QtWidgets.QComboBox(self.centralwidget)
        self.comboBox_config.setGeometry(QtCore.QRect(90, 178, 542, 25))
        self.comboBox_config.setMinimumSize(QtCore.QSize(0, 25))
        self.comboBox_config.setObjectName("comboBox_config")
        self.Infotext = QtWidgets.QLabel(self.centralwidget)
        self.Infotext.setGeometry(QtCore.QRect(90, 116, 542, 55))
        self.Infotext.setAutoFillBackground(True)
        self.Infotext.setObjectName("Infotext")
        #MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        #MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "COMET Config Assist"))
        self.OkButton.setText(_translate("MainWindow", "Load"))
        self.Title.setText(_translate("MainWindow", "Welcome to COMET - Control and Measurement Toolkit software"))
        self.Infotext.setText(_translate("MainWindow", "It seems that this is the first start of the software.\n"
                                        "COMET supports auto configuration for several setups.\n"
                                        "Please choose which setup you want to configure. "))

class PreferencesDialog(QtWidgets.QDialog):
    """Preferences dialog for application settings."""

    def __init__(self, parent=None):
        super(PreferencesDialog, self).__init__(parent)
        self.diaologBox = QCometDialog()
        self.diaologBox.setupUi(self)
        self.loadSetups()
        self.diaologBox.OkButton.clicked.connect(self.updateSettings)
        self.diaologBox.OkButton.clicked.connect(self.onClose)


    def loadSetups(self):
        """Load available setups."""
        # TODO concentrate paths in a dedicated module, eg. paths.config_dir
        location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'Setup_configs')
        items = utilities.get_available_setups(location)
        self.diaologBox.comboBox_config.clear()
        self.diaologBox.comboBox_config.addItems(items)

    def loadSettings(self):
        """Load settings to dialog widgets."""
        activeSetup = QtCore.QSettings().value('active_setup')
        setCurrentEntry(self.setupComboBox, activeSetup)
        plotStyle = QtCore.QSettings().value('plot_style')
        setCurrentEntry(self.plotsComboBox, plotStyle)

    def writeSettings(self):
        """Write settings from dialog widgets."""
        activeSetup = self.setupComboBox.currentText()
        QtCore.QSettings().setValue('active_setup', activeSetup)
        logging.info("active setup: %s", activeSetup)
        plotStyle = self.plotsComboBox.currentText()
        QtCore.QSettings().setValue('plot_style', plotStyle)
        logging.info("plot style: %s", plotStyle)

        self.close()
        # todo: delete one 
    def onClose(self):
        """On dialog close."""
        # self.updateSettings() # TODO currently holding back
        self.close()

    def onAccept(self):
        """On dialog accept (apply button was clicked)."""
        self.writeSettings()
        self.accept()
