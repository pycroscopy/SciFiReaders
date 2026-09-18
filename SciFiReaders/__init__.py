"""
The ScopeReaders package

Submodules
----------

.. autosummary::
    :toctree: _autosummary

"""
from .__version__ import version as __version__
from .readers import *
from .auto_reader import AutoReader

__all__ = readers.__all__ + ['AutoReader']