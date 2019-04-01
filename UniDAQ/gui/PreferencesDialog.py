import sys, os

from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from .. import utilities

class PreferencesDialog(QtWidgets.QDialog):
    """Preferences dialog for application settings."""

    def __init__(self, parent=None):
        super(PreferencesDialog, self).__init__(parent)
        self.setWindowTitle(self.tr("Preferences"))
        self.comboBox = QtWidgets.QComboBox()
        # Buttonbox
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Apply)
        self.buttonBox.clicked.connect(self.onClose)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.comboBox)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        self.loadSetups()

    def loadSetups(self):
        """Load available setups."""
        # TODO concentrate paths in a dedicated module, eg. paths.config_dir
        location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'Setup_configs')
        items = utilities.get_available_setups(location)
        self.comboBox.clear()
        self.comboBox.addItems(items)

    def activeSetup(self):
        """Returns active setup."""
        return self.comboBox.currentText()

    def updateSettings(self):
        """Update settings from dialog widgets."""
        QtCore.QSettings().setValue('active_setup', active_setup)

    def onClose(self):
        """On dialog close."""
        # self.updateSettings() # TODO currently holding back
        self.close()
