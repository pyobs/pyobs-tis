import asyncio
import logging
import threading
import time
from collections.abc import AsyncGenerator, Callable
from typing import Any

from pyobs.images import Image
from pyobs.modules.camera import BaseVideo, Frame
from pyobs.utils.enums import ImageType

log = logging.getLogger(__name__)

# starting/stopping the GStreamer pipeline blocks (Start_pipeline() alone waits up to 5s for the
# PLAYING state), so it runs in a daemon thread bounded by this timeout
_PIPELINE_TIMEOUT = 10.0

# frames() warns if no frame arrived for this long
_FRAME_WAIT_TIMEOUT = 30.0

# frames queued between the GStreamer thread and the event loop; latest wins beyond that
_QUEUE_SIZE = 5

# how often the exposure time is re-read from the camera, since auto exposure may change it
_EXPOSURE_REFRESH = 1.0


class TisCamera(BaseVideo):
    """A pyobs module for cameras by The Imaging Source, via tiscamera/GStreamer.

    The pipeline runs while the module is active and is stopped when it goes to sleep. Frames
    carry the exposure time read from the camera, so BaseVideo can estimate their exposure start.
    """

    __module__ = "pyobs_tis"

    def __init__(
        self,
        device: str,
        format: str,
        exposure_property: str | None = "Exposure Time (us)",
        **kwargs: Any,
    ):
        """Initializes a new TisCamera.

        Args:
            device: Serial number of the camera.
            format: Name of the video format to use.
            exposure_property: Name of the tcam property holding the exposure time in
                microseconds (depends on the tiscamera version). None disables reading it, and
                frames then carry no exposure time.
        """
        BaseVideo.__init__(self, **kwargs)

        # store
        self._device = device
        self._format = format
        self._exposure_property = exposure_property
        # typed as Any: the underlying TIS wrapper is a dynamic GObject/GStreamer binding
        self._camera: Any = None
        self._resolution: tuple[int, int] | None = None
        self._fps: float | None = None
        self._exposure_time: float | None = None
        self._exposure_read = 0.0

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

        # create pipeline, started by frames()
        log.info("Opening webcam with %dx%d at %s fps.", res.width, res.height, fps)
        self._camera.openDevice(self._device, res.width, res.height, fps, TIS.SinkFormats.GRAY8, False)

        # start streaming
        await self.activate_camera()

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

    @staticmethod
    async def _run_blocking(func: Callable[[], None], timeout: float = _PIPELINE_TIMEOUT) -> bool:
        """Run a blocking GStreamer call in a daemon thread, so a hung call can't freeze the module.

        A plain executor isn't used here, since its worker threads are non-daemon and Python joins
        them on interpreter shutdown -- a hung call would then just move the freeze to process exit.

        Returns:
            True if func completed within timeout, False if it's still running in the background.

        Raises:
            Whatever exception func() raised, if it completed within timeout.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[None] = loop.create_future()
        error: list[BaseException] = []

        def _finish() -> None:
            # after a timeout, wait_for() has already cancelled the future
            if not future.done():
                future.set_result(None)

        def _wrapper() -> None:
            try:
                func()
            except BaseException as exc:
                error.append(exc)
            finally:
                try:
                    loop.call_soon_threadsafe(_finish)
                except RuntimeError:
                    # event loop closed (shutdown)
                    pass

        threading.Thread(target=_wrapper, daemon=True).start()
        try:
            await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            return False
        if error:
            raise error[0]
        return True

    def _read_exposure_time(self, tis: Any) -> float | None:
        """Exposure time in seconds, re-read from the camera at most every _EXPOSURE_REFRESH seconds.

        Called on the GStreamer thread. If the property can't be read, reading is disabled.
        """
        if self._exposure_property is None:
            return None
        now = time.monotonic()
        if now - self._exposure_read >= _EXPOSURE_REFRESH:
            self._exposure_read = now
            try:
                self._exposure_time = float(tis.Get_Property(self._exposure_property).value) / 1e6
            except Exception:
                log.warning(
                    "Could not read exposure time from property %r, frames will carry none.",
                    self._exposure_property,
                    exc_info=True,
                )
                self._exposure_property = None
                self._exposure_time = None
        return self._exposure_time

    async def frames(self) -> AsyncGenerator[Frame, None]:
        """Start the pipeline and yield frames until BaseVideo closes the iterator.

        Frames arrive via the TIS image callback on a GStreamer thread, which hands each frame's
        own array to the event loop (TIS copies every sample into a fresh array).
        """
        if self._camera is None:
            raise RuntimeError("Camera not opened.")
        camera = self._camera
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Frame] = asyncio.Queue(maxsize=_QUEUE_SIZE)

        def _put(frame: Frame) -> None:
            # latest wins: a stalled event loop mustn't grow memory
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(frame)

        def _on_frame(tis: Any) -> None:
            # called by TIS right after converting the sample, under its own lock, so Get_image()
            # returns exactly this frame
            img = tis.Get_image()
            frame = Frame(data=img[:, :, 0], exposure_time=self._read_exposure_time(tis))
            try:
                loop.call_soon_threadsafe(_put, frame)
            except RuntimeError:
                # event loop closed (shutdown)
                pass

        def _start() -> None:
            camera.Set_Image_Callback(_on_frame)
            if not camera.Start_pipeline():
                camera.Stop_pipeline()
                raise RuntimeError("Could not start pipeline.")

        if not await self._run_blocking(_start):
            raise TimeoutError("Timed out starting pipeline.")
        try:
            while True:
                try:
                    frame = await asyncio.wait_for(queue.get(), timeout=_FRAME_WAIT_TIMEOUT)
                except TimeoutError:
                    log.warning("No frame from camera for %.1fs.", _FRAME_WAIT_TIMEOUT)
                    continue
                yield frame
        finally:
            try:
                if not await self._run_blocking(camera.Stop_pipeline):
                    log.error("Timed out stopping pipeline after %.1fs.", _PIPELINE_TIMEOUT)
            except Exception:
                log.exception("Error stopping pipeline.")


__all__ = ["TisCamera"]
