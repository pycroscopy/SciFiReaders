

from modulefinder import Module
import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader
from os import path
import sys

if sys.version_info.major == 3:
    unicode = str

try:
    import gwyfile
except ModuleNotFoundError:
    gwyfile = None

class GwyddionReader(Reader):
    """
    Extracts data and metadata from Igor Binary Wave (.ibw) files containing
    images or force curves
    """
    def __init__(self, file_path, *args, **kwargs):
        if gwyfile == None:
            raise ModuleNotFoundError('You attempted to load a Gwyddion file, but this requires gwyfile.\n \
    Please Load it with pip install gwyfile , restart and retry')
        super().__init__(file_path, *args, **kwargs)

    def read(self, verbose=False, parm_encoding='utf-8'):
        """
        Reads the file given in file_path into a sidpy dataset

        Parameters
        ----------
        verbose : Boolean (Optional)
            Whether or not to show  print statements for debugging
     
        Returns
        -------
        sidpy.Dataset : List of sidpy.Dataset objects.
            Multi-channel inputs are separated into individual dataset objects
        """
        file_path = self._input_file_path

        if not isinstance(file_path, (str, unicode)):
            raise TypeError('file_path should be a string!')
        if not (file_path.endswith('.gsf') or file_path.endswith('.gwy')):
            # TODO: Gwyddion is weird, it doesn't append the file extension some times.
            # In theory, you could identify the kind of file by looking at the header (line 38 in gsf_read()).
            # Ideally the header check should be used instead of the extension check
            raise ValueError('file_path must have a .gsf or .gwy extension!')
        
        if file_path.endswith('.gsf'):
            datasets = self.gsf_read()
        elif file_path.endswith('.gwy'):
            datasets = self.gwy_read()
        
        # Return the dataset
        return datasets

    def gsf_read(self):
        """
        Read a Gwyddion Simple Field 1.0 file format
        http://gwyddion.net/documentation/user-guide-en/gsf.html
        
        Parameters
        ----------
        file_name : string
            path to the file
        Returns
        -------
        metadata : dict)
            Additional metadata to be included in the file
        data : numpy.ndarray
            An arbitrarily sized 2D array of arbitrary numeric type
        """
       
        gsf_file = open(self._input_file_path, 'rb')
        
        metadata = {}
        
        # check if header is OK
        if not(gsf_file.readline().decode('UTF-8') == 'Gwyddion Simple Field 1.0\n'):
            gsf_file.close()
            raise ValueError('File has wrong header')
            
        term = b'00'
        # read metadata header
        while term != b'\x00':
            line_string = gsf_file.readline().decode('UTF-8')
            metadata[line_string.rpartition(' = ')[0]] = line_string.rpartition('=')[2]
            term = gsf_file.read(1)
            gsf_file.seek(-1, 1)
        
        gsf_file.read(4 - gsf_file.tell() % 4)
        
        # fix known metadata types from .gsf file specs
        # first the mandatory ones...
        metadata['XRes'] = np.int(metadata['XRes'])
        metadata['YRes'] = np.int(metadata['YRes'])
        
        # now check for the optional ones
        if 'XReal' in metadata:
            metadata['XReal'] = np.float(metadata['XReal'])
        
        if 'YReal' in metadata:
            metadata['YReal'] = np.float(metadata['YReal'])
                    
        if 'XOffset' in metadata:
            metadata['XOffset'] = np.float(metadata['XOffset'])
        
        if 'YOffset' in metadata:
            metadata['YOffset'] = np.float(metadata['YOffset'])
        
        datasets = []

        data = np.frombuffer(gsf_file.read(), dtype='float32').reshape(metadata['YRes'], metadata['XRes'])
        
        gsf_file.close()
        num_cols, num_rows = data.shape
        data_set = sid.Dataset.from_array(data, title=metadata['Title'])
        data_set.data_type = 'Image'

        #Add quantity and units
        data_set.units = metadata['ZUnits']
        data_set.quantity = metadata['Title']
       
        #Add dimension info
        data_set.set_dimension(0, sid.Dimension(np.linspace(0, metadata['XReal'], num_cols),
                                                name = 'x',
                                                units=metadata['XYUnits'], quantity = 'x',
                                                dimension_type='spatial'))
        data_set.set_dimension(1, sid.Dimension(np.linspace(0, metadata['YReal'], num_rows),
                                                name = 'y',
                                                units=metadata['XYUnits'], quantity = 'y',
                                                dimension_type='spatial'))

        # append metadata
        data_set.original_metadata = metadata
        data_set.data_type = 'image'

        #Finally, append it
        datasets.append(data_set)
        
        return datasets


    def gwy_read(self):
        """
        Parameters
        ----------
        file_path
        meas_grp
        For more information on the .gwy file format visit the link below -
        http://gwyddion.net/documentation/user-guide-en/gwyfile-format.html
        """

        # Need to build a set of channels to test against and a function-level variable to write to
        channels = []

        # Read the data in from the specified file
        gwy_data = gwyfile.load(self._input_file_path)

        for obj in gwy_data:
            gwy_key = obj.split('/')
            try:
                # if the second index of the gwy_key can be cast into an int then
                # it needs to be processed either as an image or a graph
                
                int(gwy_key[1])
                
                if gwy_key[2] == 'graph':
                    # graph processing
                   
                    channels = self._translate_graph(gwy_data,
                                                        obj)
                elif obj.endswith('data'):
                   
                    channels.append(self._translate_image_stack( gwy_data,
                                                            obj))
                else:
                    continue
            except ValueError:
                # if the second index of the gwy_key cannot be cast into an int
                # then it needs to be processed wither as a spectra, volume or xyz
                
                if gwy_key[1] == 'sps':
                
                    channels = self._translate_spectra(gwy_data,
                                                        obj)
                elif gwy_key[1] == 'brick':
                 
                    channels = self._translate_volume(gwy_data,
                                                        obj)
                elif gwy_key[1] == 'xyz':
                 
                    channels = self._translate_xyz(gwy_data,
                                                    obj)
        return channels


    def _translate_image_stack(self, gwy_data, obj):
        """
        Use this function to write data corresponding to a stack of scan images (most common)
        Returns
        -------
        """        

        if obj.endswith('data'):
            data = gwy_data[obj].data
            title = gwy_data[obj+'/title']
            keys = gwy_data[obj].keys()
            meta_data = {}
            for key in keys:
                if 'data' not in key:
                    meta_data[key] = gwy_data[obj][key] 

            x_range = gwy_data[obj].get('xreal')
            x_vals = np.linspace(0, x_range, gwy_data[obj]['xres'])
          
            y_range = gwy_data[obj].get('yreal')
            y_vals = np.linspace(0, y_range, gwy_data[obj]['yres'])

            data_set = sid.Dataset.from_array(data, title=title)
            data_set.data_type = 'Image'

            #Add quantity and units
            data_set.units = gwy_data[obj]['si_unit_z']['unitstr']
            data_set.quantity = title 
        
            #Add dimension info
            data_set.set_dimension(0, sid.Dimension(x_vals,
                                                    name = 'x',
                                                    units=gwy_data[obj]['si_unit_xy']['unitstr'], quantity = 'x',
                                                    dimension_type='spatial'))
            data_set.set_dimension(1, sid.Dimension(y_vals,
                                                    name = 'y',
                                                    units=gwy_data[obj]['si_unit_xy']['unitstr'], quantity = 'y',
                                                    dimension_type='spatial'))

            # append metadata
            data_set.original_metadata = meta_data
            data_set.data_type = 'image'

        return data_set


    def _translate_spectra(self, gwy_data, obj):
        """
        Use this to translate simple 1D data like force curves
        Returns
        -------
        """
        keys = gwy_data[obj].keys()
        meta_data = {}
        for key in keys:
            if 'data' not in key:
                meta_data[key] = gwy_data[obj][key] 

        title = obj['title']
        unitstr = obj['unitstr']
        coords = obj['coords']
        res = obj['data']['res']
        real = obj['data']['real']
        offset = obj['data']['off']
        x_units = obj['data']['si_unit_x']['unitstr']
        y_units = obj['data']['si_unit_y']['unitstr']
        data = obj['data']['data']
        indices = obj['selected']
        x_vals = np.linspace(offset, real, res)

        data_set = sid.Dataset.from_array(data, title=title)
        data_set.data_type = 'line_plot'

        #Add quantity and units
        data_set.units = y_units
        data_set.quantity = title 
    
        #Add dimension info
        data_set.set_dimension(0, sid.Dimension(x_vals,
                                                name = 'x',
                                                units = x_units, quantity = 'x',
                                                dimension_type='spectral'))

        # append metadata
        data_set.original_metadata = meta_data

        return data_set


    #TODO: This stuff is not yet supported. Need to work on it...

    def _translate_graph(self,  gwy_data, obj):
        """
        Use this to translate graphs
        Returns
        """
        return 


    def _translate_volume(self, gwy_data, obj):
        return 


    def _translate_xyz(self, gwy_data, obj):
        return 