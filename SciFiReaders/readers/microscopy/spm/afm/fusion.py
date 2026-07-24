"""
Created on Fri Jul 17 2026

@author: Aidan Swanger
"""

import sidpy
from sidpy.sid import Reader
from pathlib import Path
import h5py
import json
import numpy as np

class FSexpReader(Reader):
  """
  Extracts data and metadata from FusionScope HDF5 experiment files
  (.fsexp files) containing images.
  """
  def read(self):
    """
    Reads all image datasets and metadata from the file given in file_path.

    Returns
    --------
    dict[str, sidpy.Dataset]
        Image datasets are keyed by their index and image name.
        Summarized metadata is stored in the reader's metadata.
        Original full metadata is stored in the reader's original_metadata.
    """
    self.file_path = Path(self._input_file_path)

    if not self.file_path.is_file():
        raise ValueError(f"File does not exist: {self.file_path}")

    if not h5py.is_hdf5(self.file_path):
        raise ValueError(f"File is not a valid HDF5 file: {self.file_path}")

    self.original_metadata = self._extract_metadata()
    self.metadata = self._get_metadata_summary(self.original_metadata)

    dataset_dict = {}

    for image_index in range(len(self.metadata["image_datasets"])):
      image_record = self._read_image_data(image_index)
      image_info = self.metadata["image_datasets"][image_index]

      key = image_info["key"]
      dataset_dict[key] = image_record["sidpy_dataset"]

    return dataset_dict

  def _extract_metadata(self):
    """
    Extracts the basic metadata from .fsexp HDF5 file.
    """
    metadata = {}
    metadata["regions"] = {}
    metadata["image_datasets"] = []

    with h5py.File(self.file_path, "r") as h5_file:
      self.top_level_objects = list(h5_file.keys())
      metadata["root_attrs"] = {}

      pipeline_data = h5_file["PipelineData"]

      for key, value in h5_file.attrs.items():
        metadata["root_attrs"][key] = value

      region_names = sorted(
          pipeline_data.keys(),
          key = lambda name: -1 if name == "OverviewRegion" else int(name.split("_")[0])
      )

      for region_name in region_names:
        region_group = pipeline_data[region_name]
        metadata["regions"][region_name] = {}

        if "REGION_INFO" in region_group.attrs:
          region_info_raw = region_group.attrs["REGION_INFO"]

          if isinstance(region_info_raw, bytes):
            region_info_raw = region_info_raw.decode("utf-8")

          metadata["regions"][region_name]["REGION_INFO"] = json.loads(region_info_raw)

        if "SourceFrames" in region_group:
          source_frames = region_group["SourceFrames"]

          metadata["regions"][region_name]["frames"] = {}

          frame_names = sorted(
              source_frames.keys(),
              key = lambda name: (
                  -1 if "OverviewFrame" in name else int(name.split("_")[2]),
                  -1 if "OverviewFrame" in name else int(name.split("_")[4]),
                  int(name.split("_")[0])
              )
          )

          for frame_name in frame_names:
            frame_channel = source_frames[frame_name]
            metadata["regions"][region_name]["frames"][frame_name] = {}

            if "FRAME_INFO" in frame_channel.attrs:
              frame_info_raw = frame_channel.attrs["FRAME_INFO"]

              if isinstance(frame_info_raw, bytes):
                frame_info_raw = frame_info_raw.decode("utf-8")

              metadata["regions"][region_name]["frames"][frame_name]["FRAME_INFO"] = json.loads(frame_info_raw)

            metadata["regions"][region_name]["frames"][frame_name]["datasets"] = {}

            for processing_state in ["Raw", "Processed"]:

              if processing_state not in frame_channel:
                continue

              metadata["regions"][region_name]["frames"][frame_name]["datasets"][processing_state] = {}

              processing_group = frame_channel[processing_state]

              data_index_names = sorted(
                  processing_group.keys(),
                  key = lambda name: int(name.split("_")[-1])
              )

              for data_index_name in data_index_names:
                h5_dataset = processing_group[data_index_name]

                metadata["regions"][region_name]["frames"][frame_name]["datasets"][processing_state][data_index_name] = {
                  "path": h5_dataset.name,
                  "shape": h5_dataset.shape,
                  "dtype": str(h5_dataset.dtype),
                  "attrs": {},
                }

                for key, value in h5_dataset.attrs.items():
                  metadata["regions"][region_name]["frames"][frame_name]["datasets"][processing_state][data_index_name]["attrs"][key] = value

                number = len(metadata["image_datasets"])
                index = f"{number:03d}"

                name = h5_dataset.attrs.get("SUBCHANNEL_NAME") or frame_name or "fsexp image"

                if isinstance(name, bytes):
                  name = name.decode("utf-8")

                name = str(name)

                image_key = f"{index}_{name.replace(' ', '_')}"

                metadata["image_datasets"].append({
                    "key": image_key,
                    "index": index,
                    "path": h5_dataset.name,
                    "region_name": region_name,
                    "frame_name": frame_name,
                    "processing_state": processing_state,
                    "data_index_name": data_index_name,
                    "shape": h5_dataset.shape,
                    "dtype": str(h5_dataset.dtype),
                    "attrs": dict(h5_dataset.attrs)
                  })

    return metadata

  def _get_metadata_summary(self, original_metadata):
    """
    Creates a compact metadata summary.
    """
    summary = {}

    summary["top_level_objects"] = self.top_level_objects
    summary["num_images"] = len(original_metadata.get("image_datasets", []))

    experiment_info_raw = original_metadata["root_attrs"].get("EXPERIMENT_INFO", "{}")
    
    if isinstance(experiment_info_raw, bytes):
      experiment_info_raw = experiment_info_raw.decode("utf-8")

    experiment_info = json.loads(experiment_info_raw)

    summary["experiment_info"] = {
        "experimentName": experiment_info.get("experimentName"),
        "sampleName": experiment_info.get("sampleName"),
        "sampleDescription": experiment_info.get("sampleDescription"),
        "probeId": experiment_info.get("probeId"),
        "probeSerialNumber": experiment_info.get("probeSerialNumber"),
        "creationDateTimeStr_secsSinceEpoch": experiment_info.get("creationDateTimeStr_secsSinceEpoch")
    }

    summary["image_datasets"] = []

    for index, image_info in enumerate(original_metadata["image_datasets"]):
      attrs = image_info.get("attrs", {})

      summary["image_datasets"].append({
          "key": image_info.get("key"),
          "index": image_info.get("index", f"{index:03d}"),
          "region_name": image_info.get("region_name"),
          "frame_name": image_info.get("frame_name"),
          "processing_state": image_info.get("processing_state"),
          "data_index_name": image_info.get("data_index_name"),
          "shape": image_info.get("shape"),
          "dtype": image_info.get("dtype"),
          "subchannel_name": attrs.get("SUBCHANNEL_NAME"),
          "image_range": attrs.get("IMAGE_MINMAXRANGE"),
          "display_origin": attrs.get("DISPLAY_ORIGIN"),
          "path": image_info.get("path")
      })

    return summary

  def _read_image_data(self, image_index):
    """
    Reads one image dataset and returns the image data with its metadata and a sidpy dataset.
    """
    full_dataset_info = self.original_metadata["image_datasets"][image_index]
    dataset_path = full_dataset_info["path"]

    with h5py.File(self.file_path, "r") as h5_file:
      data = h5_file[dataset_path][()]

    region_name = full_dataset_info["region_name"]
    frame_name = full_dataset_info["frame_name"]

    full_region_info = self.original_metadata["regions"][region_name].get("REGION_INFO", {})
    full_frame_info = self.original_metadata["regions"][region_name]["frames"][frame_name].get("FRAME_INFO", {})

    dataset_info = self.metadata["image_datasets"][image_index]

    region_info = {
      "regionName": full_region_info.get("regionName"),
      "regionDescription": full_region_info.get("regionDescription"),
      "regionWidth": full_region_info.get("regionWidth"),
      "regionHeight": full_region_info.get("regionHeight"),
      "regionUnits": full_region_info.get("regionUnits"),
      "regionXOrigin": full_region_info.get("regionXOrigin"),
      "regionYOrigin": full_region_info.get("regionYOrigin"),
      "rotationAngle": full_region_info.get("rotationAngle"),
    }

    frame_info = {
      "frame_number": full_frame_info.get("frame_number"),
      "channel": full_frame_info.get("channel"),
      "frameType": full_frame_info.get("frameType"),
      "frame_valid": full_frame_info.get("frame_valid"),
      "samplesPerLine": full_frame_info.get("samplesPerLine"),
      "num_lines": full_frame_info.get("num_lines"),
      "actual_num_lines": full_frame_info.get("actual_num_lines"),
      "xStart": full_frame_info.get("xStart"),
      "xEnd": full_frame_info.get("xEnd"),
      "yStart": full_frame_info.get("yStart"),
      "yEnd": full_frame_info.get("yEnd"),
      "zScale": full_frame_info.get("zScale"),
      "rotation": full_frame_info.get("rotation"),
    }

    image_data = {
        "image_index": image_index,
        "data": data,
        "dataset_info": dataset_info,
        "region_info": region_info,
        "frame_info": frame_info
    }

    image_data["sidpy_dataset"] = self._create_sidpy_dataset(image_data)

    return image_data

  def _create_sidpy_dataset(self, image_record):
    """
    Converts one image record into a sidpy.Dataset
    """
    image_index = image_record["image_index"]
    data = image_record["data"]

    full_dataset_info = self.original_metadata["image_datasets"][image_index]

    region_name = full_dataset_info["region_name"]
    frame_name = full_dataset_info["frame_name"]

    full_region_info = self.original_metadata["regions"][region_name].get("REGION_INFO", {})
    full_frame_info = self.original_metadata["regions"][region_name]["frames"][frame_name].get("FRAME_INFO", {})

    data_index_number = full_dataset_info["data_index_name"].split("_")[-1]

    raw_metadata_key = f"meta_data_raw_{data_index_number}"
    processed_metadata_key = f"meta_data_processed_{data_index_number}"

    raw_channel_metadata = full_frame_info.get(raw_metadata_key, {})
    processed_channel_metadata = full_frame_info.get(processed_metadata_key, {})

    data_units = raw_channel_metadata.get("datachannel_units")

    if data_units in [None, ""]:
      data_units = processed_channel_metadata.get("datachannel_units")

    if data_units in [None, ""]:
      data_units = "arb.u."

    image_key = full_dataset_info["key"]

    sidpy_data = data.transpose()

    sid_dataset = sidpy.Dataset.from_array(sidpy_data, title = image_key)
    sid_dataset.title = image_key
    sid_dataset.data_type = "image"
    sid_dataset.quantity = image_key
    sid_dataset.units = data_units

    num_y, num_x = data.shape

    x_start = full_frame_info.get("xStart", 0)
    x_end = full_frame_info.get("xEnd", num_x - 1)
    y_start = full_frame_info.get("yStart", 0)
    y_end = full_frame_info.get("yEnd", num_y - 1)

    spatial_units = full_region_info.get("regionUnits")

    if spatial_units in [None, ""]:
      spatial_units = "um"

    x_values = np.linspace(x_start, x_end, num_x)
    y_values = np.linspace(y_start, y_end, num_y)

    sid_dataset.set_dimension(
        0,
        sidpy.Dimension(
            x_values,
            name = "x",
            quantity = "x-axis",
            units = spatial_units,
            dimension_type = "spatial"
        )
    )

    sid_dataset.set_dimension(
        1,
        sidpy.Dimension(
            y_values,
            name = "y",
            quantity = "y-axis",
            units = spatial_units,
            dimension_type = "spatial"
        )
    )

    sid_dataset.metadata = {
        "key": image_key,
        "dataset_info": image_record["dataset_info"],
        "region_info": image_record["region_info"],
        "frame_info": image_record["frame_info"]
    }

    sid_dataset.original_metadata = {
        "key": image_key,
        "dataset_info": full_dataset_info,
        "region_info": full_region_info,
        "frame_info": full_frame_info
    }

    return sid_dataset
