"""Smoke tests: import the driver and instantiate it without hardware, asserting it
advertises the interfaces it claims.

The vendor GStreamer wrapper ``pyobs_tis.TIS`` imports ``gi`` + the GStreamer/Tcam
typelibs at import time, so it is deliberately not imported here -- it only loads inside
``open()``, which needs real hardware anyway.
"""

from pyobs.interfaces import IImageType, IVideo
from pyobs.modules import Module

from pyobs_tis import TisCamera


def test_import_tiscamera_and_instantiate() -> None:
    camera = TisCamera(device="dummy", format="GRAY8")
    assert isinstance(camera, Module)
    assert isinstance(camera, IVideo)
    assert isinstance(camera, IImageType)
