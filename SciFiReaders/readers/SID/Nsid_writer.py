# -*- coding: utf-8 -*-
"""
NSIDWriter - mirror of NSIDReader

Writes sidpy.Dataset objects to HDF5 in NSID (pyNSID-style) format such that
SciFiReaders.readers.SID.Nsid_reader.NSIDReader can read them back.

Key compatibility requirements (enforced here):
- Main dataset must have attrs: quantity, units, main_data_name, pyNSID_version,
  data_type, modality, source
- Each axis must be stored as a dataset in the same parent group, whose name
  matches the HDF5 dimension label, and must have attrs: name, quantity, units,
  dimension_type
- Dimension labels MUST be unique (sidpy will error otherwise on readback)
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Union

import numpy as np
import h5py
import sidpy

from pyNSID.io.hdf_utils import link_as_main, write_pynsid_book_keeping_attrs, pynsid_version

def _as_str(val: Any, default: str = "generic") -> str:
    if val is None:
        return default
    if isinstance(val, (bytes, np.bytes_)):
        try:
            return val.decode("utf-8")
        except Exception:
            return str(val)
    return str(val)


def _enum_name_or_default(val: Any, enum_cls: Any, default: str) -> str:
    """
    Normalize sidpy enum-like values to a valid enum member name string.
    Examples:
      DataType.IMAGE -> "IMAGE"
      "DataType.IMAGE" -> "IMAGE"
      "image" -> "IMAGE"
      None -> default
    """
    if val is None:
        return default
    # Already enum
    try:
        if isinstance(val, enum_cls):
            return val.name
    except Exception:
        pass

    s = _as_str(val, default=default).strip()
    if "." in s:
        s = s.split(".")[-1]
    s_up = s.upper()

    try:
        members = enum_cls.__members__
        if s_up in members:
            return s_up
    except Exception:
        pass

    return default


def _safe_unique_name(name: str, taken: set[str]) -> str:
    """
    Ensure an HDF5-safe, unique dataset name within a group.
    """
    base = name.strip() if name else "dim"
    base = base.replace("/", "_").replace("-", "_")
    if base == "":
        base = "dim"
    if base not in taken:
        taken.add(base)
        return base
    k = 1
    while f"{base}_{k}" in taken:
        k += 1
    out = f"{base}_{k}"
    taken.add(out)
    return out


def _write_dict_to_group(h5_group: h5py.Group, data: Mapping[str, Any]) -> None:
    """
    Lightweight recursive dict writer for metadata. Only writes JSON-ish values.
    Skips large arrays/objects to avoid exploding file size.
    """
    for k, v in data.items():
        key = _as_str(k, default="key")
        if key in h5_group:
            del h5_group[key]

        if isinstance(v, Mapping):
            sub = h5_group.create_group(key)
            write_pynsid_book_keeping_attrs(sub)
            _write_dict_to_group(sub, v)
            continue

        # Skip huge arrays (safety)
        if isinstance(v, np.ndarray) and v.size > 1_000_000:
            h5_group.create_dataset(key, data=_as_str(f"<skipped ndarray shape={v.shape} dtype={v.dtype}>"))
            continue

        # Scalars / small arrays
        try:
            arr = np.asarray(v)
            if arr.dtype == object:
                h5_group.create_dataset(key, data=_as_str(v))
            else:
                h5_group.create_dataset(key, data=arr)
        except Exception:
            h5_group.create_dataset(key, data=_as_str(v))


class NSIDWriter:
    """
    Write sidpy.Dataset (or mapping of name -> Dataset) to HDF5 in NSID format.
    """

    def __init__(self, obj: Union[sidpy.Dataset, Mapping[str, sidpy.Dataset]]):
        if isinstance(obj, sidpy.Dataset):
            self._datasets: Dict[str, sidpy.Dataset] = {"Channel_000": obj}
        elif isinstance(obj, Mapping):
            self._datasets = {}
            for i, (k, v) in enumerate(obj.items()):
                if not isinstance(v, sidpy.Dataset):
                    raise TypeError(f"All values must be sidpy.Dataset. Key={k}, type={type(v)}")
                name = _as_str(k, default=f"Channel_{i:03d}")
                self._datasets[name] = v
        else:
            raise TypeError("obj must be a sidpy.Dataset or mapping[str, sidpy.Dataset]")

    def write(
        self,
        path_to_file: str,
        parent_group: str = "/",
        overwrite: bool = False,
        compression: Optional[str] = "gzip",
        compression_opts: int = 4,
        chunks: bool = True,
        write_metadata: bool = True,
    ) -> str:
        mode = "w" if overwrite else "a"
        with h5py.File(path_to_file, mode=mode) as h5_file:
            parent = h5_file[parent_group] if parent_group in h5_file else h5_file.create_group(parent_group)
            write_pynsid_book_keeping_attrs(parent)

            for chan_name, dset in self._datasets.items():
                if chan_name in parent:
                    del parent[chan_name]
                chan_grp = parent.create_group(chan_name)
                write_pynsid_book_keeping_attrs(chan_grp)
                self._write_one(chan_grp, dset, compression, compression_opts, chunks, write_metadata)

        return path_to_file

    def _write_one(
        self,
        h5_group: h5py.Group,
        dset: sidpy.Dataset,
        compression: Optional[str],
        compression_opts: int,
        chunks: bool,
        write_metadata: bool,
    ) -> h5py.Dataset:

        # Main dataset name: use title tail if available
        main_name = _as_str(getattr(dset, "title", None), default="Main").split("/")[-1].strip() or "Main"
        main_name = main_name.replace("-", "_")

        if main_name in h5_group:
            del h5_group[main_name]

        data = np.asarray(dset)

        create_kw = {}
        if compression is not None:
            create_kw.update(dict(compression=compression, compression_opts=compression_opts))
        if chunks:
            create_kw["chunks"] = True

        h5_main = h5_group.create_dataset(main_name, data=data, **create_kw)
        write_pynsid_book_keeping_attrs(h5_main)

        # ---- Required main attrs (check_if_main) ----
        h5_main.attrs["quantity"] = _as_str(getattr(dset, "quantity", None))
        h5_main.attrs["units"] = _as_str(getattr(dset, "units", None))
        h5_main.attrs["main_data_name"] = _as_str(getattr(dset, "title", None), default=main_name)
        h5_main.attrs["pyNSID_version"] = _as_str(pynsid_version)

        # sidpy enums must be member names:
        h5_main.attrs["data_type"] = _enum_name_or_default(getattr(dset, "data_type", None), sidpy.DataType, "UNKNOWN")
        h5_main.attrs["modality"] = _as_str(getattr(dset, "modality", None))
        h5_main.attrs["source"] = _as_str(getattr(dset, "source", None))

        # Helpful
        h5_main.attrs["title"] = _as_str(getattr(dset, "title", None), default=main_name)

        # ---- Dimensions ----
        dim_dict: Dict[int, h5py.Dataset] = {}
        taken_names = set(h5_group.keys())

        axes = getattr(dset, "_axes", None) or getattr(dset, "axes", None)
        # sidpy stores axes in dset._axes (dict). Use that if possible.
        if not isinstance(axes, dict) or len(axes) == 0:
            axes = {i: sidpy.Dimension(np.arange(s), name=f"dim_{i}", units="generic", quantity="generic")
                    for i, s in enumerate(dset.shape)}

        # We must ensure unique dimension LABELS (and that label == dim dataset name).
        used_labels: set[str] = set()

        for dim_ind in range(len(dset.shape)):
            dim_obj = axes.get(dim_ind, None)
            if dim_obj is None:
                dim_obj = sidpy.Dimension(np.arange(dset.shape[dim_ind]),
                                          name=f"dim_{dim_ind}",
                                          units="generic",
                                          quantity="generic")

            raw_label = _as_str(getattr(dim_obj, "name", None), default=f"dim_{dim_ind}")
            label = _safe_unique_name(raw_label, used_labels)

            # Also avoid clashing with existing objects in this group:
            label = _safe_unique_name(label, taken_names)

            values = np.asarray(getattr(dim_obj, "values", None))
            if values is None or values.size == 0:
                values = np.arange(dset.shape[dim_ind])

            if label in h5_group:
                del h5_group[label]
            h5_dim = h5_group.create_dataset(label, data=values)
            write_pynsid_book_keeping_attrs(h5_dim)

            # Critical: attrs['name'] MUST match label so:
            # - link_as_main sets dset.dims[i].label to this value
            # - reader uses dset.parent[label]
            h5_dim.attrs["name"] = label
            h5_dim.attrs["quantity"] = _as_str(getattr(dim_obj, "quantity", None))
            h5_dim.attrs["units"] = _as_str(getattr(dim_obj, "units", None))
            h5_dim.attrs["dimension_type"] = _enum_name_or_default(
                getattr(dim_obj, "dimension_type", None), sidpy.DimensionType, "UNKNOWN"
            )

            dim_dict[dim_ind] = h5_dim

        # Attach scales and set labels
        link_as_main(h5_main, dim_dict)

        # ---- Optional metadata (stored under _metadata to avoid setattr in reader) ----
        if write_metadata:
            md = getattr(dset, "metadata", None)
            if isinstance(md, dict) and len(md) > 0:
                if "_metadata" in h5_group:
                    del h5_group["_metadata"]
                md_g = h5_group.create_group("_metadata")
                write_pynsid_book_keeping_attrs(md_g)
                _write_dict_to_group(md_g, md)

        # Mark group
        h5_group.attrs["sidpy_class"] = "sidpy.Dataset"
        return h5_main
