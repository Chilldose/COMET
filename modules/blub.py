import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

pg.setConfigOptions(antialias=True)
pg.setConfigOption('background', '#c7c7c7')
pg.setConfigOption('foreground', '#000000')
from pyqtgraph.ptime import time
app = QtGui.QApplication([])

p = pg.plot()
p.setXRange(0,10)
p.setYRange(-10,10)
p.setWindowTitle('Current-Voltage')
p.setLabel('bottom', 'Bias', units='V', **{'font-size':'20pt'})
p.getAxis('bottom').setPen(pg.mkPen(color='#000000', width=3))
p.setLabel('left', 'Current', units='A',
            color='#c4380d', **{'font-size':'20pt'})
p.getAxis('left').setPen(pg.mkPen(color='#c4380d', width=3))
curve = p.plot(x=[], y=[], pen=pg.mkPen(color='#c4380d'))
p.showAxis('right')
p.setLabel('right', 'Dynamic Resistance', units="<font>&Omega;</font>",
            color='#025b94', **{'font-size':'20pt'})
p.getAxis('right').setPen(pg.mkPen(color='#025b94', width=3))

p2 = pg.ViewBox()
p.scene().addItem(p2)
p.getAxis('right').linkToView(p2)
p2.setXLink(p)
p2.setYRange(-10,10)

curve2 = pg.PlotCurveItem(pen=pg.mkPen(color='#025b94', width=1))
p2.addItem(curve2)

def updateViews():
    global p2
    p2.setGeometry(p.getViewBox().sceneBoundingRect())
    p2.linkedViewChanged(p.getViewBox(), p2.XAxis)

updateViews()
p.getViewBox().sigResized.connect(updateViews)

x = np.arange(0, 10.01,0.01)
data = 5+np.sin(30*x)
data2 = -5+np.cos(30*x)
ptr = 0
lastTime = time()
fps = None

def update():
    global p, x, curve, data, curve2, data2, ptr, lastTime, fps
    if ptr < len(x):
        curve.setData(x=x[:ptr], y=data[:ptr])
        curve2.setData(x=x[:ptr], y=data2[:ptr])
        ptr += 1
        now = time()
        dt = now - lastTime
        lastTime = now
        if fps is None:
            fps = 1.0/dt
        else:
            s = np.clip(dt*3., 0, 1)
            fps = fps * (1-s) + (1.0/dt) * s
        p.setTitle('%0.2f fps' % fps)
    else:
        ptr = 0
    app.processEvents()  ## force complete redraw for every plot.  Try commenting out to see if a different in speed occurs.
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(0)


if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
