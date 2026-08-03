"""
Created on Mon Aug 3 2026

@author: Aidan Swanger
"""

import os
import sys
import unittest
import urllib.request

import numpy as np
import sidpy

sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders

ROOT_PATH = (
    "https://raw.githubusercontent.com/pycroscopy/SciFiDatasets/"
    "main/data/microscopy/spm/afm/"
)

TEST_FILE_NAME = "test_FSexp.fsexp"
IMAGE_KEY = "002_AFM_Topography_(Trace)"

class TestFSexpReader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Download and read the test file once for the entire test class.
        """
        file_url = f"{ROOT_PATH}{TEST_FILE_NAME}"

        cls.file_name = TEST_FILE_NAME

        if not os.path.exists(cls.file_name):
            urllib.request.urlretrieve(file_url, cls.file_name)

        cls.reader = SciFiReaders.FSexpReader(cls.file_name)
        cls.datasets = cls.reader.read()
        cls.image = cls.datasets[IMAGE_KEY]

    def test_fsexp_file(self):
        """
        Test the file-level output structure and expected counts.
        """
        self.assertEqual(os.path.getsize(self.file_name), 12968094)

        self.assertIsInstance(self.datasets, dict)
        self.assertEqual(len(self.datasets), 22)

        self.assertEqual(len(self.reader.metadata), 4)
        self.assertEqual(len(self.reader.original_metadata), 3)

        number_of_frame_groups = sum(len(region.get("frames", {})) for region in self.reader.original_metadata["regions"].values())

        self.assertEqual(number_of_frame_groups, 10)
        self.assertEqual(len(self.reader.original_metadata["regions"]), 5)

    def test_reader_type(self):
        """
        Test that FSexpReader follows the sidpy Reader convention.
        """
        self.assertIsInstance(self.reader, sidpy.Reader)

    def test_read_image(self):
        """
        Test the properties of the selected image.
        """
        image = self.image

        self.assertIsInstance(image, sidpy.Dataset)
        self.assertEqual(image.ndim, 2)
        self.assertEqual(image.shape, (128, 128))
        self.assertEqual(image.data_type.name, "IMAGE")

        self.assertEqual(image.units, "um")
        self.assertEqual(image.title, IMAGE_KEY)
        self.assertEqual(image.quantity, IMAGE_KEY)
        self.assertEqual(image.dtype, np.dtype("float32"))

        self.assertEqual(image.source, "generic")
        self.assertEqual(image.size, 16384)
        self.assertIsNone(image.point_cloud)
        self.assertEqual(image.numblocks, (1, 1))
        self.assertEqual(image.npartitions, 1)
        self.assertEqual(image.nbytes, 65536)
        self.assertEqual(image.modality, "generic")
        self.assertEqual(image.itemsize, 4)
        self.assertIsNone(image.h5_dataset)
        self.assertEqual(image.chunksize, (128, 128))
        self.assertEqual(image.chunks, ((128,), (128,)))

        self.assertIsInstance(image.dim_0, sidpy.Dimension)
        self.assertIsInstance(image.dim_1, sidpy.Dimension)
        self.assertEqual(image.labels[0], "x-axis (um)")
        self.assertEqual(image.labels[1], "y-axis (um)")
        self.assertEqual(image.data_descriptor, f"{IMAGE_KEY} (um)")

    def test_image_metadata(self):
        """
        Test the summarized metadata attached to the selected image.
        """
        metadata = self.image.metadata

        dataset_info = metadata["dataset_info"]
        region_info = metadata["region_info"]
        frame_info = metadata["frame_info"]

        self.assertEqual(metadata["key"], IMAGE_KEY)

        self.assertEqual(dataset_info["index"], "002")
        self.assertEqual(dataset_info["region_name"], "2_Region_2")
        self.assertEqual(dataset_info["frame_name"], "2_Frame_0_Channel_0")
        self.assertEqual(dataset_info["processing_state"], "Raw")
        self.assertEqual(dataset_info["data_index_name"], "DataIndex_0")
        self.assertEqual(dataset_info["shape"], (128, 128))
        self.assertEqual(dataset_info["dtype"], "float32")
        self.assertEqual(dataset_info["subchannel_name"], "AFM Topography (Trace)")
        np.testing.assert_allclose(dataset_info["image_range"], np.array([4.503382, 4.720081], dtype = np.float32))
        self.assertEqual(dataset_info["display_origin"], b"UL")
        self.assertIsInstance(dataset_info["display_origin"], bytes)
        self.assertEqual(dataset_info["path"], "/PipelineData/2_Region_2/SourceFrames/2_Frame_0_Channel_0/Raw/DataIndex_0")

        self.assertEqual(region_info["regionName"], "Auto-Saved Scan")
        self.assertEqual(region_info["regionDescription"], "Auto-saved @ 20260731-115253")
        self.assertEqual(region_info["regionWidth"], 1.0023820400238037)
        self.assertEqual(region_info["regionHeight"], 0.9989622235298157)
        self.assertEqual(region_info["regionUnits"], "")
        self.assertEqual(region_info["regionXOrigin"], -59.999963998794556)
        self.assertEqual(region_info["regionYOrigin"], -72.20000424981117)
        self.assertEqual(region_info["rotationAngle"], 0)

        self.assertEqual(frame_info["frame_number"], 0)
        self.assertEqual(frame_info["channel"], 0)
        self.assertEqual(frame_info["frameType"], 1)
        self.assertEqual(frame_info["frame_valid"], True)
        self.assertEqual(frame_info["samplesPerLine"], 128)
        self.assertEqual(frame_info["num_lines"], 128)
        self.assertEqual(frame_info["actual_num_lines"], 128)
        self.assertEqual(frame_info["xStart"], -59.999963998794556)
        self.assertEqual(frame_info["xEnd"], -58.99758195877075)
        self.assertEqual(frame_info["yStart"], -72.20000424981117)
        self.assertEqual(frame_info["yEnd"], -71.20104202628136)
        self.assertEqual(frame_info["zScale"], 1)
        self.assertEqual(frame_info["rotation"], 0)

    def test_image_original_metadata(self):
        """
        Test the original metadata attached to the selected image.
        """
        original_metadata = self.image.original_metadata

        dataset_info = original_metadata["dataset_info"]
        dataset_attrs = dataset_info["attrs"]
        region_info = original_metadata["region_info"]
        frame_info = original_metadata["frame_info"]

        self.assertEqual(original_metadata["key"], IMAGE_KEY)

        self.assertEqual(dataset_info["index"], "002")
        self.assertEqual(dataset_info["region_name"], "2_Region_2")
        self.assertEqual(dataset_info["frame_name"], "2_Frame_0_Channel_0")
        self.assertEqual(dataset_info["processing_state"], "Raw")
        self.assertEqual(dataset_info["data_index_name"], "DataIndex_0")
        self.assertEqual(dataset_info["shape"], (128, 128))
        self.assertEqual(dataset_info["dtype"], "float32")
        self.assertEqual(dataset_info["path"], "/PipelineData/2_Region_2/SourceFrames/2_Frame_0_Channel_0/Raw/DataIndex_0")

        self.assertIsInstance(dataset_attrs, dict)
        self.assertEqual(dataset_attrs["DISPLAY_ORIGIN"], b"UL")
        self.assertIsInstance(dataset_attrs["DISPLAY_ORIGIN"], bytes)
        np.testing.assert_allclose(dataset_attrs["IMAGE_MINMAXRANGE"], np.array([4.503382, 4.720081], dtype = np.float32))
        self.assertEqual(dataset_attrs["IMAGE_SUBCLASS"], b"IMAGE_GRAYSCALE")
        self.assertIsInstance(dataset_attrs["IMAGE_SUBCLASS"], bytes)
        self.assertEqual(dataset_attrs["IMAGE_VERSION"], b"1.2")
        self.assertIsInstance(dataset_attrs["IMAGE_VERSION"], bytes)
        self.assertEqual(dataset_attrs["IMAGE_WHITE_IS_ZERO"], np.uint8(0))
        self.assertIsInstance(dataset_attrs["IMAGE_WHITE_IS_ZERO"], np.uint8)
        self.assertEqual(dataset_attrs["SUBCHANNEL_NAME"], "AFM Topography (Trace)")

        self.assertEqual(region_info["regionName"], "Auto-Saved Scan")
        self.assertEqual(region_info["regionDescription"], "Auto-saved @ 20260731-115253")
        self.assertEqual(region_info["regionWidth"], 1.0023820400238037)
        self.assertEqual(region_info["regionHeight"], 0.9989622235298157)
        self.assertEqual(region_info["regionUnits"], "")
        self.assertEqual(region_info["regionXOrigin"], -59.999963998794556)
        self.assertEqual(region_info["regionYOrigin"], -72.20000424981117)
        self.assertEqual(region_info["rotationAngle"], 0)
        self.assertEqual(region_info["regionIsCorrelated"], False)
        self.assertEqual(region_info["regionSaveCount"], 2)
        self.assertEqual(region_info["regionSaveId"], 2)
        self.assertEqual(region_info["regionType"], 0)

        self.assertEqual(frame_info["frame_number"], 0)
        self.assertEqual(frame_info["channel"], 0)
        self.assertEqual(frame_info["frameType"], 1)
        self.assertEqual(frame_info["frame_valid"], True)
        self.assertEqual(frame_info["samplesPerLine"], 128)
        self.assertEqual(frame_info["num_lines"], 128)
        self.assertEqual(frame_info["actual_num_lines"], 128)
        self.assertEqual(frame_info["xStart"], -59.999963998794556)
        self.assertEqual(frame_info["xEnd"], -58.99758195877075)
        self.assertEqual(frame_info["yStart"], -72.20000424981117)
        self.assertEqual(frame_info["yEnd"], -71.20104202628136)
        self.assertEqual(frame_info["zScale"], 1)
        self.assertEqual(frame_info["rotation"], 0)
        self.assertEqual(frame_info["current_line"], 127)
        self.assertEqual(frame_info["eds_spectra_group_path"], "")

    def test_reader_metadata(self):
        """
        Test the reader metadata that describes the complete FusionScope experiment.
        """
        experiment_info = self.reader.metadata["experiment_info"]
        root_attrs = self.reader.original_metadata["root_attrs"]

        self.assertEqual(experiment_info["experimentName"], "test")
        self.assertEqual(experiment_info["sampleName"], "gold nanoparticles")
        self.assertEqual(experiment_info["sampleDescription"], "SEM calibration sample")
        self.assertEqual(experiment_info["probeId"], "QDM-S115-nano")
        self.assertEqual(experiment_info["probeSerialNumber"], "002799900004M")
        self.assertEqual(experiment_info["creationDateTimeStr_secsSinceEpoch"], "1785509321")

        self.assertEqual(self.reader.metadata["num_images"], 22)

        self.assertEqual(root_attrs["APPLICATION_VERSION"], "1.3.10.2529")
        self.assertEqual(root_attrs["EXPERIMENT_FILE_VERSION"], "0.0.5")
        np.testing.assert_allclose(root_attrs["OVERVIEW_RECT"], np.array([-4484.30517578, -4484.30517578,  8968.61035156,  8968.61035156]))

        self.assertEqual(len(self.reader.metadata["top_level_objects"]), 3)

    def test_image_values(self):
        """
        Test independently verified values in the selected image.
        """
        image = self.image

        self.assertAlmostEqual(float(image[37, 91]), 4.643936634063721)
        self.assertAlmostEqual(float(image[91, 37]), 4.60664701461792)
        self.assertAlmostEqual(float(image[100, 17]), 4.579700469970703)

    def test_image_dimensions(self):
        """
        Test spatial dimensions and calibration of the selected image.
        """
        image = self.image
        frame_info = image.metadata["frame_info"]
        region_info = image.metadata["region_info"]

        self.assertEqual(image.dim_0.dimension_type, sidpy.DimensionType.SPATIAL)
        self.assertEqual(image.dim_1.dimension_type, sidpy.DimensionType.SPATIAL)

        self.assertEqual(image.dim_0.name, "x")
        self.assertEqual(image.dim_1.name, "y")

        self.assertEqual(len(image.x), image.shape[0])
        self.assertEqual(len(image.y), image.shape[1])

        self.assertEqual(image.x.units, "um")
        self.assertEqual(image.y.units, "um")

        self.assertAlmostEqual(float(image.x[0]), frame_info["xStart"])
        self.assertAlmostEqual(float(image.x[-1]), frame_info["xEnd"])
        self.assertAlmostEqual(float(image.y[0]), frame_info["yStart"])
        self.assertAlmostEqual(float(image.y[-1]), frame_info["yEnd"])

    def test_image_order(self):
        """
        Test the deterministic order of the images.
        """
        image_keys = list(self.datasets.keys())

        self.assertEqual(image_keys[2], IMAGE_KEY)
        self.assertEqual(image_keys[0], "000_1_OverviewFrame")
        self.assertEqual(image_keys[-1], "021_10_Frame_7_Channel_0")

if __name__ == "__main__":
    unittest.main()
