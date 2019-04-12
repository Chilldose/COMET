# Some functions for Ueye camera systems

import logging
class Ueye_main:

    def __init__(self):

        self.log = logging.getLogger(__name__)
        self.log.info("Try to start Ueye camera interface...")
        try:
            from pyueye import ueye
            from .Ueye_camera.pyueye_camera import Camera
            from .Ueye_camera.pyueye_utils import FrameThread
            from .Ueye_camera.pyueye_gui import PyuEyeQtView

            # a basic qt window
            self.view = PyuEyeQtView()
            self.view.show()

            # camera class to simplify uEye API access
            self.cam = Camera()
            self.cam.init()
            self.cam.set_colormode(ueye.IS_CM_BGR8_PACKED)
            self.cam.set_aoi(0,0, 1280, 1024)
            self.cam.alloc()

            # a thread that waits for new images and processes all connected views
            self.continous_capture = FrameThread(self.cam, self.view)

        except:
            self.log.info("Ueye camera interface could not be started...")


    def start(self):
        """Starts the camera """
        self.cam.capture_video()
        self.continous_capture.start()

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