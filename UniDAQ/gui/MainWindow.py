import webbrowser
import sys, os

from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from ..utilities import ErrorMessageBoxHandler

ContentsURL = "https://chilldose.github.io/UniDAQ/_build/html/index.html"
"""URL to primary documentation."""

class MainWindow(QtWidgets.QMainWindow):
    """Main window containing plugin tabs as central widget."""

    def __init__(self, message_to_main, parent=None):
        super(MainWindow, self).__init__(parent)
        self.message_to_main = message_to_main
        self.setWindowTitle(self.tr("Comet"))
        icon_filename = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images', 'logo.png')
        self.setWindowIcon(QtGui.QIcon(icon_filename))
        # Only minimize and maximize button are active
        self.setWindowFlags(Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.resize(1600, 800)
        # Create actions and toolbars.
        self.createActions()
        self.createMenus()
        self.createToolbar()
        self.createStatusBar()
        # Create central widget
        self.setCentralWidget(QtWidgets.QTabWidget(self))
        # Create error message dialog
        self.errMsg = ErrorMessageBoxHandler(QiD=self)

    def createActions(self):
        """Create actions."""
        # Action for quitting the program.
        self.quitAct = QtWidgets.QAction(self.tr("&Quit"), self)
        self.quitAct.setShortcut(QtGui.QKeySequence.Quit)
        self.quitAct.setStatusTip(self.tr("Quit the programm"))
        self.quitAct.triggered.connect(self.close)
        # Open contents URL.
        self.contentsAct = QtWidgets.QAction(self.tr("&Contents"), self)
        self.contentsAct.setShortcut(QtGui.QKeySequence(Qt.Key_F1))
        self.contentsAct.setStatusTip(self.tr("Visit manual on github pages"))
        self.contentsAct.triggered.connect(self.showContents)

    def createMenus(self):
        """Create menus."""
        # File menu
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.quitAct)
        # Help menu
        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.addAction(self.contentsAct)

    def createToolbar(self):
        """Create toolbar."""
        pass

    def createStatusBar(self):
        """Create status bar."""
        self.statusBar()

    def addTab(self, widget, title):
        """Add an existing widget to central tab widget, provided for convenince."""
        self.centralWidget().addTab(widget, title)

    def showContents(self):
        """Open web browser and open contents."""
        webbrowser.open_new_tab(ContentsURL)

    def closeEvent(self, event):
        """On window close event."""
        result = QtWidgets.QMessageBox.question(None,
            self.tr("Confirm quit"),
            self.tr("Are you sure to quit?"),
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            # Send close message to main thread
            self.message_to_main.put({"CLOSE_PROGRAM": True})
            event.accept()
        else:
            event.ignore()
