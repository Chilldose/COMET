from PyQt5.QtWidgets import QWidget, QVBoxLayout, QDialog
from ..measurement_plugins.forge_tools import tools
from time import sleep
from PyQt5.QtWidgets import QApplication, QFileDialog


class CMS_DB_loader(QDialog):
    def __init__(self, gui, parent=None):

        super(CMS_DB_loader, self).__init__(None)
        self.gui = gui
        self.tools = tools

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
        for i in range(10):
            self.DBwidget.progressBar.setValue(((i+1)/10.)*100)
            self.DBwidget.which_file.setText("Uploading file: {}".format(i))
            sleep(0.2)
            QApplication.processEvents()
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

