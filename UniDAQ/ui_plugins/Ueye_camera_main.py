# Some functions for Ueye camera systems

import logging
from PyQt5.QtCore import Qt
class Ueye_main:

    def __init__(self, layout_camera, roi_width=1280, roi_height=1024):

        self.log = logging.getLogger(__name__)
        self.log.info("Try to start Ueye camera interface...")
        self.camera_View = layout_camera
        try:
            from pyueye import ueye
            from ..Ueye_camera.pyueye_camera import Camera
            from ..Ueye_camera.pyueye_utils import FrameThread
            from ..Ueye_camera.pyueye_gui import PyuEyeQtView

            # a basic qt window
            self.view = PyuEyeQtView()
            #self.view.show()
            self.camera_View.addWidget(self.view)
            #self.camera_View.setAlignment(self.view, Qt.AlignTop)

            # camera class to simplify uEye API access
            self.cam = Camera()
            self.cam.init()
            self.cam.set_colormode(ueye.IS_CM_BGR8_PACKED)
            self.cam.set_aoi(int((2456-roi_width)/2),int((1842-roi_height)/2), roi_width, roi_height)
            #self.cam.set_aoi(roi_width,roi_height, roi_width, roi_height)
            self.cam.alloc()

            # a thread that waits for new images and processes all connected views
            self.continous_capture = FrameThread(self.cam, self.view)
            self.continous_capture.start()

        except:
            self.log.info("Ueye camera interface could not be started...")


    def start(self):
        """Starts the camera """
        self.cam.capture_video()


    def stop(self):
        """Stops the camera capture"""
        self.cam.stop_video()

    def close(self):
        """Closes the camera thread and everything else related to it"""
        # cleanup

        try:
            self.continous_capture.stop()
            self.continous_capture.join()

            self.cam.stop_video()
            self.cam.exit()
        except:
            self.log.warning("Could not correctly close camera session...")