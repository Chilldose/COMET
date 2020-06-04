# Some functions for Ueye camera systems

import ctypes
import logging


class Ueye_main:
    def __init__(self, layout_camera, roi_width=1920, roi_height=1080):

        self.log = logging.getLogger(__name__)
        self.log.info("Try to start Ueye camera interface...")
        self.camera_View = layout_camera
        try:
            from pyueye import ueye
            from ..misc_plugins.Ueye_camera.pyueye_camera import Camera
            from ..misc_plugins.Ueye_camera.pyueye_utils import FrameThread
            from ..misc_plugins.Ueye_camera.pyueye_gui import PyuEyeQtView

            # a basic qt window
            self.view = PyuEyeQtView()
            self.camera_View.addWidget(self.view)
            self.ueye = ueye

            # camera class to simplify uEye API access
            self.cam = Camera()
            self.cam.init()

            # Set framerate, WB, etc.
            self.SetAutoParameter(
                self.cam, "SET_ENABLE_AUTO_WHITEBALANCE", pval1=1, pval2=0
            )
            self.SetAutoParameter(self.cam, "SET_AUTO_WB_AOI", pval1=1, pval2=0)
            self.SetAutoParameter(self.cam, "SET_AUTO_BRIGHT_AOI", pval1=1, pval2=0)

            # ueye.is_SetAutoParameter(ctypes.c_int(self.cam.h_cam),
            #                         ctypes.c_int(ueye.IS_SET_ENABLE_AUTO_WHITEBALANCE),
            #                         ctypes.c_double(1), ctypes.c_double(0))

            self.cam.set_colormode(ueye.IS_CM_BGR8_PACKED)
            self.cam.set_aoi(
                int((2456 - roi_width) / 2),
                int((1842 - roi_height) / 2),
                roi_width,
                roi_height,
            )
            self.cam.alloc()

            # a thread that waits for new images and processes all connected views
            self.continous_capture = FrameThread(self.cam, self.view)
            self.continous_capture.start()

        except Exception as err:
            self.log.error(
                "Ueye camera interface could not be started...", exc_info=True
            )

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

    def SetAutoParameter(self, camera, isType, pval1=1, pval2=0):
        """ controls Auto Gain, Auto Shutter, Auto Framerate and Auto Whitebalance
        functionality. Purpose of the auto functions is it to control the camera
        image in its average
         SET_AUTO_BRIGHT_AOI -- Set the Auto Feature AOI for Auto Gain and Auto Shutter
         SET_AUTO_WB_AOI -- Set AOI for Auto Whitebalance
         SET_ENABLE_AUTO_WHITEBALANCE
        """
        cam = ctypes.c_int(camera.h_cam)
        pval1_c = ctypes.c_double(pval1)
        pval2_c = ctypes.c_double(pval2)
        isType = getattr(self.ueye, "IS_" + isType)
        isType_c = ctypes.c_int(isType)
        r = self.CALL("SetAutoParameter", cam, isType_c, pval1_c, pval2_c)
        pval1 = pval1_c.value
        pval2 = pval2_c.value
        ret = dict()
        ret["status"] = r
        ret["pval1"] = pval1
        ret["pval2"] = pval2
        return ret

    def CALL(self, name, *args):
        """
        Calls ueye function "name" and arguments "args".
        """
        funcname = "is_" + name
        func = getattr(self.ueye, funcname)
        return func(*args)
