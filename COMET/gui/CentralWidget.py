from PyQt5 import QtWidgets

class CentralWidget(QtWidgets.QTabWidget):
    """Central tab widget displaying plugins."""

    def __init__(self, parent=None):
        super(CentralWidget, self).__init__(parent)

    def onStart(self):
        """Propagate start event to plugin widgets."""
        for index in range(self.count()):
            widget = self.widget(index)
            if hasattr(widget, 'onStart'):
                widget.onStart()

    def onStop(self):
        """Propagate stop event to plugin widgets."""
        for index in range(self.count()):
            widget = self.widget(index)
            if hasattr(widget, 'onStop'):
                widget.onStop()
