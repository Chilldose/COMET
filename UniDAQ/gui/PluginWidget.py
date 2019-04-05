from PyQt5 import QtCore
from PyQt5 import QtWidgets

class PluginWidget(QtWidgets.QWidget):
    """Widget for plugins tabs."""

    start = QtCore.pyqtSignal()
    stop = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(PluginWidget, self).__init__(parent)

    def onStart(self):
        """Emits start measurement signals."""
        self.start.emit()

    def onStop(self):
        """Emits stop measurement signals."""
        self.stop.emit()
