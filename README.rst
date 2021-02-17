SciFiReaders
============

.. image:: https://github.com/pycroscopy/SciFiReaders/workflows/build/badge.svg?branch=master
    :target: https://github.com/pycroscopy/SciFiReaders/actions?query=workflow%3Abuild
    :alt: GitHub Actions

.. image:: https://img.shields.io/pypi/v/SciFiReaders.svg
    :target: https://pypi.org/project/SciFiReaders/
    :alt: PyPI

.. image:: https://img.shields.io/pypi/l/SciFiReaders.svg
    :target: https://pypi.org/project/SciFiReaders/
    :alt: License

.. image:: http://pepy.tech/badge/SciFiReaders
    :target: http://pepy.tech/project/SciFiReaders
    :alt: Downloads

Tools for extracting data and metadata from scientific data files. Will read them into Sidpy datasets or lists of sidpy datasets. 

Currently supporting the following formats:

Generic:
    - Image reader - for generic image formats
Microscopy:
    Electron microscopy:
        - Nion
        - DM3
    Scanning probe microscopy:
        - ARhdf5 (Asylum Research)
        - Igor ibw
        - Omicro asc
    SID:
        - USID (Universal spectral imaging data model)
        - NSID (N-dimensional spectral imaging data model)

