import unittest
import sys
import sidpy
from pywget import wget
import os

sys.path.append("../../../../../SciFiReaders/")
if __name__ == '__main__':
    sys.path.append("../SciFiReaders/")

import SciFiReaders as sr

root_path = "https://github.com/pycroscopy/SciFiDatasets/blob/main/data/microscopy/spm/afm/wsxm/"
data_files = {
    '1d': [
        'WsXM1DReader_spectrocurve_0001_Normal force.f.curves',
        'WsXM1DReader_spectrocurve_0001_Normal force.f.curves'
    ],
    '2d': [
        'WsXM2DReader_jumpingmodeimage_0002_Topography.f.dy.top',
        'WsXM2DReader_jumpingmodeimage_0002_Topography.f.dy.top'
    ],
    '3d': [
        'WsXM3DReader_Forcevolume_0003_Normal force.ff.ch1.gsi',
        'WsXM3DReader_Forcevolume_0003_Normal force.ff.ch1.gsi'
    ]
}


class TestWSxM(unittest.TestCase):

    def download_files(self, file_type):
        for file_i in data_files[file_type]:
            if not os.path.exists(file_i):
                wget.download(root_path + file_i + "?raw=true", out=file_i)
    
    def clear_files(self, file_type):
        for file_i in data_files[file_type]:
            if os.path.exists(file_i):
                os.remove(file_i)

    def test_wsxm_1d_file(self):
        self.download_files('1d')
        # Test if the force curve file can be successfully read
        file_path = 'WSxM1DReader_spectrocurve_0001_Normal force.f.curves'
        data_translator = sr.WSxM1DReader(file_path)
        datasets = data_translator.read()
        assert len(datasets.keys()) == 10, "Length of dataset should be 10 but is instead {}".format(len(datasets))
        
        for chan, data in datasets.items():
            assert type(data)== sidpy.sid.dataset.Dataset, "Dataset No. {} not read in as sidpy dataset" \
                    "but was instead read in as {}".format(type(data))

            assert data.shape[0]==512, "Dataset[{}] is of size 512 but was read in as {}".format(data.shape[0])
            assert type(data._axes[0]) == sidpy.sid.dimension.Dimension, "Dataset should have dimension type " \
                                           "of sidpy Dimension, but is instead {}".format(type(data._axes))

        self.clear_files('1d')
        print("WSxM 1D file read successfully")

    def test_wsxm_2d_file(self):
        self.download_files('2d')
        # Test if the image file can be read in correctly
        file_path = 'WSxM2DReader_jumpingmodeimage_0002_Topography.f.dy.top'
        data_translator = sr.WSxM2DReader(file_path)
        datasets = data_translator.read()
        assert len(datasets.keys()) == 2, "Length of dataset should be 2 but is instead {}".format(len(datasets))
        
        for chan, data in datasets.items():
            assert type(data)== sidpy.sid.dataset.Dataset, "Dataset No. {} not read in as sidpy dataset" \
                    "but was instead read in as {}".format(type(data))

            assert data.shape==(256,256), "Dataset[{}] is of size (256,256) but was read in as {}".format(data.shape)
            assert type(data._axes[0]) == sidpy.sid.dimension.Dimension, "Dataset should have 1st dimension type " \
                                           "of sidpy Dimension, but is instead {}".format(type(data._axes))
            assert type(data._axes[1]) == sidpy.sid.dimension.Dimension, "Dataset should have 2nd dimension type " \
                                           "of sidpy Dimension, but is instead {}".format(type(data._axes))

        self.clear_files('2d')
        print("WSxM 2D file read successfully")

    def test_wsxm_3d_file(self):
        self.download_files('3d')
        # Test if the force volume file can be read in correctly
        file_path = 'WSxM3DReader_Forcevolume_0003_Normal force.ff.ch1.gsi'
        data_translator = sr.WSxM3DReader(file_path)
        datasets = data_translator.read()

        assert len(datasets.keys()) == 2, "Length of dataset should be 2 but is instead {}".format(len(datasets))
        
        for chan, data in datasets.items():
            assert type(data)== sidpy.sid.dataset.Dataset, "Dataset No. {} not read in as sidpy dataset" \
                    "but was instead read in as {}".format(type(data))
            assert data.shape==(512,64,64), "Dataset[{}] is of size (64,64,512) but was read in as {}".format(data.shape)
            assert type(data._axes[0]) == sidpy.sid.dimension.Dimension, "Dataset should have 1st dimension type " \
                                           "of sidpy Dimension, but is instead {}".format(type(data._axes))
            assert type(data._axes[1]) == sidpy.sid.dimension.Dimension, "Dataset should have 2nd dimension type " \
                                           "of sidpy Dimension, but is instead {}".format(type(data._axes))
            assert type(data._axes[2]) == sidpy.sid.dimension.Dimension, "Dataset should have 3rd dimension type " \
                                           "of sidpy Dimension, but is instead {}".format(type(data._axes))

        self.clear_files('3d')
        print("WSxM 3D file read successfully")

if __name__ == '__main__':        
    test = TestWSxM()
    test.test_wsxm_1d_file()
    test.test_wsxm_2d_file()
    test.test_wsxm_3d_file()