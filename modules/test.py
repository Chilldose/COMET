#from modules.VisaConnectWizard import *
from time import sleep
from pyqtgraph.Qt import QtGui, QtCore
import sys
import pyqtgraph as pg
import thread, Queue
import numpy as np
import datetime as date
import os.path
import random


#Variables
#SMUdata = np.array([0,1], dtype=np.float32)
SMUdata = []
stop=False
biasVoltage = 50
ramp_steps = 3
time_to_wait = 0.01 #sec
create_new_files = True #creates new files every time the program starts
save_to_file = True
#For shared variables among threads
q = Queue.Queue()

#Filenaming
filename= 'current_measurement_' + str.replace(date.datetime.now().isoformat()[:9], '-','_') + '_0' #create filename dynamically
counter = 1

while os.path.isfile(filename) and create_new_files: #checks if file exists
    filename = filename[:-1] + str(counter) #if exists than change the last number in filename string
    counter += 1


if save_to_file: #opens file for writing
    # Open a file
    fd = os.open(filename, os.O_WRONLY | os.O_CREAT)


def get_smu_data(data, file, q):

    while not stop:
        dummy = random.randint(1,10)
        data = np.append(data,[dummy])
        #print sys.getsizeof(file)
        #print data
        q.put(data)
        # Write one string and append the data to file
        string_to_write = str(date.datetime.now().isoformat()) + "\t" + str(dummy)
        os.write(file, string_to_write)

        # ensures that the data is written on HDD
        os.fsync(file)

        sleep(time_to_wait)
    print "Stop taking data"


#Plotting
QtGui.QApplication.setGraphicsSystem('raster')

#app = QtGui.QApplication([])
#mw = QtGui.QMainWindow()
#mw.resize(800,800)

win = pg.GraphicsWindow(title="Current over time")
win.resize(1000,600)
win.setWindowTitle('2410 SMU')

# Enable antialiasing for prettier plots
pg.setConfigOptions(antialias=True)

p1 = win.addPlot(title="Current over time")
p2 = win.addPlot(title="Current over time")
p3 = win.addPlot(title="Current over time")
p4 = win.addPlot(title="Current over time")
p5 = win.addPlot(title="Current over time")
p6 = win.addPlot(title="Current over time")
p7 = win.addPlot(title="Current over time")
p8 = win.addPlot(title="Current over time")
p9 = win.addPlot(title="Current over time")
p0 = win.addPlot(title="Current over time")
curve0 = p0.plot(pen='y')
curve1 = p1.plot(pen='y')
curve2 = p2.plot(pen='y')
curve3 = p3.plot(pen='y')
curve4 = p4.plot(pen='y')
curve5 = p5.plot(pen='y')
curve6 = p6.plot(pen='y')
curve7 = p7.plot(pen='y')
curve8 = p8.plot(pen='y')
curve9 = p9.plot(pen='y')
ptr=0
def update():
    global curve, SMUdata, ptr, p6
    #q.get() wartet bis es eine Antwort bekommt, daher steht es dort
    try:
        SMUdata = q.get_nowait()
        #print "plot data: " + sys.getsizeof(SMUdata)

    except:
        pass
    curve0.setData(SMUdata)
    curve1.setData(SMUdata)
    curve2.setData(SMUdata)
    curve3.setData(SMUdata)
    curve4.setData(SMUdata)
    curve5.setData(SMUdata)
    curve6.setData(SMUdata)
    curve7.setData(SMUdata)
    curve8.setData(SMUdata)
    curve9.setData(SMUdata)

   #print sys.getsizeof(pg)
#    if ptr == 0:
#        p6.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted
    ptr += 1

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)


def start_plotting():
    ## Start Qt event loop unless running in interactive mode or using pyside.
    if __name__ == '__main__':
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()


thread.start_new_thread(get_smu_data, (SMUdata, fd, q))

start_plotting()

#for i in range(10):
#    print SMUdata
#    sleep(1)

#while not stop:
#    a = str(raw_input("End data taking? (y)"))
#    if a == "y":
#        stop=True
#    else:
#        print "Wrong input"


stop=True


