import numpy as np
import sidpy as sid
import xml.etree.ElementTree as ET
from aicspylibczi import CziFile
from sidpy.sid import Reader
import os
import traceback

class CZIReader(Reader):
    def __init__(self, file_path, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)

    def read(self):
        """
        Main execution loop for reading CZI and converting to sidpy Datasets.
        """
        if not os.path.exists(self._input_file_path):
            raise FileNotFoundError(f"No file found at {self._input_file_path}")

        czi = CziFile(self._input_file_path)
        
        # Get shape information (handles the tuples Zeiss returns)
        dims_dict = czi.get_dims_shape()[0] 
        
        #Extract Metadata
        xml_root = czi.meta 
        processed_meta = self._parse_czi_metadata(xml_root)
        
        datasets = []
        
        # Extract Scene count
        raw_s = dims_dict.get('S', 1)
        num_scenes = raw_s[0] if isinstance(raw_s, tuple) else raw_s
        
        # Extract Channel count 
        raw_c = dims_dict.get('C', 0)
        num_channels = raw_c[0] if isinstance(raw_c, tuple) else raw_c
        actual_channels = max(1, num_channels)

        print(f"DEBUG: Dimensions found: {dims_dict}")

        for s_idx in range(num_scenes):
            for c_idx in range(actual_channels):
                # 3. Read image data
                try:
                    if num_channels > 0:
                        data, _ = czi.read_image(S=s_idx, C=c_idx)
                    else:
                        data, _ = czi.read_image(S=s_idx)
                except:
                    continue
                
                if data is None or data.size == 0: continue
                data = np.squeeze(data) 

                # 4. Initialize sidpy.Dataset
                chan_list = processed_meta.get('channel_names', [])
                base_name = chan_list[c_idx] if c_idx < len(chan_list) else f"Channel_{c_idx}"
                chan_name = f"Scene{s_idx}_{base_name}" if num_scenes > 1 else base_name

                # Clean name for HDF5 compatibility (no special chars)
                chan_name = chan_name.replace(" ", "_").replace(".", "_")

                dataset = sid.Dataset.from_array(data, name=chan_name)
                
                # 5. Attach Metadata for HDF5 attributes
                dataset.original_metadata = processed_meta 
                dataset.metadata = {
                    'instrument': processed_meta.get('instrument', 'Unknown'),
                    'objective': processed_meta.get('objective', 'Unknown')
                }
                
                dataset.data_type = 'image_stack' if data.ndim > 2 else 'image'
                dataset.units = 'a.u.'
                dataset.quantity = 'Intensity'

                # 6. Set the physical dimension scales
                self._set_dimensions(dataset, dims_dict, processed_meta)
                
                datasets.append(dataset)
            
        return datasets

    def _parse_czi_metadata(self, root):
        """Parses XML root to extract scientific parameters."""
        metadata = {}
        for dist in root.findall(".//Distance"):
            axis_id = dist.get('Id') 
            v, u = dist.find('Value'), dist.find('DefaultUnitFormat')
            if v is not None and u is not None:
                metadata[f'pixel_size_{axis_id.lower()}'] = float(v.text)
                metadata[f'units_{axis_id.lower()}'] = u.text
        m = root.find(".//Microscope/Name")
        if m is not None: metadata['instrument'] = m.text
        o = root.find(".//Lens/Name")
        if o is not None: metadata['objective'] = o.text
        metadata['channel_names'] = [chan.get('Name') for chan in root.findall(".//Channel") if chan.get('Name')]
        return metadata

    def _set_dimensions(self, dataset, dims_dict, meta):
        """Creates physical Dimension scales."""
        if dataset.ndim == 3:
            labels = ['channel_axis', 'y_axis', 'x_axis'] if dataset.shape[0] < 10 else ['z_axis', 'y_axis', 'x_axis']
        else:
            labels = ['y_axis', 'x_axis']

        for i, axis_name in enumerate(labels):
            size = dataset.shape[i]
            meta_key = axis_name.split('_')[0]
            
            if meta_key == 'channel':
                values, unit, quant, d_type = np.arange(size), 'index', 'index', 'channel'
            else:
                res = meta.get(f'pixel_size_{meta_key}', 1.0)
                unit = meta.get(f'units_{meta_key}', 'm')
                values, quant, d_type = np.linspace(0, size * res, size), 'distance', 'spatial'
            
            dim_obj = sid.Dimension(values, name=axis_name, units=unit, quantity=quant, dimension_type=d_type)
            dataset.set_dimension(i, dim_obj)