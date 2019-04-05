import logging
import sys, os

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

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
        self.setWindowTitle(self.tr("Preferences"))
        self.setMinimumSize(400, 200)
        # Setup group box
        self.setupGroupBox = QtWidgets.QGroupBox(self.tr("Setup"), self)
        self.setupComboBox = QtWidgets.QComboBox()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.setupComboBox)
        self.setupGroupBox.setLayout(layout)
        # Plots style group box
        self.plotsGroupBox = QtWidgets.QGroupBox(self.tr("Plots style"), self)
        self.plotsComboBox = QtWidgets.QComboBox()
        self.plotsComboBox.addItem(self.tr("dark"))
        self.plotsComboBox.addItem(self.tr("light"))
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.plotsComboBox)
        self.plotsGroupBox.setLayout(layout)
        # Buttonbox
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.onAccept)
        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.setupGroupBox)
        layout.addWidget(self.plotsGroupBox)
        layout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        self.loadSetups()
        self.loadSettings()

    def loadSetups(self):
        """Load available setups."""
        # TODO concentrate paths in a dedicated module, eg. paths.config_dir
        location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'Setup_configs')
        items = utilities.get_available_setups(location)
        self.setupComboBox.clear()
        self.setupComboBox.addItems(items)

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

    def onAccept(self):
        """On dialog accept (apply button was clicked)."""
        self.writeSettings()
        self.accept()
