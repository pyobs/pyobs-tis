import asyncio
import concurrent.futures
import logging
import time
from typing import Any

from pyobs.images import Image
from pyobs.modules.camera import BaseVideo
from pyobs.utils.enums import ImageType

log = logging.getLogger(__name__)


class TisCamera(BaseVideo):
    def __init__(self, device: str, format: str, **kwargs: Any):
        BaseVideo.__init__(self, **kwargs)

        # store
        self._device = device
        self._format = format
        # typed as Any: the underlying TIS wrapper is a dynamic GObject/GStreamer binding
        self._camera: Any = None
        self._last_image_time: float | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._resolution: tuple[int, int] | None = None
        self._fps: float | None = None

    async def open(self) -> None:
        """Open module"""
        await BaseVideo.open(self)

        # imported lazily: TIS pulls in gi + the GStreamer/Tcam typelibs at import time,
        # which aren't available on a plain CI runner
        from . import TIS

        # create camera
        self._camera = TIS.TIS()
        self._camera.serialnumber = self._device

        # get formats
        formats = self._camera.createFormats()
        if self._format not in formats:
            raise ValueError(f"Invalid format: {self._format}")
        fmt = formats[self._format]

        # resolution and fps
        res = fmt.res_list[0]
        fps = res.fps[0]
        self._resolution = (res.width, res.height)
        self._fps = fps

        # open camera
        log.info("Opening webcam with %dx%d at %s fps.", res.width, res.height, fps)
        self._camera.openDevice(self._device, res.width, res.height, fps, TIS.SinkFormats.GRAY8, False)

        # the image callback fires on a GStreamer thread, so schedule the coroutine onto our event loop
        self._loop = asyncio.get_running_loop()
        self._camera.Set_Image_Callback(self._on_new_image)

        # start taking images
        if not self._camera.Start_pipeline():
            self._camera.Stop_pipeline()
            raise ValueError("Could not start pipeline.")

    async def close(self) -> None:
        """Close module"""
        await BaseVideo.close(self)

        # stop live video stream
        self._camera.Stop_pipeline()

    async def _finish_image(self, image: Image, broadcast: bool, image_type: ImageType) -> tuple[Image, str]:
        """Add device identity/format headers, then finish up as usual (BaseVideo has no
        per-frame header hook of its own, so this is the earliest point after add_fits_headers()
        and before the image is serialized to bytes)."""
        image.header["INSTRUME"] = (self._device, "Camera serial number")
        if self._resolution is not None:
            image.header["VIDFMT"] = (f"{self._resolution[0]}x{self._resolution[1]}", "Video resolution used")
        if self._fps is not None:
            image.header["VIDFPS"] = (self._fps, "Video frame rate used [fps]")
        return await super()._finish_image(image, broadcast, image_type)

    def _on_new_image(self, tis: Any) -> None:
        """Called by TIS on its GStreamer thread: hand the coroutine to our event loop."""
        if self._loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(self.new_image(tis), self._loop)

        def _log_result(fut: concurrent.futures.Future) -> None:
            try:
                fut.result()
            except Exception:
                log.exception("Error processing new image.")

        future.add_done_callback(_log_result)

    async def new_image(self, tis: Any) -> None:
        if self._last_image_time is not None and time.time() < self._last_image_time + self._interval:
            return
        self._last_image_time = time.time()

        # get image and process it
        img = self._camera.Get_image()
        await self._set_image(img[:, :, 0])


__all__ = ["TisCamera"]
