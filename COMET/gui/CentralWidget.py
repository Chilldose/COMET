from PyQt5 import QtWidgets
import logging


class CentralWidget(QtWidgets.QTabWidget):
    """Central tab widget displaying plugins."""

    def __init__(self, parent=None):
        super(CentralWidget, self).__init__(parent)
        self.log = logging.getLogger(__name__)

    def onStart(self):
        """Propagate start event to current plugin widget."""
        widget = self.currentWidget()
        if hasattr(widget, "onStart"):
            widget.onStart()
        else:
            self.log.error(
                "The current selected tab does not support external start signal."
            )

    def onStop(self):
        """Propagate stop event to plugin widgets."""
        for index in range(self.count()):
            widget = self.widget(index)
            if hasattr(widget, "onStop"):
                widget.onStop()
