"""Unit tests for non-hardware logic in TisCamera: constructor state, frames() and the exposure
time read-back. The TIS GStreamer wrapper is replaced by a fake.
"""

import threading
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import numpy.typing as npt
import pytest

from pyobs_tis import TisCamera


class FakeTIS:
    """Stands in for pyobs_tis.TIS.TIS: start_pipeline() delivers the given frames via the callback
    on a separate thread, like GStreamer does."""

    def __init__(self, frames: list[npt.NDArray[Any]], start_ok: bool = True) -> None:
        self.frames = frames
        self.start_ok = start_ok
        self.calls: list[str] = []
        self.callback: Any = None
        self.img: npt.NDArray[Any] | None = None
        self.exposure_us = 20000.0

    def Set_Image_Callback(self, function: Any) -> None:
        self.callback = function

    def Start_pipeline(self) -> bool:
        self.calls.append("start")
        if self.start_ok:
            threading.Thread(target=self._deliver, daemon=True).start()
        return self.start_ok

    def _deliver(self) -> None:
        for frame in self.frames:
            self.img = frame
            self.callback(self)

    def Stop_pipeline(self) -> None:
        self.calls.append("stop")

    def Get_image(self) -> npt.NDArray[Any] | None:
        return self.img

    def Get_Property(self, name: str) -> Any:
        if name != "Exposure Time (us)":
            raise ValueError(f"No property {name}")
        return MagicMock(value=self.exposure_us)


def _camera(fake: FakeTIS, **kwargs: Any) -> TisCamera:
    camera = TisCamera(device="dummy", format="GRAY8", **kwargs)
    camera._camera = fake
    return camera


def _frame(value: int) -> npt.NDArray[Any]:
    return np.full((2, 3, 1), value, dtype=np.uint8)


def test_constructor_stores_device_and_format() -> None:
    camera = TisCamera(device="serial123", format="GRAY8")
    assert camera._device == "serial123"
    assert camera._format == "GRAY8"
    assert camera._exposure_property == "Exposure Time (us)"
    assert camera._camera is None


@pytest.mark.asyncio
async def test_frames_yields_every_frame_and_stops_pipeline_on_close() -> None:
    fake = FakeTIS([_frame(i) for i in range(3)])
    camera = _camera(fake)

    iterator = camera.frames()
    frames = [await anext(iterator) for _ in range(3)]
    await iterator.aclose()

    assert [int(f.data[0, 0]) for f in frames] == [0, 1, 2]
    assert all(f.data.shape == (2, 3) for f in frames)
    assert all(f.exposure_time == 0.02 and f.start is None for f in frames)
    assert fake.calls == ["start", "stop"]


@pytest.mark.asyncio
async def test_frames_raises_if_pipeline_does_not_start() -> None:
    fake = FakeTIS([], start_ok=False)
    camera = _camera(fake)

    with pytest.raises(RuntimeError, match="Could not start pipeline"):
        await anext(camera.frames())
    assert fake.calls == ["start", "stop"]


@pytest.mark.asyncio
async def test_unknown_exposure_property_disables_reading() -> None:
    fake = FakeTIS([_frame(0), _frame(1)])
    camera = _camera(fake, exposure_property="Nope")

    iterator = camera.frames()
    frames = [await anext(iterator) for _ in range(2)]
    await iterator.aclose()

    assert all(f.exposure_time is None for f in frames)
    assert camera._exposure_property is None


def test_exposure_time_is_cached_between_refreshes() -> None:
    fake = FakeTIS([])
    camera = _camera(fake)

    assert camera._read_exposure_time(fake) == 0.02
    fake.exposure_us = 50000.0
    assert camera._read_exposure_time(fake) == 0.02
    camera._exposure_read = 0.0
    assert camera._read_exposure_time(fake) == 0.05


def test_no_exposure_property() -> None:
    fake = FakeTIS([])
    camera = _camera(fake, exposure_property=None)
    assert camera._read_exposure_time(fake) is None
