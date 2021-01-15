"""
The ScopeReaders package

Submodules
----------

.. autosummary::
    :toctree: _autosummary

"""
from .__version__ import version as __version__
from ScopeReaders import em, generic, ion, spm

__all__ = ['__version__', 'em', 'generic', 'ion', 'spm']
# Traditional hierarchical approach - importing submodules


# Making things easier by surfacing all low-level modules directly:

