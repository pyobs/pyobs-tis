*pyobs* for cameras from The Imaging Source
============================================

This is a [pyobs](https://www.pyobs.org) module for cameras from
[The Imaging Source](https://www.theimagingsource.com/), accessed via their
[tiscamera](https://github.com/TheImagingSource/tiscamera) GStreamer driver.


System dependencies
--------------------
The tiscamera driver and its GObject introspection bindings are not pip-installable, so they need to be installed
via your system's package manager before installing *pyobs-tis*.

On Debian/Ubuntu:

    sudo apt-get install python3-gi python3-gi-cairo gir1.2-gstreamer-1.0

This provides **PyGObject** (`python3-gi`, `python3-gi-cairo`), the `gi` module used to access GStreamer/tcam
from Python. The tiscamera driver itself (providing the `Tcam` GObject introspection typelib) is not packaged
for Debian/Ubuntu and needs to be installed separately, either from a
[release package](https://github.com/TheImagingSource/tiscamera/releases) or the
[the-imaging-source PPA](https://launchpad.net/~the-imaging-source/+archive/ubuntu/tiscamera).

Since these packages are installed system-wide, your virtual environment needs access to the system
site-packages so it can find the `gi` module.


Install *pyobs-tis*
-------------------
Clone the repository:

    git clone https://github.com/pyobs/pyobs-tis.git
    cd pyobs-tis

Create a virtual environment with access to the system site-packages and install the package with
[uv](https://docs.astral.sh/uv/):

    uv venv --system-site-packages
    uv sync

Alternatively, with plain `venv`/`pip`:

    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    pip install .


Configuration
-------------
The *TisCamera* class is derived from *BaseVideo* (see *pyobs* documentation) and requires at least two
parameters:

    device:
        Name of TIS device to open.
    format:
        Image format and size to use.

A basic module configuration would look like this:

    class: pyobs_tis.TisCamera
    device: DMK 38GX304 24910177
    format: Y800 (640x480)


Dependencies
------------
* [pyobs-core](https://github.com/pyobs/pyobs-core) for the core functionality.
* [NumPy](https://numpy.org/) for array handling.
* [tiscamera](https://github.com/TheImagingSource/tiscamera) and [PyGObject](https://pygobject.readthedocs.io/)
  for accessing the camera, installed via the system's package manager (see above).
