import logging
import os.path as osp
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .. import utilities


l = logging.getLogger(__name__)





class Info_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout

        # Dynamic waiting time detection tab
        self.widget = QWidget()
        self.dynamic = self.variables.load_QtUi_file("QTC_Main.ui", self.widget)
        self.layout.addWidget(self.widget)

        self.layout.parent().start.connect(self.onStart)
        self.layout.parent().stop.connect(self.onStop)

    def onStart(self):
        self.widget.setStyleSheet("background: orange;")

    def onStop(self):
        self.widget.setStyleSheet("background: white;")
