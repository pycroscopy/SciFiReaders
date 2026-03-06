
"""
################################################################################
# Python class for reading Bruker .rto files into sidpy Dataset
# and extracting all metadata
#
# Written by Gerd Duscher, UTK 2025
#
# Works for python 3
#
################################################################################
"""
import os
import codecs
import xml

import numpy as np
import sidpy

__version__ = '0.1beta'
__all__ = ["BrukerReader", "__version__"]


def get_bruker_dictionary(filename):
    """ Convert xm, style .rto file to python dictionary

    The problem is that there are xml sections with same name (spectrum, image) that need to be numbered
    """
    tree = xml.etree.ElementTree.parse(filename)
    root = tree.getroot()
    spectrum_number = 0
    i = 0
    image_count = 0
    overlay_count = 0
    tags = {}
    for neighbor in root.iter():
        if 'Type' in neighbor.attrib:
            if 'TRTCrossOverlayElement' in neighbor.attrib['Type']:
                if 'Spectrum' in neighbor.attrib['Name']:
                    overlay_count += 1
                    if 'overlay' not in tags:
                        tags['overlay'] = {}
                    if 'image' + str(image_count) not in tags['overlay']:
                        tags['overlay']['image' + str(image_count)] = {}
                    tags['overlay']['image' + str(image_count)][neighbor.attrib['Name']] = {}

                    over = tags['overlay']['image' + str(image_count)][neighbor.attrib['Name']]

                    for child in neighbor.iter():
                        if 'verlay' in child.tag:
                            pos = child.find('./Pos')
                            if pos is not None:
                                over['pos_x'] = int(pos.find('./PosX').text)
                                over['pos_y'] = int(pos.find('./PosY').text)
                                over['position'] = [over['pos_x'], over['pos_y']]
                                over['type'] = 'spot'
                                over['label'] = neighbor.attrib['Name']
            if 'TRTImageData' in neighbor.attrib['Type']:
                _ = neighbor.find("./ClassInstance[@Type='TRTCrossOverlayElement']")
                image = neighbor
                if 'image' not in tags:
                    tags['image'] = {}
                tags['image'][image_count] = {}
                im = tags['image'][image_count]
                im['width'] = int(image.find('./Width').text)  # in pixels
                im['height'] = int(image.find('./Height').text)  # in pixels
                im['dtype'] = 'u' + image.find('./ItemSize').text  # in bytes ('u1','u2','u4')
                im['scale_x'] = float(image.find('./XCalibration').text)
                im['scale_y'] = float(image.find('./YCalibration').text)
                im['plane_count'] = int(image.find('./PlaneCount').text)
                im['date'] = str((image.find('./Date').text))
                im['time'] = str((image.find('./Time').text))
                im['data'] = {}
                for j in range(im['plane_count']):
                    img = image.find("./Plane" + str(i))
                    raw = codecs.decode((img.find('./Data').text).encode('ascii'), 'base64')
                    array1 = np.frombuffer(raw, dtype=im['dtype'])
                    im['data'][str(j)] = np.reshape(array1, (im['height'], im['width']))
                image_count += 1
            if 'TRTDetectorHeader' == neighbor.attrib['Type']:
                detector = neighbor
                tags['detector'] = {}
                for child in detector:
                    if child.tag == "WindowLayers":
                        tags['detector']['layers'] = {}
                        for child2 in child:
                            tags['detector']['layers'][child2.tag] = {}
                            tags['detector']['layers'][child2.tag]['Z'] = child2.attrib["Atom"]
                            tags['detector']['layers'][child2.tag]['thickness'] = float(
                                child2.attrib["Thickness"]) * 1e-6  # now in m
                            if 'RelativeArea' in child2.attrib:
                                tags['detector']['layers'][child2.tag]['relative_area'] = float(
                                    child2.attrib["RelativeArea"])
                    else:
                        if child.tag != 'ResponseFunction':
                            if child.text is not None:
                                tags['detector'][child.tag] = child.text

                                if child.tag == 'SiDeadLayerThickness':
                                    tags['detector'][child.tag] = float(child.text) * 1e-6

                                if child.tag == 'DetectorThickness':
                                    tags['detector'][child.tag] = float(child.text) * 1e-1

            # ESMA could stand for Electron Scanning Microscope Analysis
            if 'TRTESMAHeader' == neighbor.attrib['Type']:
                esma = neighbor
                tags['esma'] = {}
                for child in esma:
                    if child.tag in ['PrimaryEnergy', 'ElevationAngle', 'AzimutAngle', 'Magnification',
                                     'WorkingDistance']:
                        tags['esma'][child.tag] = float(child.text)
            if 'TRTSpectrum' == neighbor.attrib['Type']:
                if 'spectrum' not in tags:
                    tags['spectrum'] = {}
                if 'Name' in neighbor.attrib:
                    spectrum = neighbor
                    trt_header = spectrum.find('./TRTHeaderedClass')

                    if trt_header is not None:
                        hardware_header = trt_header.find("./ClassInstance[@Type='TRTSpectrumHardwareHeader']")
                        spectrum_header = spectrum.find("./ClassInstance[@Type='TRTSpectrumHeader']")
                        result_header = spectrum.find("./ClassInstance[@Type='TRTResult']")
                        tags['spectrum'][spectrum_number] = {}
                        tags['spectrum'][spectrum_number]['hardware_header'] = {}
                        if hardware_header is not None:
                            for child in hardware_header:
                                tags['spectrum'][spectrum_number]['hardware_header'][child.tag] = child.text
                        tags['spectrum'][spectrum_number]['detector_header'] = {}
                        tags['spectrum'][spectrum_number]['spectrum_header'] = {}
                        for child in spectrum_header:
                            tags['spectrum'][spectrum_number]['spectrum_header'][child.tag] = child.text
                        tags['spectrum'][spectrum_number]['results'] = {}
                        for result in result_header:
                            result_tag = {}
                            for child in result:
                                result_tag[child.tag] = child.text
                            if 'Atom' in result_tag:
                                if result_tag['Atom'] not in tags['spectrum'][spectrum_number]['results']:
                                    tags['spectrum'][spectrum_number]['results'][result_tag['Atom']] = {}
                                tags['spectrum'][spectrum_number]['results'][result_tag['Atom']].update(result_tag)
                        tags['spectrum'][spectrum_number]['data'] = np.fromstring(spectrum.find('./Channels').text, 
                                                                                  dtype=np.int16, sep=",")
                        spectrum_number += 1
    return tags


