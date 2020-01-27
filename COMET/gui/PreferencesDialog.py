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
from PyQt5 import uic


from .. import utilities

def setCurrentEntry(widget, text):
    """Set current combo box entry by test, provided for convenince."""
    index = widget.findText(text)
    if index >= 0:
        widget.setCurrentIndex(index)

class PreferencesDialog(QtWidgets.QDialog):
    """Preferences dialog for application settings."""

    def __init__(self, parent=None):
        super(PreferencesDialog, self).__init__(parent)
        dialogBox, QtBaseClass = uic.loadUiType(
            os.path.join(os.getcwd(),
            os.path.normpath("COMET/QT_Designer_UI/PreferenceDialog.ui")
                         ))
        self.diaologBox = dialogBox()
        self.diaologBox.setupUi(self)
        self.loadSetups()
        self.loadSettings()
        self.diaologBox.OkButton.clicked.connect(self.writeSettings)
        self.diaologBox.OkButton.clicked.connect(self.onClose)


    def loadSetups(self):
        """Load available setups."""
        # TODO concentrate paths in a dedicated module, eg. paths.config_dir
        location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'Setup_configs')
        items = utilities.get_available_setups(location)
        self.diaologBox.setupComboBox.clear()
        self.diaologBox.setupComboBox.addItems(items)
        self.diaologBox.plotsComboBox.clear()
        self.diaologBox.plotsComboBox.addItems(["light", "dark"])

    def loadSettings(self):
        """Load settings to dialog widgets."""
        activeSetup = QtCore.QSettings().value('active_setup')
        setCurrentEntry(self.diaologBox.setupComboBox, activeSetup)
        plotStyle = QtCore.QSettings().value('plot_style')
        setCurrentEntry(self.diaologBox.plotsComboBox, plotStyle)

    def writeSettings(self):
        """Write settings from dialog widgets."""
        activeSetup = self.diaologBox.setupComboBox.currentText()
        QtCore.QSettings().setValue('active_setup', activeSetup)
        logging.info("active setup: %s", activeSetup)
        plotStyle = self.diaologBox.plotsComboBox.currentText()
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
