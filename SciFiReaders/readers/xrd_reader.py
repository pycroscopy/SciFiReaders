import numpy as np
import xml.etree.ElementTree as ET
import sidpy as sid
from sidpy.sid import Reader
import sys

if sys.version_info.major == 3:
    unicode = str

class XRDMLReader(Reader):
    """
    Extracts data and metadata from PANalytical X-ray Diffraction/Reflectivity (.xrdml) files
    into standardized sidpy.Dataset objects.
    """
    def __init__(self, file_path, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)

    def read(self, verbose=False, parm_encoding='utf-8'):
        """
        Reads the .xrdml file given in file_path into a list of sidpy.Dataset objects.

        Parameters
        ----------
        verbose : Boolean (Optional)
            Whether or not to show print statements for debugging
        parm_encoding : str
            Encoding for metadata strings

        Returns
        -------
        datasets : list of sidpy.Dataset objects
            The parsed 1D diffraction, XRR, or rocking curve datasets.
        """
        file_path = self._input_file_path

        # Step 1: Reader Detection & Match
        if not isinstance(file_path, (str, unicode)):
            raise TypeError('file_path should be a string!')
        if not file_path.endswith('.xrdml'):
            raise ValueError('file_path must have a .xrdml extension!')

        # Parse XML tree
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except Exception as e:
            raise IOError(f"Failed to parse XML in .xrdml file: {e}")

        # Strip XML namespaces for simplified tag lookup
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]

        # Step 2: Metadata & Header Parse
        metadata = self._extract_metadata(root)

        # Step 3: Numerical Data Extraction
        intensities, axis_vals, axis_name, axis_unit = self._extract_data_and_axes(root)

        # Step 4: sidpy.Dataset Assembly
        title = metadata.get('scanType', 'XRD Scan')
        data_set = sid.Dataset.from_array(intensities, title=title)
        data_set.data_type = 'line_plot'

        # Set quantity and units for intensity
        data_set.quantity = 'Intensity'
        data_set.units = 'Counts'

        # Set dimension info (e.g., 2Theta, Omega, or Distance)
        data_set.set_dimension(0, sid.Dimension(
            axis_vals,
            name=axis_name,
            units=axis_unit,
            quantity=axis_name,
            dimension_type='spectral'
        ))

        # Attach original metadata dictionary
        data_set.original_metadata = metadata

        if verbose:
            print(f"Successfully loaded {file_path} with {len(intensities)} data points.")

        # Step 5: Integration Ready (Returns list of sidpy.Dataset)
        return [data_set]

    #def _extract_metadata(self, root):
    #    """Extracts general instrument metadata, X-ray tube info, and scan parameters."""
    #    metadata = {}
    #    
    #    # Extract measurement info
    #    meas_info = root.find('.//measurement')
    #    if meas_info is not None:
    #        metadata.update(meas_info.attrib)
    #
    #    # Extract X-ray tube wavelength information if available
    #    tubes = root.findall('.//usedWavelength')
    #    for tube in tubes:
    #        for child in tube:
    #            metadata[child.tag] = child.text
    #
    #    # Extract scan axis information
    #    scan_axes = []
    #    for axis in root.findall('.//axis'):
    #        axis_attr = axis.attrib.get('name', 'unknown')
    #        scan_axes.append(axis_attr)
    #    metadata['scanAxes'] = scan_axes
    #
    #    return metadata
    def _extract_metadata(self, root):
        """Extracts comprehensive instrument metadata, beam paths, and scan headers from .xrdml."""
        metadata = {}
        
        # Helper to recursively grab attributes and text from XML branches
        def parse_element(element, prefix=""):
            data = {}
            if element.attrib:
                for k, v in element.attrib.items():
                    data[f"{prefix}_{k}" if prefix else k] = v
            if element.text and element.text.strip():
                data[f"{prefix}_text" if prefix else "text"] = element.text.strip()
            for child in element:
                child_data = parse_element(child, child.tag)
                data.update(child_data)
            return data

        # 1. Global comments & configuration notes
        comments = [entry.text for entry in root.findall('.//comment/entry') if entry.text]
        if comments:
            metadata['comments'] = comments

        # 2. X-ray wavelength specifications
        wavelength_elem = root.find('.//usedWavelength')
        if wavelength_elem is not None:
            metadata['usedWavelength'] = parse_element(wavelength_elem)

        # 3. Incident Beam Path (Tube, Mirror, Monochromator, Slits, Attenuator)
        incident_elem = root.find('.//incidentBeamPath')
        if incident_elem is not None:
            metadata['incidentBeamPath'] = parse_element(incident_elem)

        # 4. Diffracted Beam Path (Soller slits, Collimator, Detector)
        diffracted_elem = root.find('.//diffractedBeamPath')
        if diffracted_elem is not None:
            metadata['diffractedBeamPath'] = parse_element(diffracted_elem)

        # 5. Scan Header (Timestamps, Software version, Author)
        header_elem = root.find('.//scan/header')
        if header_elem is not None:
            metadata['scanHeader'] = parse_element(header_elem)

        # 6. Scan Configuration Attributes (scan axis, mode, status)
        scan_elem = root.find('.//scan')
        if scan_elem is not None:
            metadata['scanConfig'] = scan_elem.attrib

        # 7. Sample Offsets (Omega, Chi, etc.)
        offsets = {}
        for pos in root.findall('.//sampleOffset/position'):
            axis = pos.attrib.get('axis')
            unit = pos.attrib.get('unit', '')
            if axis and pos.text:
                offsets[axis] = f"{pos.text} {unit}"
        if offsets:
            metadata['sampleOffsets'] = offsets

        return metadata

    def _extract_data_and_axes(self, root):
        """Extracts the intensity array and corresponding primary scan axis values and units."""
        # Extract intensities
        intensities_elem = root.find('.//intensities')
        if intensities_elem is not None and intensities_elem.text:
            intensities = np.array([float(val) for val in intensities_elem.text.split()])
        else:
            raise ValueError("No intensity data found in .xrdml file.")

        # Extract primary scan axis (e.g., 2Theta, Omega, etc.)
        axis_name = '2Theta'
        axis_unit = 'degrees'
        
        # Look for axis configuration
        positions = root.findall('.//positions')
        start_pos, end_pos = None, None

        for pos in positions:
            axis_elem = pos.find('axis')
            if axis_elem is not None:
                axis_name = axis_elem.text
            unit_elem = pos.find('unit')
            if unit_elem is not None:
                axis_unit = unit_elem.text
            start_elem = pos.find('startPosition')
            if start_elem is not None:
                start_pos = float(start_elem.text)
            end_elem = pos.find('endPosition')
            if end_elem is not None:
                end_pos = float(end_elem.text)

        # Generate axis coordinate array
        if start_pos is not None and end_pos is not None:
            axis_vals = np.linspace(start_pos, end_pos, len(intensities))
        else:
            # Fallback if start/end positions aren't explicit attributes
            axis_vals = np.arange(len(intensities), dtype=float)

        return intensities, axis_vals, axis_name, axis_unit