import unittest
import sys
import os
import sidpy
from pywget import wget
from matplotlib import pyplot as plt


sys.path.append("../../../../../SciFiReaders/")
if __name__ == '__main__':
    sys.path.append("../SciFiReaders/")

import SciFiReaders as sr

root_path = "https://github.com/pycroscopy/SciFiDatasets/blob/main/data/microscopy/spm/afm/wsxm/"
# root_path = "https://github.com/PranavSudersan/SciFiDatasets/blob/eabc7a708e316bdf19cd344c603f014b99c3daea/data/microscopy/spm/afm/wsxm/"
data_files = {
    '1d': [
        'WSxM1DReader_spectrocurve_0001_Normalforce.f.curves',
        'WSxM1DReader_spectrocurve_0001_Amplitude.f.curves'
    ],
    '2d': [
        'WSxM2DReader_jumpingmodeimage_0002_Topography.f.dy.top',
        'WSxM2DReader_jumpingmodeimage_0002_Adhesion.f.dy.jm.adh'
    ],
    '3d': [
        'WSxM3DReader_Forcevolume_0003_Amplitude.ff.ch15.gsi',
        'WSxM3DReader_Forcevolume_0003_Normalforce.ff.ch1.gsi'
    ]
}

class TestWSxM(unittest.TestCase):

    def download_files(self, file_type):
        for file_i in data_files[file_type]:
            if not os.path.exists(file_i):
                print(root_path + file_i + "?raw=true")
                wget.download(root_path + file_i + "?raw=true", out=file_i) 
    
    def clear_files(self, file_type):
        for file_i in data_files[file_type]:
            if os.path.exists(file_i):
                os.remove(file_i)

    def test_wsxm_1d_file(self):
        self.download_files('1d')
        # Test if the force curve file can be successfully read
        for file_path in data_files['1d'][:1]: #only first file read, second file should be detected by the reader automatically
            data_translator = sr.WSxM1DReader(file_path)
            datasets = data_translator.read()
            assert len(datasets.keys()) == 10, "Length of dataset should be 10 but is instead {}".format(len(datasets))
            
            for chan, data in datasets.items():
                assert type(data)== sidpy.sid.dataset.Dataset, "Dataset No. {} not read in as sidpy dataset" \
                        "but was instead read in as {}".format(type(data))

                assert data.shape[0]==512, "Dataset[{}] is of size 512 but was read in as {}".format(data.shape[0])
                assert type(data._axes[0]) == sidpy.sid.dimension.Dimension, "Dataset should have dimension type " \
                                            "of sidpy Dimension, but is instead {}".format(type(data._axes))
                print(chan, data.quantity, data.direction)
                print(data.metadata['File path'])
                data.plot() # Plot the data

        self.clear_files('1d')
        print("\nWSxM 1D files read successfully")
        plt.show()
        print("WSxM 1D data plotted successfully\n")

    def test_wsxm_2d_file(self):
        self.download_files('2d')
        # Test if the image file can be read in correctly
        for file_path in data_files['2d'][:1]: #only first file read, second file should be detected by the reader automatically
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
                print(chan, data.quantity, data.direction)
                print(data.metadata['File path'])
                data.plot() # Plot the data

        self.clear_files('2d')
        print("\nWSxM 2D files read successfully")
        plt.show()
        print("WSxM 2D data plotted successfully\n")

    def test_wsxm_3d_file(self):
        self.download_files('3d')
        # Test if the force volume file can be read in correctly
        for file_path in data_files['3d'][:1]: #only first file read, second file should be detected by the reader automatically
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
                print(chan, data.quantity, data.direction)
                print(data.metadata['File path'])
                data.plot() # Plot the data

        self.clear_files('3d')
        print("\nWSxM 3D files read successfully")
        plt.show()
        print("WSxM 3D data plotted successfully\n")

if __name__ == '__main__':     
    test = TestWSxM()
    test.test_wsxm_1d_file()
    test.test_wsxm_2d_file()
    test.test_wsxm_3d_file()