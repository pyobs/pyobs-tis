import time
import logging
from typing import Any

from pyobs.modules.camera import BaseVideo
from . import TIS

log = logging.getLogger(__name__)


class TisCamera(BaseVideo):
    def __init__(self, device: str, format: str, **kwargs: Any):
        BaseVideo.__init__(self, **kwargs)

        # store
        self._device = device
        self._format = format
        self._camera = None
        self._last_image_time = None

    async def open(self) -> None:
        """Open module"""
        await BaseVideo.open(self)

        # create camera
        self._camera = TIS.TIS()
        self._camera.serialnumber = self._device

        # get formats
        formats = self._camera.createFormats()
        if self._format not in formats:
            raise ValueError("Invalid format: %s" % self._format)
        fmt = formats[self._format]

        # resolution and fps
        res = fmt.res_list[0]
        fps = res.fps[0]

        # open camera
        log.info("Opening webcam with %dx%d at %s fps.", res.width, res.height, fps)
        self._camera.openDevice(self._device, res.width, res.height, fps, TIS.SinkFormats.GRAY8, False)
        self._camera.Set_Image_Callback(self.new_image)

        # start taking images
        if not self._camera.Start_pipeline():
            raise ValueError("Could not start pipeline.")

    async def close(self) -> None:
        """Close module"""
        await BaseVideo.close(self)

        # stop live video stream
        self._camera.Stop_pipeline()

    async def new_image(self, tis: TIS.TIS) -> None:
        if self._last_image_time is not None and time.time() < self._last_image_time + self._interval:
            return
        self._last_image_time = time.time()

        # get image and process it
        img = self._camera.Get_image()
        await self._set_image(img[:, :, 0])


__all__ = ["TisCamera"]
