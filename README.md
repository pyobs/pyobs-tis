*pyobs* for camera from The Imaging Source
==========================================

Install *pyobs-tis*
-------------------
Clone the repository:

    git clone https://github.com/pyobs/pyobs-tis.git


Install dependencies:

    cd pytel-tis
    pip3 install -r requirements
        
And install it:

    python3 setup.py install


Configuration
-------------
The *TisCamera* class is derived from *BaseCamera* (see *pyobs* documentation) and requires at least two parameters:

    device:
        Name of TIS device to open.
    format:
        Image format and size to use.

Thus, a basic module configuration would look like this:

    module:
      class: pyobs_tis.TisCamera
      device: DMK 38GX304 24910177
      format: Y800 (640x480)

Dependencies
------------
* **pyobs** for the core funcionality. It is not included in the *requirements.txt*, so needs to be installed 
  separately.
* [Astropy](http://www.astropy.org/) for FITS file handling.
* [NumPy](http://www.numpy.org/) for array handling.