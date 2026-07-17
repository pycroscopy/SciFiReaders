import os
import tempfile
import unittest
from unittest import mock

import h5py
import numpy as np
import sidpy

from SciFiReaders.mcp import scifireaders_mcp


def _make_dataset(data, title):
    dataset = sidpy.Dataset.from_array(np.asarray(data), title=title)
    dataset.units = "counts"
    dataset.quantity = "intensity"
    dataset.data_type = "image"
    dataset.modality = "test"
    dataset.source = "unit-test"
    dataset.set_dimension(
        0,
        sidpy.Dimension(
            np.arange(dataset.shape[0]),
            name="row",
            quantity="distance",
            units="nm",
            dimension_type="spatial",
        ),
    )
    dataset.set_dimension(
        1,
        sidpy.Dimension(
            np.arange(dataset.shape[1]),
            name="col",
            quantity="distance",
            units="nm",
            dimension_type="spatial",
        ),
    )
    return dataset


class DummyReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def read(self):
        return [
            _make_dataset(np.arange(6).reshape(2, 3), "first"),
            _make_dataset(np.arange(6, 12).reshape(2, 3), "second"),
        ]


class DMReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def can_read(self):
        return None


class DM3Reader:
    def __init__(self, file_path):
        self.file_path = file_path

    def can_read(self):
        return None


class NionReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def can_read(self):
        return None


class NoMatchReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def can_read(self):
        return False


class TestMCPExport(unittest.TestCase):
    def test_read_file_exports_nexus_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            raw_path = os.path.join(tmp_dir, "sample.dm4")
            with open(raw_path, "wb") as handle:
                handle.write(b"placeholder")

            with mock.patch.object(
                scifireaders_mcp,
                "_select_reader",
                return_value=(DummyReader, [{"name": "DummyReader", "module": "tests", "doc": ""}]),
            ), mock.patch.object(
                scifireaders_mcp,
                "available_readers",
                return_value=[{"name": "DummyReader", "module": "tests", "doc": ""}],
            ):
                payload = scifireaders_mcp.read_file(raw_path, return_mode="file")

            self.assertEqual(payload["file_path"], raw_path)
            self.assertEqual(payload["return_mode"], "file")
            self.assertEqual(payload["dataset_count"], 2)
            self.assertNotIn("datasets", payload)
            self.assertTrue(payload["output_file_path"].endswith(".dm4.nxs.h5"))
            self.assertTrue(os.path.exists(payload["output_file_path"]))

            with h5py.File(payload["output_file_path"], "r") as h5_file:
                self.assertEqual(h5_file.attrs["default"], "Channel_000")
                self.assertIn("Channel_000", h5_file)
                self.assertIn("Channel_001", h5_file)
                np.testing.assert_allclose(
                    h5_file["Channel_000/data/data"][()],
                    np.arange(6).reshape(2, 3),
                )
                np.testing.assert_allclose(
                    h5_file["Channel_001/data/data"][()],
                    np.arange(6, 12).reshape(2, 3),
                )

    def test_read_file_returns_inline_datasets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            raw_path = os.path.join(tmp_dir, "sample.dm4")
            with open(raw_path, "wb") as handle:
                handle.write(b"placeholder")

            with mock.patch.object(
                scifireaders_mcp,
                "_select_reader",
                return_value=(DummyReader, [{"name": "DummyReader", "module": "tests", "doc": ""}]),
            ), mock.patch.object(
                scifireaders_mcp,
                "available_readers",
                return_value=[{"name": "DummyReader", "module": "tests", "doc": ""}],
            ):
                payload = scifireaders_mcp.read_file(raw_path, return_mode="data")

            self.assertEqual(payload["return_mode"], "data")
            self.assertEqual(payload["dataset_count"], 2)
            self.assertNotIn("output_file_path", payload)
            self.assertIn("datasets", payload)
            self.assertEqual(sorted(payload["datasets"].keys()), ["Channel_000", "Channel_001"])
            np.testing.assert_allclose(
                payload["datasets"]["Channel_000"]["data"],
                np.arange(6).reshape(2, 3),
            )
            np.testing.assert_allclose(
                payload["datasets"]["Channel_001"]["data"],
                np.arange(6, 12).reshape(2, 3),
            )

    def test_read_file_returns_both_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            raw_path = os.path.join(tmp_dir, "sample.dm4")
            with open(raw_path, "wb") as handle:
                handle.write(b"placeholder")

            with mock.patch.object(
                scifireaders_mcp,
                "_select_reader",
                return_value=(DummyReader, [{"name": "DummyReader", "module": "tests", "doc": ""}]),
            ), mock.patch.object(
                scifireaders_mcp,
                "available_readers",
                return_value=[{"name": "DummyReader", "module": "tests", "doc": ""}],
            ):
                payload = scifireaders_mcp.read_file(raw_path, return_mode="both")

            self.assertEqual(payload["return_mode"], "both")
            self.assertIn("datasets", payload)
            self.assertIn("output_file_path", payload)
            self.assertTrue(os.path.exists(payload["output_file_path"]))

    def test_read_file_rejects_invalid_return_mode(self):
        with self.assertRaises(ValueError):
            scifireaders_mcp.read_file("sample.dm4", return_mode="invalid")


class TestMCPReaderSelection(unittest.TestCase):
    def test_select_reader_routes_dm3_to_non_deprecated_reader(self):
        with mock.patch.object(
            scifireaders_mcp,
            "_load_reader_classes",
            return_value=[DMReader, DM3Reader],
        ):
            reader_cls, matched_readers = scifireaders_mcp._select_reader("sample.dm3")

        self.assertIs(reader_cls, DMReader)
        self.assertEqual([reader["name"] for reader in matched_readers], ["DMReader"])

    def test_select_reader_routes_dm4_to_dm_reader(self):
        with mock.patch.object(
            scifireaders_mcp,
            "_load_reader_classes",
            return_value=[DMReader, DM3Reader],
        ):
            reader_cls, matched_readers = scifireaders_mcp._select_reader("sample.dm4")

        self.assertIs(reader_cls, DMReader)
        self.assertEqual([reader["name"] for reader in matched_readers], ["DMReader"])

    def test_select_reader_routes_nion_extensions(self):
        with mock.patch.object(
            scifireaders_mcp,
            "_load_reader_classes",
            return_value=[NoMatchReader, NionReader],
        ):
            ndata_reader, _ = scifireaders_mcp._select_reader("sample.ndata")
            h5_reader, _ = scifireaders_mcp._select_reader("sample.h5")

        self.assertIs(ndata_reader, NionReader)
        self.assertIs(h5_reader, NionReader)

    def test_select_reader_error_includes_suffix_and_tried_readers(self):
        with mock.patch.object(
            scifireaders_mcp,
            "_load_reader_classes",
            return_value=[NoMatchReader],
        ):
            with self.assertRaisesRegex(
                TypeError,
                r"ending in \.unknown.*NoMatchReader",
            ):
                scifireaders_mcp._select_reader("sample.unknown")


if __name__ == "__main__":
    unittest.main()
