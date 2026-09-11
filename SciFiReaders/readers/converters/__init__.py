"""
Converters from other packages' data objects to sidpy.Dataset

Submodules
----------

.. autosummary::
    :toctree: _autosummary

    hyperspy
"""

from .hyperspy import convert_hyperspy

__all__ = ['convert_hyperspy']

all_readers = [convert_hyperspy]
