import sys, os
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
import glob
import yaml
from functools import partial
from distutils.dir_util import copy_tree

class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(695, 294)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.OkButton = QtWidgets.QPushButton(self.centralwidget)
        self.OkButton.setGeometry(QtCore.QRect(90, 210, 542, 28))
        self.OkButton.setObjectName("OkButton")
        self.Title = QtWidgets.QLabel(self.centralwidget)
        self.Title.setGeometry(QtCore.QRect(90, 53, 542, 56))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.Title.setFont(font)
        self.Title.setAutoFillBackground(True)
        self.Title.setObjectName("Title")
        self.comboBox_config = QtWidgets.QComboBox(self.centralwidget)
        self.comboBox_config.setGeometry(QtCore.QRect(90, 178, 542, 25))
        self.comboBox_config.setMinimumSize(QtCore.QSize(0, 25))
        self.comboBox_config.setObjectName("comboBox_config")
        self.Infotext = QtWidgets.QLabel(self.centralwidget)
        self.Infotext.setGeometry(QtCore.QRect(90, 116, 542, 55))
        self.Infotext.setAutoFillBackground(True)
        self.Infotext.setObjectName("Infotext")
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.OkButton.clicked.connect(partial(configureSetup, self))

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "COMET Config Assist"))
        self.OkButton.setText(_translate("MainWindow", "Load"))
        self.Title.setText(_translate("MainWindow", "Welcome to COMET - Control and Measurement Toolkit software"))
        self.Infotext.setText(_translate("MainWindow", "It seems that this is the first start of the software.\n"
                                        "COMET supports auto configuration for several setups.\n"
                                        "Please choose which setup you want to configure. "))

class WelcomeApp(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(WelcomeApp, self).__init__(parent)
        self.setupUi(self)

def configureSetup(widget):
    """Loads the Setup and conigures if"""
    # todo: better way possible, but I am tired
    package_dir = os.path.dirname(os.path.realpath(__file__))
    setup_dir = os.path.join(package_dir, 'UniDAQ', 'config', 'Setup_configs')
    value = widget.comboBox_config.currentText()
    setup_config_path = os.path.join(setup_dir,value)
    copy_tree(setup_config_path, os.path.join(package_dir, 'UniDAQ', 'config'))

    QApplication.quit() # Quits the setup
    #sleep(0.5) # Because it takes some time to get rid of the window in the memory

def Loadmain():
    """This function looks if settings have already been done, otherwise it configs everything and starts the env"""

    #os.system("activate UniDAQenv") # Start the environement for the Software

    # Look if setup has been configured
    package_dir = os.path.dirname(os.path.realpath(__file__))
    setup_dir =  os.path.join(package_dir, 'UniDAQ', 'config', 'Setup_configs')

    # Get config dirs
    config_dir = os.path.join(package_dir, 'UniDAQ', 'config', 'config')
    list_configs = list(map(os.path.basename, glob.glob(os.path.join(config_dir, "settings.yml"))))
    setup_configs = list(map(os.path.basename, [d for d in os.listdir(setup_dir) if os.path.isdir(os.path.join(setup_dir, d))]))

    if len(list_configs)==1:
        with open(os.path.join(config_dir, list_configs[0]), "r") as fp:
            # We have to look if it isnt the blank project
            dic = yaml.safe_load(fp)
        if dic["Settings_name"] == "Empty_Setup" and len(dic) == 1:
            app = QApplication(sys.argv)
            form = WelcomeApp()
            # Add all Setups possible to config
            form.comboBox_config.addItems(setup_configs)
            form.show()
            app.exec_()

    elif len(list_configs)>1:
        print("More then one config file found for configuration of setuo. Please clean directory")
    else:
        app = QApplication(sys.argv)
        form = WelcomeApp()
        # Add all Setups possible to config
        form.comboBox_config.addItems(setup_configs)
        form.show()
        app.exec_()

if __name__ == '__main__':
    Loadmain()
    from UniDAQ.main import main# This starts the actual measurement software
    main()