def get_image(tags, key=0):
    """ Convert image part of dictionary to sidpy dataset"""
    image = tags['image'][key]
    names = ['x', 'y']
    units = 'nm'
    quantity = 'distance'
    dimension_type = 'spatial'
    to_nm = 1e3

    scale_x = float(image['scale_x']) * to_nm
    scale_y = float(image['scale_y']) * to_nm

    dataset = sidpy.Dataset.from_array(image['data']['0'].T)
    dataset.data_type = 'image'
    dataset.units = 'counts'
    dataset.quantity = 'intensity'

    dataset.modality = 'SEM'
    dataset.title = 'image'
    dataset.add_provenance('SciFiReader', 'BrukerReader', version='0', linked_data='File: ')

    dataset.set_dimension(0, sidpy.Dimension(np.arange(image['data']['0'].shape[1]) * scale_x,
                                             name=names[0], units=units,
                                             quantity=quantity,
                                             dimension_type=dimension_type))
    dataset.set_dimension(1, sidpy.Dimension(np.arange(image['data']['0'].shape[0]) * scale_y,
                                             name=names[1], units=units,
                                             quantity=quantity,
                                             dimension_type=dimension_type))

    dataset.metadata['experiment'] = tags.get('esma', {}).copy()
    dataset.metadata['annotations'] = tags.get('overlay', {}).get('image1', {}).copy()
    return dataset


def get_spectrum(tags, key=0):
    """ Convert spectrum part of dictionary to sipdy dataset"""
    spectrum = tags['spectrum'][key]
    offset = float(spectrum['spectrum_header']['CalibAbs'])
    scale = float(spectrum['spectrum_header']['CalibLin'])

    dataset = sidpy.Dataset.from_array(spectrum['data'])
    energy_scale = (np.arange(len(dataset)) * scale + offset) * 1000
    dataset.units = 'counts'
    dataset.quantity = 'intensity'
    dataset.data_type = 'spectrum'

    dataset.modality = 'EDS'
    dataset.title = 'spectrum'
    dataset.set_dimension(0, sidpy.Dimension(energy_scale,
                                             name='energy_scale', units='eV',
                                             quantity='energy',
                                             dimension_type='spectral'))

    dataset.metadata['experiment'] = tags['esma'].copy()
    acceleration_voltage = float(tags.get('experiment', {}).get('PrimaryEnergy', 0))*1000.
    dataset.metadata['experiment']['acceleration_voltage'] =  acceleration_voltage
    dataset.metadata['EDS'] = {'detector': tags.get('detector', '')}
    dataset.metadata['EDS']['results'] = {}
    for  result in spectrum.get('results', {}).values():
        if 'Name' in result:
            dataset.metadata['EDS']['results'][result['Name']] = result.copy()
    return dataset


class BrukerReader(sidpy.Reader):
    """
    Creates an instance of BrukerReader which can read .rto files
    datasets formatted in the Bruker format

    We can read Images, and Spectra.
    Please note that all original metadata are retained in each sidpy dataset.
    ToDo: evaluate if this should this be a point cloud

    Parameters
    ----------
    file_path : str
        Path to a Bruker rto file
    Return
    ------
    datasets: dict
        dictionary of sidpy.Datasets
    """

    def __init__(self, file_path, verbose=False):
        """
        file_path: filepath to rto file.
        """

        super().__init__(file_path)

        # initialize variables ##
        self.verbose = verbose
        self.__filename = file_path

        _, file_name = os.path.split(self.__filename)
        self.basename, self.extension = os.path.splitext(file_name)
        self.datasets = {}
        self.tags = {}
        if 'rto' in self.extension:
            try:
                self.tags = get_bruker_dictionary(file_path)

            except IOError:
                raise IOError(f"File {self.__filename} does not seem to be of Bruker's .rto format")
        self.channel_number = 0

    def can_read(self):
        """ Checks if the reader can read the file format """
        return 'rto' in self.extension

    def read(self):
        """ Parses the dictionary that was extracted from the xml type file of Bruker .rto file
        Reads images and spectra
        """
        if 'image' in self.tags:
            key = f"Channel_{int(self.channel_number):03d}"
            self.datasets[key] = get_image(self.tags, key=0)
            self.channel_number += 1

            self.datasets[key].title = self.basename+'_image'
            self.datasets[key].add_provenance('SciFiReader', 'BrukerReader', version=__version__,
                                              linked_data=f'File: {self.basename}.{self.extension}')
        if 'spectrum' in self.tags:
            for spectrum_key in self.tags['spectrum']:
                key = f"Channel_{int(self.channel_number):03d}"
                self.datasets[key] = get_spectrum(self.tags, key=spectrum_key)
                self.channel_number += 1

                self.datasets[key].title = self.basename + '_spectrum_' + str(spectrum_key)
                self.datasets[key].add_provenance('SciFiReader', 'BrukerReader', version=__version__,
                                                  linked_data=f'File: {self.basename}.{self.extension}')
        return self.datasets

    def get_filename(self):
        """ Returns the filename of the Bruker file"""
        return self.__filename

    def get_datasets(self):
        """ Returns the datasets created by the reader""" 
        return self.datasets

    filename = property(get_filename)
