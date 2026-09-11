Available Readers
=================

Each reader is a ``sidpy.Reader`` subclass. Import it from the package and call
``.read()``::

    import SciFiReaders as sr
    dataset = sr.NanonisSXMReader('scan.sxm').read()

Please `get in touch <./contact.html>`_ if you would like to contribute a reader.
See `Creating a Reader <./notebooks/00_developing_a_reader/index.html>`_ for how.

Electron microscopy
-------------------

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Instrument / format
     - Extensions
     - Reader
   * - Gatan DigitalMicrograph
     - ``.dm3``, ``.dm4``
     - ``DMReader``, ``DM3Reader``
   * - Nion Swift
     - ``.ndata``, ``.h5``
     - ``NionReader``
   * - Thermo Fisher / FEI Velox
     - ``.emd``
     - ``EMDReader``
   * - MRC (4D-STEM, Velox export)
     - ``.mrc``
     - ``MRCReader``
   * - EDAX EDS
     - ``.h5``
     - ``EDAXReader``
   * - Bruker EDS
     - ``.rto``
     - ``BrukerReader``

Scanning probe microscopy: AFM
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Instrument / format
     - Extensions
     - Reader
   * - Asylum Research (HDF5 export)
     - ``.h5``
     - ``ARhdf5Reader``
   * - Asylum Research / Igor binary wave
     - ``.ibw``
     - ``IgorIBWReader``, ``IgorMatrixReader``
   * - Bruker Nano / NanoScope
     - vendor files, no fixed extension
     - ``BrukerAFMReader``
   * - Gwyddion
     - ``.gwy``, ``.gsf``
     - ``GwyddionReader``
   * - NT-MDT
     - ``.mdt``
     - ``MDTReader``
   * - Nanosurf
     - ``.nid``
     - ``NanoSurfNIDReader``
   * - Quantum Design FusionScope
     - ``.fsexp``
     - ``FSexpReader``
   * - WSxM
     - ``.top``, ``.stp``, ``.cur``, ``.gsi``, ``.mpp``
     - ``WSxM1DReader``, ``WSxM2DReader``, ``WSxM3DReader``
   * - Molecular Vista PiFM
     - ``.txt``, ``.int``
     - ``PiFMReader``
   * - Anfatec AXZ
     - ``.axz``
     - ``AxzReader``

Scanning probe microscopy: STM
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Instrument / format
     - Extensions
     - Reader
   * - Nanonis scan
     - ``.sxm``
     - ``NanonisSXMReader``
   * - Nanonis spectroscopy
     - ``.dat``
     - ``NanonisDatReader``
   * - Nanonis grid spectroscopy
     - ``.3ds``
     - ``Nanonis3dsReader``
   * - Omicron
     - ``.asc``
     - ``AscReader``

Optical microscopy and spectroscopy
-----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Instrument / format
     - Extensions
     - Reader
   * - Zeiss confocal
     - ``.czi``
     - ``CZIReader``
   * - Princeton Instruments (Raman)
     - ``.spe``
     - ``RamanSpeReader``

Generic and pycroscopy formats
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Format
     - Extensions
     - Reader
   * - Images
     - ``.png``, ``.jpg``, ``.tif``, ``.tiff``, ``.bmp``
     - ``ImageReader``
   * - NSID (N-dimensional spectral imaging data)
     - ``.h5``
     - ``NSIDReader``, ``NSIDWriter``
   * - USID (Universal spectral imaging data)
     - ``.h5``
     - ``Usid_reader``
   * - HyperSpy signals (conversion, not a file reader)
     - —
     - ``convert_hyperspy``