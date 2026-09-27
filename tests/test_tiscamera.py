"""Unit tests for non-hardware logic in TisCamera: constructor state and new_image().

Opening the camera and talking to GStreamer/Tcam is out of scope here.
"""

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
async def test_new_image_processes_every_frame() -> None:
    """No throttle in new_image(): every frame delivered to it is passed to _set_image()
    (BaseVideo's own video_handler/_set_image() throttle the live-view JPEG output instead)."""
    camera = TisCamera(device="dummy", format="GRAY8")
    camera._camera = MagicMock()
    camera._camera.Get_image.return_value = np.zeros((10, 10, 1), dtype=np.uint8)
    camera._set_image = AsyncMock()  # type: ignore[method-assign]

    await camera.new_image(MagicMock())
    await camera.new_image(MagicMock())

    assert camera._set_image.call_count == 2  # type: ignore[union-attr]
