from datetime import datetime
import threading
import logging
import numpy as np

from pyobs.images import Image
from pyobs.modules.camera import BaseCamera
from pyobs.utils.enums import ExposureStatus

from . import tisgrabber as IC


log = logging.getLogger(__name__)


class TisCamera(BaseCamera):
    def __init__(self, device: str, format: str, *args, **kwargs):
        BaseCamera.__init__(self, *args, **kwargs)

        # store
        self._device = device
        self._format = format

        # create the camera object.
        self._camera = IC.TIS_CAM()

    def open(self):
        """Open module"""
        BaseCamera.open(self)

        # open camera
        self._camera.open(self._device)

        # set video format
        self._camera.SetVideoFormat(self._format)

        # start the live video stream
        self._camera.StartLive(0)

        # disable exposure automatic
        self._camera.SetPropertySwitch("Exposure", "Auto", 0)

        # gain and whitebalance
        self._camera.SetPropertySwitch("Gain", "Auto", 0)
        self._camera.SetPropertyValue("Gain", "Value", 10)
        self._camera.SetPropertyValue("WhiteBalance", "White Balance Red", 64)
        self._camera.SetPropertyValue("WhiteBalance", "White Balance Green", 64)
        self._camera.SetPropertyValue("WhiteBalance", "White Balance Blue", 64)

    def close(self):
        """Close module"""
        BaseCamera.close(self)

        # stop live video stream
        self._camera.StopLive()

    def _expose(self, exposure_time: float, open_shutter: bool, abort_event: threading.Event) -> Image:
        """Actually do the exposure, should be implemented by derived classes.

        Args:
            exposure_time: The requested exposure time in seconds.
            open_shutter: Whether or not to open the shutter.
            abort_event: Event that gets triggered when exposure should be aborted.

        Returns:
            The actual image.

        Raises:
            ValueError: If exposure was not successful.
        """

        # set an absolute exposure time
        self._camera.SetPropertyAbsoluteValue("Exposure", "Value", exposure_time / 1000.)

        # set exposing
        self._change_exposure_status(ExposureStatus.EXPOSING)

        # get date obs
        log.info('Starting exposure with %s shutter for %.2f seconds...',
                 'open' if open_shutter else 'closed', exposure_time / 1000.)
        date_obs = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")

        # Snap an image
        self._camera.SnapImage()

        # Get the image
        data = self._camera.GetImage()[:, :, 1]

        # create FITS image and set header
        img = Image.from_bytes(data)
        img.header['DATE-OBS'] = (date_obs, 'Date and time of start of exposure')
        img.header['EXPTIME'] = (exposure_time / 1000., 'Exposure time [s]')

        # statistics
        img.header['DATAMIN'] = (float(np.min(data)), 'Minimum data value')
        img.header['DATAMAX'] = (float(np.max(data)), 'Maximum data value')
        img.header['DATAMEAN'] = (float(np.mean(data)), 'Mean data value')

        # return FITS image
        log.info('Readout finished.')
        self._change_exposure_status(ExposureStatus.IDLE)
        return img


__all__ = ['TisCamera']
