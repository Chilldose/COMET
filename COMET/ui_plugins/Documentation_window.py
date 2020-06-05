import logging
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import os


class Documentation_window:
    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout
        self.log = logging.getLogger(__name__)

        self.view = QWebEngineView()
        filepath = os.path.join(
            self.variables.framework_variables["rootdir"], "..", "docs", "index.html"
        )
        self.view.load(QUrl.fromLocalFile(filepath))
        self.layout.addWidget(self.view)
