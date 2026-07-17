SciFiReaders
============

.. image:: https://github.com/pycroscopy/SciFiReaders/actions/workflows/actions.yml/badge.svg
    :target: https://github.com/pycroscopy/SciFiReaders/actions/workflows/actions.yml
    :alt: GitHub Actions

.. image:: https://img.shields.io/pypi/v/SciFiReaders.svg
    :target: https://pypi.org/project/SciFiReaders/
    :alt: PyPI
    
.. image:: https://img.shields.io/conda/vn/conda-forge/SciFiReaders.svg
    :target: https://github.com/conda-forge/SciFiReaders-feedstock
    :alt: conda-forge

.. image:: https://img.shields.io/pypi/l/SciFiReaders.svg
    :target: https://pypi.org/project/SciFiReaders/
    :alt: License

.. image:: http://pepy.tech/badge/SciFiReaders
    :target: http://pepy.tech/project/SciFiReaders
    :alt: Downloads
    
.. image:: https://codecov.io/gh/pycroscopy/SciFiReaders/graph/badge.svg?token=5511SG1YWE
    :target: https://codecov.io/gh/pycroscopy/SciFiReaders
    :alt: Coverage

Tools for extracting data and metadata from scientific data files.
Extracted information are returned as a dictionary of `sidpy.Dataset <https://pycroscopy.github.io/sidpy/_autosummary/sidpy.sid.dataset.Dataset.html#sidpy.sid.dataset.Dataset>`_ objects.

Please see `SciFiReaders documentation website <https://pycroscopy.github.io/SciFiReaders/index.html>`_ for more information.

MCP server
----------

If you want to run the SciFiReaders Model Context Protocol server directly, install the optional MCP extra and launch the console entrypoint:

.. code-block:: bash

    uv sync --extra mcp
    uv run scifireaders_mcp.exe

The server runs over stdio and exposes the ``read_file`` tool.
