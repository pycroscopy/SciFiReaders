"""
Tools to read, data in from generic files

Submodules
----------

.. autosummary::
    :toctree: _autosummary

    ImageReader
"""

from .hyperspy import convert_hyperspy

__all__ = ['convert_hyperspy']

all_readers = [convert_hyperspy]
