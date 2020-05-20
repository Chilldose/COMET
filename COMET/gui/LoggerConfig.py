import logging
from PyQt5 import QtWidgets
import os
from PyQt5 import QtCore
from PyQt5 import uic


from .. import utilities

def setCurrentEntry(widget, text):
    """Set current combo box entry by test, provided for convenince."""
    index = widget.findText(text)
    if index >= 0:
        widget.setCurrentIndex(index)

class LoggerConfig(QtWidgets.QDialog):
    """Preferences dialog for application settings."""

    def __init__(self, parent=None):
        super(LoggerConfig, self).__init__(parent)
        dialogBox, QtBaseClass = uic.loadUiType(
            os.path.join(os.getcwd(),
            os.path.normpath("COMET/QT_Designer_UI/LoggerConfig.ui")
                         ))
        self.diaologBox = dialogBox()
        self.diaologBox.setupUi(self)
        self.diaologBox.LevelComboBox.clear()
        self.diaologBox.HandlersComboBox.clear()
        self.diaologBox.LevelComboBox.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_LEVELS = {"NOTSET": 0, "DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

        self.loadHandlers()

        self.diaologBox.OkButton.clicked.connect(self.onClose)
        self.diaologBox.ApplyButton.clicked.connect(self.onApplyLevel)

    def loadHandlers(self):
        """Loads the handlers"""
        logger = logging.getLogger()
        self.diaologBox.HandlersComboBox.clear()
        for handler in logger.handlers:
            self.diaologBox.HandlersComboBox.addItem(str(handler))

    def onApplyLevel(self):
        """Changes the logging level of the selected Handler to the new level"""
        logger = logging.getLogger()
        newLevel = self.diaologBox.LevelComboBox.currentText()
        handlerchange = self.diaologBox.HandlersComboBox.currentText()
        for handler in logger.handlers:
            if str(handler) == handlerchange:
                handler.setLevel(self.log_LEVELS[newLevel])
        self.loadHandlers()


    def onClose(self):
        """On dialog close."""
        # self.updateSettings() # TODO currently holding back
        self.close()

    def onAccept(self):
        """On dialog accept (apply button was clicked)."""
        self.writeSettings()
        self.accept()
