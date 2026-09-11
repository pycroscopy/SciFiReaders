SciFiReaders
============

Tools for extracting data and metadata from scientific data files.

What it does
------------

Every instrument vendor saves data in its own file format. SciFiReaders is a collection of
``Reader`` classes, one per format, that open these files and return the data as
`sidpy.Dataset <https://pycroscopy.github.io/sidpy/_autosummary/sidpy.sid.dataset.Dataset.html>`_
objects. A ``sidpy.Dataset`` holds the raw array together with its axes, units, and the
instrument metadata, so the same analysis code works no matter which instrument produced the file.

Main ideas
----------

* One reader per file format. All readers share the same interface: ``Reader(path).read()``.
* The result is a ``sidpy.Dataset`` (or a dictionary of them when a file holds several channels).
  It behaves like a NumPy/Dask array and carries axes, units, and metadata with it.
* Readers only read. Writing to a standard HDF5 layout is done with ``NSIDWriter``
  (see :doc:`notebooks/03_data_formats_and_converters/index`).
* Readers are grouped by scientific method: electron microscopy, scanning probe microscopy,
  spectroscopy, and so on. The package layout under ``SciFiReaders/readers`` follows the same grouping.
* Adding a new format takes a few lines once you can already parse the file.
  See :doc:`notebooks/00_developing_a_reader/index`.

Quick example
-------------

.. code-block:: python

   import SciFiReaders as sr

   reader = sr.DM3Reader('EELS_STO.dm3')
   dataset = reader.read()

   print(dataset)            # shape, axes, units
   dataset.plot()            # quick look

.. toctree::
   :maxdepth: 1
   :caption: Getting started

   install
   available_readers
   contact

.. toctree::
   :maxdepth: 2
   :caption: Examples by method

   notebooks/00_developing_a_reader/index
   notebooks/01_electron_microscopy/index
   notebooks/02_scanning_probe_microscopy/index
   notebooks/03_data_formats_and_converters/index

.. toctree::
   :maxdepth: 1
   :caption: Reference

   api