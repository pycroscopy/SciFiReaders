from .igor_ibw import IgorIBWReader, IgorMatrixReader
from .AR_hdf5  import ARhdf5Reader
from .bruker_nano import BrukerAFMReader
from .gwyddion import GwyddionReader
from .axz import AxzReader
from .mdt import MDTReader
from .wsxm import WSxM1DReader, WSxM2DReader, WSxM3DReader

__all__ = ['IgorIBWReader', 'ARhdf5Reader', 'BrukerAFMReader', 'GwyddionReader', 'IgorMatrixReader', 'AxzReader',
           'WSxM1DReader', 'WSxM2DReader', 'WSxM3DReader','MDTReader']
all_readers = [IgorIBWReader, ARhdf5Reader, BrukerAFMReader, GwyddionReader, IgorMatrixReader, AxzReader,
               WSxM1DReader, WSxM2DReader, WSxM3DReader,MDTReader]