"""Unit tests for non-hardware logic in TisCamera: constructor state and the image
throttle gating in new_image().

Opening the camera and talking to GStreamer/Tcam is out of scope here.
"""

import time
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from pyobs_tis import TisCamera


def test_constructor_stores_device_and_format() -> None:
    camera = TisCamera(device="serial123", format="GRAY8")
    assert camera._device == "serial123"
    assert camera._format == "GRAY8"
    assert camera._camera is None


@pytest.mark.asyncio
async def test_new_image_throttles_within_interval() -> None:
    camera = TisCamera(device="dummy", format="GRAY8")
    camera._last_image_time = time.time()  # an image just arrived
    camera._set_image = AsyncMock()  # type: ignore[method-assign]

    await camera.new_image(MagicMock())

    camera._set_image.assert_not_called()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_new_image_processes_when_due() -> None:
    camera = TisCamera(device="dummy", format="GRAY8")
    camera._last_image_time = None
    camera._camera = MagicMock()
    camera._camera.Get_image.return_value = np.zeros((10, 10, 1), dtype=np.uint8)
    camera._set_image = AsyncMock()  # type: ignore[method-assign]

    await camera.new_image(MagicMock())

    camera._set_image.assert_called_once()  # type: ignore[union-attr]
    assert camera._last_image_time is not None
