import webbrowser
import sys, os

from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from ..utilities import ErrorMessageBoxHandler

ContentsURL = "https://chilldose.github.io/UniDAQ/_build/html/index.html"
"""URL to primary documentation."""

ResourcePath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images')

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
        self.resize(1600, 1000)
        # Create actions and toolbars.
        self.createActions()
        self.createMenus()
        self.createToolbar()
        self.createStatusBar()
        # Create central widget
        central_widget = QtWidgets.QTabWidget(self)
        central_widget.setMinimumSize(640, 490)
        self.setCentralWidget(central_widget)
        # Create error message dialog
        self.errMsg = ErrorMessageBoxHandler(QiD=self)

    def createActions(self):
        """Create actions."""
        # Action for quitting the program.
        self.quitAct = QtWidgets.QAction(self.tr("&Quit"), self)
        self.quitAct.setShortcut(QtGui.QKeySequence.Quit)
        self.quitAct.setStatusTip(self.tr("Quit the programm"))
        self.quitAct.triggered.connect(self.close)
        # Action for starting a measurement.
        self.startAct = QtWidgets.QAction(self.tr("&Start"), self)
        self.startAct.setIcon(QtGui.QIcon(os.path.join(ResourcePath, 'start.svg')))
        self.startAct.setStatusTip(self.tr("Start measurement"))
        self.startAct.triggered.connect(self.onStart)
        self.startAct.setCheckable(True)
        # Action for stopping a measurement.
        self.stopAct = QtWidgets.QAction(self.tr("S&top"), self)
        self.stopAct.setIcon(QtGui.QIcon(os.path.join(ResourcePath, 'stop.svg')))
        self.stopAct.setStatusTip(self.tr("Stop measurement"))
        self.stopAct.triggered.connect(self.onStop)
        self.stopAct.setCheckable(True)
        self.stopAct.setChecked(True)
        self.stopAct.setEnabled(False)
        # Action group for measurement control
        self.measureActGroup = QtWidgets.QActionGroup(self)
        self.measureActGroup.addAction(self.startAct)
        self.measureActGroup.addAction(self.stopAct)
        self.measureActGroup.setExclusive(True)
        # Open contents URL.
        self.contentsAct = QtWidgets.QAction(self.tr("&Contents"), self)
        self.contentsAct.setShortcut(QtGui.QKeySequence(Qt.Key_F1))
        self.contentsAct.setStatusTip(self.tr("Visit manual on github pages"))
        self.contentsAct.triggered.connect(self.onShowContents)

    def createMenus(self):
        """Create menus."""
        # File menu
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.quitAct)
        # Measurement menu
        self.measureMenu = self.menuBar().addMenu(self.tr("&Measure"))
        self.measureMenu.addActions(self.measureActGroup.actions())
        # Help menu
        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.addAction(self.contentsAct)

    def createToolbar(self):
        """Create main toolbar and pin to top area."""
        self.toolbar = self.addToolBar("Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.addActions(self.measureActGroup.actions())

    def createStatusBar(self):
        """Create status bar."""
        self.statusBar()

    def addTab(self, widget, title):
        """Add an existing widget to central tab widget, provided for convenince."""
        self.centralWidget().addTab(widget, title)

    def onStart(self):
        """Starting a measurement."""
        self.startAct.setEnabled(not self.startAct.isEnabled())
        self.stopAct.setEnabled(not self.stopAct.isEnabled())
        # TODO

    def onStop(self):
        """Stopping current measurement."""
        self.startAct.setEnabled(not self.startAct.isEnabled())
        self.stopAct.setEnabled(not self.stopAct.isEnabled())
        # TODO

    def onShowContents(self):
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
