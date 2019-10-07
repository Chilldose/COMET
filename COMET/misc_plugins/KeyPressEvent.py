from PyQt5 import QtCore
from PyQt5.QtCore import QObject


class keyPress_handler(QObject):
    keyPressed = QtCore.pyqtSignal(int)

    def __init__(self, widget, event):
        super(keyPress_handler, self).keyPressEvent(event)
        self.keyPressed.emit(event.key())

    def on_key(key):
        # test for a specific key
        if key == QtCore.Qt.Key_Return:
            print('return key pressed')
        else:
            print('key pressed: %i' % key)

# usage:
#self.widget.keyPressed.connect(on_key)
