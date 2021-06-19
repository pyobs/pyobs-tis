from datetime import datetime
import threading
import logging
import numpy as np

from pyobs.images import Image
from pyobs.modules.camera import BaseWebcam
from pyobs.utils.enums import ExposureStatus

from . import tisgrabber as IC, TIS

log = logging.getLogger(__name__)


class TisCamera(BaseWebcam):
    def __init__(self, device: str, format: str, *args, **kwargs):
        BaseWebcam.__init__(self, *args, **kwargs)

        # store
        self._device = device
        self._format = format

        # create the camera object.
        self._camera = IC.TIS_CAM()

    def open(self):
        """Open module"""
        BaseWebcam.open(self)

        # open camera
        self.camera = TIS.TIS()
        self.camera.openDevice(self._device, 1280, 960, "15/1", TIS.SinkFormats.GRAY8, False)
        self.camera.Set_Image_Callback(self.new_image)
        self.camera.Start_pipeline()

    def close(self):
        """Close module"""
        BaseWebcam.close(self)

        # stop live video stream
        self.camera.Stop_pipeline()

    def wait_for_frame(self, *args, **kwargs):
        pass

    def get_last_frame(self, *args, **kwargs) -> str:
        pass

__all__ = ['TisCamera']
