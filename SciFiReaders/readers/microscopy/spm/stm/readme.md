# STM Readers

This directory contains readers for Nanonis scanning tunneling microscopy (STM) data:

| Reader | File | Content | Output per dataset |
|---|---|---|---|
| `Nanonis3dsReader` | `.3ds` | grid spectroscopy | `(ny, nx, points)` spectral image, plus a `(ny, nx)` topography image |
| `NanonisSXMReader` | `.sxm` | scan images | `(ny, nx)` image per channel and scan direction |
| `NanonisDatReader` | `.dat` | point spectroscopy | `(points,)` spectrum per column |

Each reader returns a **dict of `sidpy.Dataset`**, one dataset per channel (and direction / sweep).

### One reader for all file types
`sr.AutoReader` selects the reader from the file extension (`.3ds` → `Nanonis3dsReader`, `.sxm` →
`NanonisSXMReader`, `.dat` → `NanonisDatReader`, and the other formats SciFiReaders supports) and returns exactly
what that reader returns.

```python
import SciFiReaders as sr

datasets = sr.AutoReader("grid.3ds").read()      # or "scan.sxm", "spectrum.dat"
print(list(datasets))              # ['Current', 'Current [bwd]', 'LI Demod 1 X', ..., 'Topography']
current = datasets['Current']
print(current.shape, current.units, current.quantity)
print(current.original_metadata['sweep_ramp'])
```

The selected reader is available as `sr.AutoReader(path).reader_cls`. Errors from the reader (e.g. a file that is not
a Nanonis file) are raised as they are; an unsupported extension raises a `TypeError`.

### Specific readers
```python
import SciFiReaders as sr

grid = sr.Nanonis3dsReader("grid.3ds").read()
scan = sr.NanonisSXMReader("scan.sxm").read()
spec = sr.NanonisDatReader("spectrum.dat").read()
```

---

## Conventions shared by all three readers

### Dataset keys and titles
- Spectroscopy (`.3ds`, `.dat`): the key is the channel name **as written by Nanonis, without the unit**:
  `Current (A)` → `Current`, `Current [bwd] (A)` → `Current [bwd]`, `Current [00001] [bwd] (A)` → `Current [00001] [bwd]`.
- Images (`.sxm`): the key is `'<channel> forward'` / `'<channel> backward'`, e.g. `Z forward`.
- `dataset.title` equals the key.
- If two channels would get the same key, the first keeps it and later ones get `_1`, `_2`, … (a `UserWarning`
  is issued for each rename; `original_metadata['Channel']` still shows the original name).

### Per-channel metadata
Every dataset carries its channel description at the top of `original_metadata`, followed by the file header:

| Key | Meaning |
|---|---|
| `Name` | channel name without unit and without `[bwd]` (e.g. `Current`, `Current [AVG]`); also `dataset.quantity` |
| `Unit` | unit from the file (e.g. `A`, `V`, `m`); also `dataset.units` |
| `Channel` | `.3ds` / `.dat`: the full channel string from the file (`Current [bwd] (A)`); `.sxm`: the Nanonis signal index from the header table (`'14'`) |
| `Direction` | `forward` / `backward` – see below |
| `sweep_ramp` | `.3ds` / `.dat` only: `increasing`, `decreasing` or `mixed` – see below |

### Direction
- **Spectroscopy (`.3ds`, `.dat`)**: *sweep* direction. Nanonis tags the return sweep with `[bwd]`; untagged channels
  are the first (forward) sweep, whichever way the bias goes.
- **Images (`.sxm`)**: *scan* direction of the fast axis (trace / retrace).

### Sweep ramp (`.3ds`, `.dat`)
Forward and `[bwd]` data are both stored against the **same** sweep axis (Sweep Start → Sweep End), so the array order
does not tell in which direction the bias actually ramped. `sweep_ramp` records it:
- `increasing` / `decreasing`: direction of the sweep in time for that channel (forward: Sweep Start → Sweep End,
  `[bwd]`: the reverse);
- `mixed`: the sweep changes direction (e.g. a multi-segment 0 → 1 → 0 V sweep).

This works for any swept signal (bias, Z, …).

### Spatial axes (`.3ds`, `.sxm`)
- Arrays are `(rows, columns) = (ny, nx)`: **axis 0 is `Y`, axis 1 is `X`**.
- Row 0 is the **bottom** and column 0 the **left** of the frame.
- Axis values are in **nm**, starting at 0, with pitch = frame size / pixels. They are positions within the frame; the
  frame centre / offset and rotation angle are in the metadata (`pos_xy` + `angle` for `.3ds`, `scan_offset` +
  `scan_angle` for `.sxm`, in m and degrees).
