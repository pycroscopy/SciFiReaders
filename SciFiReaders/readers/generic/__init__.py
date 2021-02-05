"""
Tools to read, data in from generic files

Submodules
----------

.. autosummary::
    :toctree: _autosummary

    ImageReader
"""

from .image import ImageReader

__all__ = ['ImageReader']

all_readers = [ImageReader]
