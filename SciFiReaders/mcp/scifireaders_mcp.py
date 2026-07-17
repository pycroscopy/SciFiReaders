"""
Model Context Protocol server for SciFiReaders.

The server intentionally exposes a single tool:
``read_file``. It automatically selects the best reader from the package's
registered readers, executes that reader, and can either return serialized
dataset content, export it to a NeXus-compatible HDF5 file, or do both.
"""

from __future__ import annotations

import importlib
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence
from warnings import warn

import h5py
import numpy as np
from sidpy import sidpy_to_nexus_hdf5

try:  # pragma: no cover - optional runtime dependency
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - optional runtime dependency
    FastMCP = None


def _as_builtin(value: Any) -> Any:
    """Convert nested numpy/sidpy-heavy structures into JSON-friendly values."""
    if isinstance(value, dict):
        return {str(key): _as_builtin(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_as_builtin(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        for encoding in ("utf-8", "latin-1"):
            try:
                return value.decode(encoding)
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Enum):
        return value.name
    return value


def _load_reader_classes() -> list[type]:
    """Import the package reader registry lazily."""
    readers_module = importlib.import_module("SciFiReaders.readers")
    return list(getattr(readers_module, "all_readers", []))


def _reader_summary(reader_cls: type) -> Dict[str, Any]:
    """Return a short, serializable description of a reader class."""
    doc = (reader_cls.__doc__ or "").strip()
    return {
        "name": reader_cls.__name__,
        "module": reader_cls.__module__,
        "doc": doc.splitlines()[0] if doc else "",
    }


_EXTENSION_READER_MAP: dict[str, set[str]] = {
    ".bmp": {"imagereader"},
    ".czi": {"czireader"},
    ".dm3": {"dmreader", "dm3reader"},
    ".dm4": {"dmreader"},
    ".emd": {"emdreader"},
    ".h5": {"edaxreader", "nionreader"},
    ".ibw": {"igoribwreader"},
    ".jpeg": {"imagereader"},
    ".jpg": {"imagereader"},
    ".mrc": {"mrcreader"},
    ".ndata": {"nionreader"},
    ".png": {"imagereader"},
    ".spe": {"ramanspereader"},
    ".tif": {"imagereader"},
    ".tiff": {"imagereader"},
}


def _matches_extension(reader_cls: type, file_suffix: str) -> bool:
    """Best-effort extension routing for legacy readers whose can_read() is not compatible."""
    suffix = file_suffix.lower()
    module_name = reader_cls.__module__.lower()
    class_name = reader_cls.__name__.lower()
    expected_classes = _EXTENSION_READER_MAP.get(suffix, set())

    if class_name in expected_classes:
        return True
    if "imagereader" in expected_classes and module_name.endswith("generic.image"):
        return True
    if "ramanspereader" in expected_classes and "spe" in module_name:
        return True
    return False


def _is_deprecated_reader(reader_cls: type) -> bool:
    """Return True for reader classes kept only for backward compatibility."""
    return reader_cls.__name__.lower() == "dm3reader"


def _preferred_reader(matches: Sequence[type]) -> type:
    """Choose a reader while avoiding deprecated aliases when possible."""
    active_matches = [reader_cls for reader_cls in matches if not _is_deprecated_reader(reader_cls)]
    if active_matches:
        return active_matches[-1]
    return matches[-1]


def available_readers() -> list[Dict[str, Any]]:
    """Advertise the reader classes currently registered by the package."""
    try:
        reader_classes = _load_reader_classes()
    except Exception as exc:  # pragma: no cover - runtime import problems
        return [{"name": "<unavailable>", "module": "", "doc": f"Could not load readers: {exc}"}]
    return [_reader_summary(reader_cls) for reader_cls in reader_classes]


def _is_dataset_like(value: Any) -> bool:
    """Best-effort check for sidpy.Dataset without importing sidpy eagerly."""
    if (
        hasattr(value, "compute")
        and hasattr(value, "shape")
        and hasattr(value, "metadata")
        and hasattr(value, "get_dimension_by_number")
    ):
        return True
    return False


def _dimension_payload(dataset: Any, index: int) -> Dict[str, Any]:
    """Serialize a single sidpy dimension."""
    try:
        dimension = dataset.get_dimension_by_number(index)[0]
    except Exception:
        return {"index": index}

    return {
        "index": index,
        "name": getattr(dimension, "name", f"dim_{index}"),
        "quantity": getattr(dimension, "quantity", ""),
        "units": getattr(dimension, "units", ""),
        "dimension_type": getattr(getattr(dimension, "dimension_type", None), "name", str(getattr(dimension, "dimension_type", ""))),
        "values": _as_builtin(getattr(dimension, "values", [])),
    }


def _dataset_payload(dataset: Any) -> Dict[str, Any]:
    """Convert a sidpy.Dataset into a serializable dictionary."""
    try:
        data = dataset.compute()
    except Exception:
        data = np.asarray(dataset)

    shape = list(getattr(dataset, "shape", np.asarray(data).shape))
    dimensions = [_dimension_payload(dataset, index) for index in range(len(shape))]
    data_type = getattr(dataset, "data_type", None)
    data_type_name = getattr(data_type, "name", str(data_type)) if data_type is not None else "UNKNOWN"

    return {
        "title": getattr(dataset, "title", ""),
        "quantity": getattr(dataset, "quantity", ""),
        "units": getattr(dataset, "units", ""),
        "data_type": data_type_name,
        "shape": shape,
        "dtype": str(getattr(np.asarray(data), "dtype", "")),
        "labels": _as_builtin(getattr(dataset, "labels", [])),
        "data": _as_builtin(data),
        "metadata": _as_builtin(getattr(dataset, "metadata", {})),
        "original_metadata": _as_builtin(getattr(dataset, "original_metadata", {})),
        "dimensions": dimensions,
    }


def _flatten_dataset_items(value: Any, prefix: str = "Channel") -> list[tuple[str, Any]]:
    """Collect dataset-like objects from nested reader output."""
    items: list[tuple[str, Any]] = []

    if _is_dataset_like(value):
        items.append((prefix, value))
        return items

    if isinstance(value, Mapping):
        for key, item in value.items():
            child_prefix = str(key) if str(key).strip() else prefix
            items.extend(_flatten_dataset_items(item, child_prefix))
        return items

    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_flatten_dataset_items(item, f"{prefix}_{index:03d}"))
        return items

    return items


def _sanitize_hdf5_name(name: str, fallback: str) -> str:
    """Normalize names so they are safe and predictable in HDF5 paths."""
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", str(name).strip()).strip("_")
    return cleaned or fallback


def _output_hdf5_path(file_path: str) -> str:
    """Return the generated NeXus HDF5 path for the provided source file."""
    source = Path(file_path)
    return str(source.with_suffix(source.suffix + ".nxs.h5"))


def _write_datasets_to_nexus(file_path: str, datasets: Sequence[tuple[str, Any]]) -> str:
    """Persist one or more sidpy datasets into a NeXus HDF5 file."""
    if not datasets:
        raise TypeError("The selected reader did not return any sidpy.Dataset objects to export.")

    output_path = _output_hdf5_path(file_path)

    with h5py.File(output_path, "w") as h5_file:
        used_entry_names: set[str] = set()
        default_entry_name = None

        for index, (name, dataset) in enumerate(datasets):
            entry_name = _sanitize_hdf5_name(name, f"entry_{index:03d}")
            if entry_name in used_entry_names:
                entry_name = f"{entry_name}_{index:03d}"
            used_entry_names.add(entry_name)

            signal_path = sidpy_to_nexus_hdf5(
                dataset,
                h5_file,
                entry_name=entry_name,
                nxdata_name="data",
                signal_name="data",
            )
            if default_entry_name is None:
                default_entry_name = signal_path.parent.parent.name.lstrip("/")

        if default_entry_name is not None:
            h5_file.attrs["default"] = default_entry_name
        h5_file.flush()

    return output_path


def _serialize_result(result: Any) -> Any:
    """Recursively serialize reader output."""
    if _is_dataset_like(result):
        return _dataset_payload(result)
    if isinstance(result, Mapping):
        return {str(key): _serialize_result(val) for key, val in result.items()}
    if isinstance(result, (list, tuple)):
        return [_serialize_result(item) for item in result]
    return _as_builtin(result)


def _looks_like_dataset_payload(value: Any) -> bool:
    """Detect a serialized single-dataset payload."""
    if not isinstance(value, dict):
        return False
    return {"title", "shape", "data_type", "data"}.issubset(value.keys())


def _select_reader(file_path: str) -> tuple[type, list[Dict[str, Any]]]:
    """Select the best matching reader using the package's own registry."""
    reader_classes = _load_reader_classes()
    matches: list[type] = []
    file_suffix = str(Path(file_path).suffix).lower()

    for reader_cls in reader_classes:
        if _is_deprecated_reader(reader_cls) and any(not _is_deprecated_reader(match) for match in matches):
            continue
        if _matches_extension(reader_cls, file_suffix):
            matches.append(reader_cls)
            continue
        try:
            candidate = reader_cls(file_path)
            readable = candidate.can_read()
        except TypeError:
            # Older SciFiReaders readers call sidpy.Reader.can_read(extension=...)
            # which no longer exists in newer sidpy releases. Fall back to
            # extension-based routing for those readers.
            continue
        except Exception:
            continue
        if readable:
            matches.append(reader_cls)

    if not matches:
        tried_readers = ", ".join(reader_cls.__name__ for reader_cls in reader_classes)
        suffix_detail = file_suffix or "<no suffix>"
        raise TypeError(
            "The automatic search for a suitable reader was unsuccessful "
            f"for files ending in {suffix_detail}. Tried readers: {tried_readers}."
        )

    selected_reader = _preferred_reader(matches)

    if len(matches) > 1:
        warn(
            "Multiple readers may be able to read this file. "
            f"Using {selected_reader.__name__}."
        )

    return selected_reader, [_reader_summary(reader_cls) for reader_cls in matches]


def read_file(file_path: str, return_mode: str = "file") -> Dict[str, Any]:
    """
    Read a file with the appropriate SciFiReaders reader.

    The payload includes:
    - ``available_readers``: all registered readers in the package
    - ``matched_readers``: readers that reported they could read the file
    - ``selected_reader``: the reader that was actually used
    - ``output_file_path``: generated NeXus HDF5 path containing exported datasets
    - ``datasets``: serialized dataset payloads when inline output is requested

    Parameters
    ----------
    file_path : str
        Source file to read.
    return_mode : str, optional
        One of ``"file"``, ``"data"``, or ``"both"``.
    """
    if return_mode not in {"file", "data", "both"}:
        raise ValueError("return_mode must be one of: 'file', 'data', 'both'")

    reader_cls, matched_readers = _select_reader(file_path)
    extracted = reader_cls(file_path).read()
    dataset_items = _flatten_dataset_items(extracted)

    payload = {
        "file_path": file_path,
        "return_mode": return_mode,
        "available_readers": available_readers(),
        "matched_readers": matched_readers,
        "selected_reader": _reader_summary(reader_cls),
        "dataset_count": len(dataset_items),
    }

    if return_mode in {"data", "both"}:
        payload["datasets"] = {
            name: _dataset_payload(dataset)
            for name, dataset in dataset_items
        }

    if return_mode in {"file", "both"}:
        payload["output_file_path"] = _write_datasets_to_nexus(file_path, dataset_items)

    return payload


def list_readers() -> list[Dict[str, Any]]:
    """Return the package's reader registry for discovery and routing."""
    return available_readers()


def create_mcp_server(server_name: str = "scifireaders") -> Any:
    """Create the MCP server exposing the discovery and file-reading tools."""
    if FastMCP is None:  # pragma: no cover - optional runtime dependency
        raise ImportError("The 'mcp' package is required to create the SciFiReaders MCP server.")

    server = FastMCP(server_name)

    @server.tool(
        name="list_readers",
        title="SciFiReaders reader list",
        description="List the SciFiReaders reader classes currently available in this environment.",
    )
    def list_readers_tool() -> list[Dict[str, Any]]:
        return list_readers()

    @server.tool(
        name="read_file",
        title="SciFiReaders file reader",
        description="Read a scientific file with the best available SciFiReaders reader.",
    )
    def read_file_tool(file_path: str, return_mode: str = "file") -> Dict[str, Any]:
        """Read a file with the automatically selected SciFiReaders reader."""
        return read_file(file_path, return_mode=return_mode)

    @server.tool(
        name="read_scifireaders_file",
        title="SciFiReaders file reader",
        description="Read a scientific file with the best available SciFiReaders reader.",
    )
    def read_scifireaders_file_tool(file_path: str, return_mode: str = "file") -> Dict[str, Any]:
        """Read a file with the automatically selected SciFiReaders reader."""
        return read_file(file_path, return_mode=return_mode)

    return server


if FastMCP is not None:  # pragma: no cover - optional runtime dependency
    mcp = create_mcp_server()
else:  # pragma: no cover - optional runtime dependency
    mcp = None


def main() -> None:
    """Run the MCP server over stdio."""
    if mcp is None:  # pragma: no cover - optional runtime dependency
        raise ImportError("Install the 'mcp' package or the optional 'SciFiReaders[mcp]' extra to run this server.")
    try:
        mcp.run(transport="stdio")
    except TypeError:  # pragma: no cover - compatibility with older MCP releases
        mcp.run()


__all__ = [
    "AVAILABLE_READERS",
    "available_readers",
    "create_mcp_server",
    "list_readers",
    "main",
    "read_file",
]


AVAILABLE_READERS = available_readers()