- **Angle convention (Nanonis): a positive angle means the frame is rotated clockwise.** To map frame positions to
  lab coordinates, rotate them by `-angle` (counter-clockwise positive) about the frame centre.

### Data
- Values are native `float32` (`.3ds`, `.sxm`) or `float64` (`.dat`).
- Unmeasured pixels are `NaN`, never zeros: Nanonis writes a stopped scan at full size with `NaN` for the pixels it
  did not reach, and files that are shorter than their header says are padded with `NaN`.

---

## `.3ds` – grid spectroscopy (`Nanonis3dsReader`)

### Outputs
| Key | Shape | Type | Content |
|---|---|---|---|
| one per channel, e.g. `Current`, `LI Demod 1 X`, `Current [bwd]` | `(ny, nx, points)` | `SPECTRAL_IMAGE` | spectra at every pixel |
| `Topography` | `(ny, nx)` | `IMAGE` | `Z (m)` recorded at every pixel (only if the grid recorded `Z (m)`) |

Dimensions: `Y` (nm), `X` (nm), and the sweep signal (e.g. `Bias` in V).

### Sweep axis
- `Filetype=Linear`: `linspace(Sweep Start, Sweep End, Points)`.
- `Filetype=MLS` (multi-segment): built piecewise from the header's segment table, so non-uniform steps are exact.
  The segment table stays in `original_metadata` under its header key (`Segment Start (V), Segment End (V), …`).

### Metadata
- Frame: `dim_px` (nx, ny), `pos_xy` (centre, m), `size_xy` (m), `angle` (deg).
- Experiment: `sweep_signal`, `experiment_name`, `measure_delay` (s), `start_time`, `end_time`, `user`, `comment`,
  `Filetype`, and every other header entry by its Nanonis name. Entries missing from the file are `nan` / `''`.
- Per-pixel parameters under their Nanonis names (`Sweep Start`, `X (m)`, `Y (m)`, `Z (m)`, `Settling time (s)`,
  `Scan:…`, …): a **scalar** if constant over the grid, otherwise the full **`(ny, nx)` grid**, aligned with the
  data (`meta['X (m)'][i, j]` is the true position of pixel `[i, j]`).

### Examples
```python
import numpy as np
import matplotlib.pyplot as plt

ds = sr.Nanonis3dsReader("grid.3ds").read()
didv = ds['LI Demod 1 X']
bias = np.asarray(didv._axes[2])                      # sweep axis (exact, also for MLS)

# map at the bias closest to 0.1 V
k = np.argmin(np.abs(bias - 0.1))
x, y = np.asarray(didv._axes[1]), np.asarray(didv._axes[0])
plt.imshow(np.asarray(didv)[:, :, k], origin='lower', extent=[x[0], x[-1], y[0], y[-1]])

# average spectrum and true pixel positions
avg = np.nanmean(np.asarray(didv), axis=(0, 1))
meta = didv.original_metadata
X, Y = meta['X (m)'], meta['Y (m)']                   # (ny, nx) grids in m (scalars if constant)

# forward vs. return sweep
fwd, bwd = ds['Current'], ds.get('Current [bwd]')
print(fwd.original_metadata['sweep_ramp'], bwd.original_metadata['sweep_ramp'] if bwd is not None else None)

# topography
topo = ds['Topography']                               # (ny, nx), m
```

---

## `.sxm` – scan images (`NanonisSXMReader`)

### Outputs
One `IMAGE` dataset `(ny, nx)` per channel and recorded direction: `Z forward`, `Z backward`, `Current forward`, …
Channels recorded in only one direction give only that dataset. Non-square scans are supported.

### Orientation – plot with `origin='lower'`
Images are flipped at read time so that every image, whatever the scan direction, has **row 0 at the bottom and
column 0 at the left** of the Nanonis scan frame:
- `scan_dir == 'down'`: flipped vertically;
- backward (retrace) images: flipped horizontally.

Forward and backward images therefore overlay pixel by pixel, and the result matches the Nanonis display when plotted
with `origin='lower'`:

