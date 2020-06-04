import logging
from PyQt5 import QtWidgets
import os
from PyQt5 import uic


class SaveOptionDialog(QtWidgets.QDialog):
    """Preferences dialog for application settings."""

    def __init__(self, tocall, file, data, parent=None):
        super(SaveOptionDialog, self).__init__(parent)
        dialogBox, QtBaseClass = uic.loadUiType(
            os.path.join(
                os.getcwd(), os.path.normpath("COMET/QT_Designer_UI/DataChanged.ui")
            )
        )
        self.log = logging.getLogger("ChangeDataVIS")
        self.diaologBox = dialogBox()
        self.diaologBox.setupUi(self)
        self.diaologBox.LevelComboBox.clear()
        self.tocall = (
            tocall  # A function that should be called after the apply button was called
        )
        self.file = file
        self.data = data

        self.diaologBox.ApplyButton.clicked.connect(self.onApplyLevel)
        self.diaologBox.datafile_label.setText(self.file)
        self.diaologBox.LevelComboBox.addItems(list(self.data[self.file].keys()))

    def onApplyLevel(self):
        """Changes the logging level of the selected Handler to the new level"""
        newLevel = self.diaologBox.LevelComboBox.currentText()
        self.tocall(self.data, self.file, newLevel)
        self.close()

    def onClose(self):
        """On dialog close."""
        self.close()
