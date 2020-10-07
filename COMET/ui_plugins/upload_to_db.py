from PyQt5.QtWidgets import QWidget, QVBoxLayout, QDialog
from ..measurement_plugins.forge_tools import tools
from time import sleep
from PyQt5.QtWidgets import QApplication, QFileDialog
import subprocess, os
import logging
import glob


class CMS_DB_loader(QDialog):
    def __init__(self, gui, parent=None):

        super(CMS_DB_loader, self).__init__(None)
        self.gui = gui
        self.tools = tools
        self.log = logging.getLogger(__name__)

        layout = QVBoxLayout(self)

        # Dynamic waiting time detection tab
        self.DB_Widget_object = QWidget()
        self.DBwidget = self.gui.variables.load_QtUi_file(
            "DataBaseLoader.ui", self.DB_Widget_object
        )
        layout.addWidget(self.DB_Widget_object)

        # Init some values
        self.DBwidget.progressBar.setValue(0.)

        # Do all the actions
        self.DBwidget.Upload_Button.clicked.connect(self.upload_action)
        self.DBwidget.directory_toolButton.clicked.connect(self.dir_selector_action)


    def upload_action(self):
        """Starts the script to upload data to DB"""
        self.DBwidget.Upload_Button.setEnabled(False)
        directory = self.DBwidget.directory_edit.text()
        if os.path.isdir(directory):
            file_list = glob.glob(directory + "/*.xml")
            if "CMSxmlTemplate" in self.gui.variables.default_values_dict:
                uploader = self.gui.variables.default_values_dict["CMSxmlTemplate"].get("DB_uploader_API_module", "")
                for i, file in enumerate(file_list):
                    self.DBwidget.which_file.setText("Uploading file: {}".format(os.path.basename(file)))
                    try:
                        proc = subprocess.run("python " + os.path.normpath(uploader) + " " + os.path.normpath(file), capture_output=True)
                        answer = proc.stdout.decode()
                        self.log.info("Uploader return: {}".format(answer))
                    except:
                        self.log.error("An error happened while uploading file {}".format(file), exc_info=True)
                    # todo: username and pw query
                    self.DBwidget.progressBar.setValue(((i+1)/len(file_list))*100)
                    QApplication.processEvents()
                    sleep(0.3)
        else:
            self.log.error("The path {} does not exist!".format(directory))
        self.DBwidget.Upload_Button.setEnabled(True)
        self.DBwidget.which_file.setText("")  
        self.DBwidget.progressBar.setValue(0.)

    def get_acc_info(self):
        """Gets the account info if need be"""
        user = self.DBwidget.Username_lineEdit.text()
        pw = self.DBwidget.Password_lineEdit.text()
        return user, pw

    def dir_selector_action(self):
        self.autodirgen = True
        fileDialog = QFileDialog()
        directory = fileDialog.getExistingDirectory()
        self.DBwidget.directory_edit.setText(directory)

