import time
import logging

from pyobs.modules.camera import BaseWebcam
from . import TIS

log = logging.getLogger(__name__)


class TisCamera(BaseWebcam):
    def __init__(self, device: str, format: str = '', *args, **kwargs):
        BaseWebcam.__init__(self, *args, **kwargs)

        # store
        self._device = device
        self._format = format
        self._camera = None

    def open(self):
        """Open module"""
        BaseWebcam.open(self)

        # open camera
        self._camera = TIS.TIS()
        self._camera.openDevice(self._device, 1280, 960, "15/1", TIS.SinkFormats.GRAY8, False)
        self._camera.Set_Image_Callback(self.new_image)

        # start taking images
        if not self._camera.Start_pipeline():
            raise ValueError('Could not start pipeline.')

    def close(self):
        """Close module"""
        BaseWebcam.close(self)

        # stop live video stream
        self._camera.Stop_pipeline()

    def wait_for_frame(self, *args, **kwargs):
        pass

    def get_last_frame(self, *args, **kwargs) -> str:
        pass

    def new_image(self, tis):
        interval = 0.5
        if self.last_image is not None and time.time() < self.last_image + interval:
            return
        self.last_image = time.time()

        # get image and process it
        img = self.camera.Get_image()
        self._set_image(img)


__all__ = ['TisCamera']
