import logging
import os.path as osp
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .. import utilities


l = logging.getLogger(__name__)

hf = utilities.help_functions()




class Info_window:

    def __init__(self, GUI, layout):

        self.variables = GUI
        self.layout = layout

        pic = QLabel()
        path = osp.join(osp.dirname(sys.modules[__name__].__file__), '../images/cms.png')
        pic.setPixmap(QPixmap(path))
        pic.setScaledContents(True)
        effect1 = QGraphicsOpacityEffect(pic)
        effect2 = QGraphicsBlurEffect(pic)
        effect1.setOpacity(0.2)
        effect2.setBlurRadius(8.)
        pic.setGraphicsEffect(effect1)
        pic.setGraphicsEffect(effect2)
        pic.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.layout.addWidget(pic,0,0)



        # Info text
        textbox = QLabel()
        #textbox.setStyleSheet("QLabel { background : rgb(179,179,179) }")
        #textbox.setFrameStyle( QFrame.StyledPanel | QFrame.Sunken)
        textbox.setLineWidth(4)
        textbox.setMidLineWidth(3)
        textbox.setFont(QFont("Times", 12, QFont.Bold))

        textbox.setText("Fancy text")
        textbox.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(textbox, 0, 0)
