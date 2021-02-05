"""
The ScopeReaders package

Submodules
----------

.. autosummary::
    :toctree: _autosummary

"""
from .__version__ import version as __version__
from .readers import *
from . import ingestor

__all__ = readers.__all__