```python
import numpy as np
import matplotlib.pyplot as plt

ds = sr.NanonisSXMReader("scan.sxm").read()
z = ds['Z forward']
x, y = np.asarray(z._axes[1]), np.asarray(z._axes[0])            # nm
plt.imshow(np.asarray(z), origin='lower', cmap='gray',
           extent=[x[0], x[-1] + (x[1] - x[0]), y[0], y[-1] + (y[1] - y[0])])
plt.xlabel('X (nm)'); plt.ylabel('Y (nm)')
```

With the default `origin='upper'` the image appears upside down.

### Partial scans
A scan stopped before the end keeps its full size; the lines not reached are `NaN`. With the orientation above, an
`up` scan fills from row 0 upwards, a `down` scan from the top row downwards. A line stopped during the retrace is
`NaN` on its left part in the backward image (the retrace runs right to left).

### Metadata
- Channel: `Channel` (Nanonis signal index), `Name`, `Unit`, `Direction`, `Calibration`, `Offset` (numbers).
- Scan: `scan_pixels` (nx, ny), `scan_range` (m), `scan_offset` (m), `scan_angle` (deg, number), `scan_dir`
  (`up` / `down`, slow axis), `scan_time`, `acq_time`, `bias`, `rec_date`, `rec_time`, `comment`, `z-controller`
  (table), and all other header entries in lower case (e.g. `scan>speed forw. (m/s)`).

---

## `.dat` – point spectroscopy (`NanonisDatReader`)

### Outputs
One `SPECTRUM` dataset `(points,)` per data column. Column 0 (the swept signal, e.g. `Bias calc (V)` or `Z rel (m)`)
is the spectral dimension of every dataset, named and unit'ed after that column. Because `.dat` files store the
actual sweep values, the axis is exact for linear and multi-segment (MLS) sweeps alike.

### Multiple sweeps, averages, filtered data
Nanonis tags extra columns, and every column becomes its own dataset:

| Column in file | Key | `Name` / `quantity` | `Direction` |
|---|---|---|---|
| `Current (A)` | `Current` | `Current` | forward |
| `Current [bwd] (A)` | `Current [bwd]` | `Current` | backward |
| `Current [00003] (A)` | `Current [00003]` | `Current [00003]` | forward |
| `Current [AVG] [bwd] (A)` | `Current [AVG] [bwd]` | `Current [AVG]` | backward |
| `Current (A) [filt]` | `Current [filt]` | `Current [filt]` | forward |

So a file with channels Current, LIX and LIY, 5 sweeps and backward sweep on returns 3 × (5 + average) × 2 = 36
datasets. Group them by key:

```python
ds = sr.NanonisDatReader("spectrum.dat").read()
bias = np.asarray(ds['Current [AVG]']._axes[0])
sweeps_fwd = [k for k in ds if k.startswith('Current [0') and ds[k].original_metadata['Direction'] == 'forward']
stack = np.stack([np.asarray(ds[k]) for k in sweeps_fwd])        # (n_sweeps, points)
```

### Metadata
- Per channel: `Name`, `Unit`, `Channel`, `Direction`, `sweep_ramp`.
- Header: every line before `[DATA]` under its Nanonis name (`Experiment`, `Date`, `X (m)`, `Z (m)`,
  `Settling time (s)`, `Filter type`, MLS segment table, …). A single value is a number where possible, otherwise a
  string; several values are a list; an empty value is `''`. Each dataset has its own copy of the header.

Files that are not Nanonis `.dat` files (no `[DATA]` section) raise a `ValueError`.

---

## Testing status

Unit tests (`tests/readers/microscopy/spm/stm/test_nanonis.py`) cover one example file per reader: a `.dat` with
`[bwd]` and filtered columns, a two-direction `.sxm` (scan `up`) and a linear `.3ds` grid, and that `sr.AutoReader`
selects the right reader for each. The datasets are taken from `<repo>/data/` and downloaded there if missing.

Additional behaviour has been checked against real instrument files: backward sweeps, multi-sweep and MLS `.dat`
files, MLS and `[bwd]` `.3ds` grids, `up` / `down` and partial `.sxm` scans.

Not yet verified with real files:
- **`.sxm` channels recorded in one direction only** (e.g. forward-only): supported and tested on files built from a
  two-direction scan, assuming such a channel is stored as a single data block, but not confirmed with an instrument file.

`AscReader` (`omicron_asc.py`, Omicron `.asc` files) in this directory has **no unit test**.


## Notes

Modified and tested: Ganesh Narasimha, 30 Sept 2026