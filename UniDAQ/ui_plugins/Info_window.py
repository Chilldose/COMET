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
        test = QWidget()
        self.dynamic = self.variables.load_QtUi_file("QTC_Main.ui", test)
        self.layout.addWidget(test)







