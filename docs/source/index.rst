pyobs-tis
#########

This is a `pyobs <https://www.pyobs.org>`_ (`documentation <https://docs.pyobs.org>`_) module for cameras from
`The Imaging Source <https://www.theimagingsource.com/>`_, accessed via their
`tiscamera <https://github.com/TheImagingSource/tiscamera>`_ GStreamer driver.


Example configuration
*********************

This is an example configuration::

    class: pyobs_tis.TisCamera
    device: DMK 38GX304 24910177
    format: Y800 (640x480)

    # communication
    comm:
      jid: test@example.com
      password: ***


Available classes
*****************

There is one single class for TIS cameras.

TisCamera
=========
.. autoclass:: pyobs_tis.TisCamera
   :members:
   :show-inheritance:
