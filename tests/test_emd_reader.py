"""
Test of EMD Reader of ThermoFisher Velox files
part of SciFiReader, a pycroscopy package

author: Gerd Duscher, UTK
First Version 11/19/2021
"""
import unittest
import numpy as np
import sys
import os
import wget

import sidpy

sys.path.insert(0, "../SciFiReaders/")
import SciFiReaders
from SciFiReaders import EMDReader

data_path = os.path.join(os.path.dirname(__file__), '../data')


class TestEMDReader(unittest.TestCase):

    def test_data_available(self):
        file_name = wget.download(
            'https://raw.githubusercontent.com/pycroscopy/SciFiReaders/master/data/fei_emd_spectrum.emd')
        emd_reader = EMDReader(file_name)

        self.assertIsInstance(emd_reader, sidpy.Reader)
        emd_reader.close()

    def test_read_spectrum(self):
        file_name = 'fei_emd_spectrum.emd'
        emd_reader = EMDReader(file_name)
        datasets = emd_reader.read()
        emd_reader.close()

        self.assertIsInstance(datasets[0], sidpy.Dataset)
        self.assertTrue(datasets[0].ndim == 1)
        self.assertTrue(len(datasets) == 1)
        print(datasets[0].original_metadata)

        self.assertTrue(datasets[0].units == 'counts')
        self.assertTrue(datasets[0].quantity == 'intensity')
        self.assertIsInstance(datasets[0].energy_scale, sidpy.Dimension)
        original_metadata = {'Core': {'MetadataDefinitionVersion': '7.9',
                                      'MetadataSchemaVersion': 'v1/2013/07',
                                      'guid': '00000000000000000000000000000000'},
                             'Instrument': {'ControlSoftwareVersion': '1.6.0',
                                            'Manufacturer': 'FEI Company',
                                            'InstrumentId': '6308',
                                            'InstrumentClass': 'Talos',
                                            'ComputerName': 'TALOS-D6308'},
                             'Acquisition': {'AcquisitionStartDatetime': {'DateTime': '1488794225'},
                                             'AcquisitionDatetime': {'DateTime': '0'},
                                             'BeamType': '',
                                             'SourceType': 'XFEG'},
                             'Optics': {'GunLensSetting': '4',
                                        'ExtractorVoltage': '4098.9010989010985',
                                        'AccelerationVoltage': '200000',
                                        'SpotIndex': '7',
                                        'C1LensIntensity': '0.20658579468727112',
                                        'C2LensIntensity': '0.3045177161693573',
                                        'ObjectiveLensIntensity': '0.94855332374572754',
                                        'IntermediateLensIntensity': '-0.078506767749786377',
                                        'DiffractionLensIntensity': '0.40315291285514832',
                                        'Projector1LensIntensity': '-0.95146656036376953',
                                        'Projector2LensIntensity': '-0.92141127586364746',
                                        'MiniCondenserLensIntensity': '-0.91795682907104492',
                                        'ScreenCurrent': '2.4672221479801257e-010',
                                        'LastMeasuredScreenCurrent': '2.4672221479801257e-010',
                                        'FullScanFieldOfView': {'x': '2.7148363970517e-006',
                                                                'y': '2.7148363970517e-006'},
                                        'Focus': '0',
                                        'StemFocus': '0',
                                        'Defocus': '0',
                                        'HighMagnificationMode': 'None',
                                        'Apertures': {'Aperture-0': {'Name': 'C1',
                                                                     'Number': '1',
                                                                     'MechanismType': 'Motorized',
                                                                     'Type': 'Circular',
                                                                     'Diameter': '0.002',
                                                                     'Enabled': '0',
                                                                     'PositionOffset': {'x': '0.0012696000000000001',
                                                                                        'y': '0.0013899200000000002'}},
                                                      'Aperture-1': {'Name': 'C2',
                                                                     'Number': '2',
                                                                     'MechanismType': 'Motorized',
                                                                     'Type': 'Circular',
                                                                     'Diameter': '6.9999999999999994e-005',
                                                                     'Enabled': '2',
                                                                     'PositionOffset': {'x': '0.00706064',
                                                                                        'y': '0.0013604800000000001'}},
                                                      'Aperture-2': {'Name': 'OBJ',
                                                                     'Number': '4',
                                                                     'MechanismType': 'Motorized',
                                                                     'Type': 'None',
                                                                     'PositionOffset': {'x': '0.00014992',
                                                                                        'y': '-0.00050016000000000004'}
                                                                     },
                                                      'Aperture-3': {'Name': 'SA',
                                                                     'Number': '5',
                                                                     'MechanismType': 'Motorized',
                                                                     'Type': 'Circular',
                                                                     'Diameter': '0.00080000000000000004',
                                                                     'Enabled': '3',
                                                                     'PositionOffset': {'x': '0.00061903999999999995',
                                                                                        'y': '0.00437376'}}},
                                        'OperatingMode': '2',
                                        'TemOperatingSubMode': 'None',
                                        'ProjectorMode': '1',
                                        'EFTEMOn': 'false',
                                        'ObjectiveLensMode': 'HM',
                                        'IlluminationMode': 'None',
                                        'ProbeMode': '1',
                                        'CameraLength': '0.098000000000000004'},
                             'EnergyFilter': {'EntranceApertureType': ''},
                             'Stage': {'Position': {'x': '-9.3740169600000009e-006',
                                                    'y': '0.00014370383231999999',
                                                    'z': '2.8805790000000001e-005'},
                                       'AlphaTilt': '0.00011072368774652029',
                                       'BetaTilt': '0',
                                       'HolderType': 'Single Tilt'},
                             'Scan': {'ScanSize': {'width': '0', 'height': '0'},
                                      'MainsLockOn': 'false',
                                      'FrameTime': '6.0416000000000007',
                                      'ScanRotation': '1.6580627893946103'},
                             'Vacuum': {'VacuumMode': 'Ready'},
                             'Detectors': {'Detector-0': {'DetectorName': 'BF',
                                                          'DetectorType': 'ScanningDetector',
                                                          'Inserted': 'false',
                                                          'Enabled': 'true'},
                                           'Detector-1': {'DetectorName': 'DF2',
                                                          'DetectorType': 'ScanningDetector',
                                                          'Inserted': 'false',
                                                          'Enabled': 'true'},
                                           'Detector-2': {'DetectorName': 'DF4',
                                                          'DetectorType': 'ScanningDetector',
                                                          'Inserted': 'false',
                                                          'Enabled': 'true'},
                                           'Detector-3': {'DetectorName': 'HAADF',
                                                          'DetectorType': 'ScanningDetector',
                                                          'Inserted': 'true',
                                                          'Enabled': 'true'},
                                           'Detector-4': {'DetectorName': 'SuperXG21',
                                                          'DetectorType': 'AnalyticalDetector',
                                                          'Inserted': 'true',
                                                          'Enabled': 'true',
                                                          'ElevationAngle': '0.38397244000000003',
                                                          'AzimuthAngle': '0.78539816339744828',
                                                          'CollectionAngle': '0.22500000000000001',
                                                          'Dispersion': '10',
                                                          'PulseProcessTime': '3.0000000000000001e-006',
                                                          'RealTime': '0.029570824999999999',
                                                          'LiveTime': '0.0259824552188541',
                                                          'InputCountRate': '0',
                                                          'OutputCountRate': '0',
                                                          'AnalyticalDetectorShutterState': '0',
                                                          'OffsetEnergy': '-1000',
                                                          'ElectronicsNoise': '31',
                                                          'BeginEnergy': '163'},
                                           'Detector-5': {'DetectorName': 'SuperXG22',
                                                          'DetectorType': 'AnalyticalDetector',
                                                          'Inserted': 'true',
                                                          'Enabled': 'true',
                                                          'ElevationAngle': '0.38397244000000003',
                                                          'AzimuthAngle': '2.3561944901923448',
                                                          'CollectionAngle': '0.22500000000000001',
                                                          'Dispersion': '10',
                                                          'PulseProcessTime': '3.0000000000000001e-006',
                                                          'RealTime': '0.029381749999999998',
                                                          'LiveTime': '0.026721048183602016',
                                                          'InputCountRate': '0',
                                                          'OutputCountRate': '0',
                                                          'AnalyticalDetectorShutterState': '0',
                                                          'OffsetEnergy': '-1000',
                                                          'ElectronicsNoise': '31',
                                                          'BeginEnergy': '164'},
                                           'Detector-6': {'DetectorName': 'SuperXG23',
                                                          'DetectorType': 'AnalyticalDetector',
                                                          'Inserted': 'true',
                                                          'Enabled': 'true',
                                                          'ElevationAngle': '0.38397244000000003',
                                                          'AzimuthAngle': '3.9269908169872414',
                                                          'CollectionAngle': '0.22500000000000001',
                                                          'Dispersion': '10',
                                                          'PulseProcessTime': '3.0000000000000001e-006',
                                                          'RealTime': '0.029267149999999999',
                                                          'LiveTime': '0.026188349677848218',
                                                          'InputCountRate': '0',
                                                          'OutputCountRate': '0',
                                                          'AnalyticalDetectorShutterState': '0',
                                                          'OffsetEnergy': '-1000',
                                                          'ElectronicsNoise': '31',
                                                          'BeginEnergy': '170'},
                                           'Detector-7': {'DetectorName': 'SuperXG24',
                                                          'DetectorType': 'AnalyticalDetector',
                                                          'Inserted': 'true',
                                                          'Enabled': 'true',
                                                          'ElevationAngle': '0.38397244000000003',
                                                          'AzimuthAngle': '5.497787143782138',
                                                          'CollectionAngle': '0.22500000000000001',
                                                          'Dispersion': '10',
                                                          'PulseProcessTime': '3.0000000000000001e-006',
                                                          'RealTime': '0.029135249999999998',
                                                          'LiveTime': '0.025585437925304481',
                                                          'InputCountRate': '0',
                                                          'OutputCountRate': '0',
                                                          'AnalyticalDetectorShutterState': '0',
                                                          'OffsetEnergy': '-1000',
                                                          'ElectronicsNoise': '31',
                                                          'BeginEnergy': '169'},
                                           'Detector-8': {'DetectorName': 'BM-Ceta',
                                                          'DetectorType': 'ImagingDetector'}},
                             'BinaryResult': {'AcquisitionUnit': '',
                                              'CompositionType': '',
                                              'Detector': 'SuperXG2',
                                              'Encoding': ''},
                             'Sample': '',
                             'GasInjectionSystems': '',
                             'CustomProperties': {'Aperture[C1].Name': {'type': 'string', 'value': '2000'},
                                                  'Aperture[C2].Name': {'type': 'string', 'value': '70'},
                                                  'Aperture[OBJ].Name': {'type': 'string', 'value': 'None'},
                                                  'Aperture[SA].Name': {'type': 'string', 'value': '800'},
                                                  'Detectors[SuperXG21].BilatThresholdHi': {'type': 'double',
                                                                                            'value': '0.00314897'},
                                                  'Detectors[SuperXG21].KMax': {'type': 'double', 'value': '180'},
                                                  'Detectors[SuperXG21].KMin': {'type': 'double', 'value': '120'},
                                                  'Detectors[SuperXG21].PulsePairResolutionTime': {'type': 'double',
                                                                                                   'value': '5e-007'},
                                                  'Detectors[SuperXG21].SpectrumBeginEnergy': {'type': 'int32',
                                                                                               'value': '163'},
                                                  'Detectors[SuperXG22].BilatThresholdHi': {'type': 'double',
                                                                                            'value': '0.00312853'},
                                                  'Detectors[SuperXG22].KMax': {'type': 'double', 'value': '180'},
                                                  'Detectors[SuperXG22].KMin': {'type': 'double', 'value': '120'},
                                                  'Detectors[SuperXG22].PulsePairResolutionTime': {'type': 'double',
                                                                                                   'value': '5e-007'},
                                                  'Detectors[SuperXG22].SpectrumBeginEnergy': {'type': 'int32',
                                                                                               'value': '164'},
                                                  'Detectors[SuperXG23].BilatThresholdHi': {'type': 'double',
                                                                                            'value': '0.00324329'},
                                                  'Detectors[SuperXG23].KMax': {'type': 'double', 'value': '180'},
                                                  'Detectors[SuperXG23].KMin': {'type': 'double', 'value': '120'},
                                                  'Detectors[SuperXG23].PulsePairResolutionTime': {'type': 'double',
                                                                                                   'value': '5e-007'},
                                                  'Detectors[SuperXG23].SpectrumBeginEnergy': {'type': 'int32',
                                                                                               'value': '170'},
                                                  'Detectors[SuperXG24].BilatThresholdHi': {'type': 'double',
                                                                                            'value': '0.00319699'},
                                                  'Detectors[SuperXG24].KMax': {'type': 'double', 'value': '180'},
                                                  'Detectors[SuperXG24].KMin': {'type': 'double', 'value': '120'},
                                                  'Detectors[SuperXG24].PulsePairResolutionTime': {'type': 'double',
                                                                                                   'value': '5e-007'},
                                                  'Detectors[SuperXG24].SpectrumBeginEnergy': {'type': 'int32',
                                                                                               'value': '169'},
                                                  'StemMagnification': {'type': 'double', 'value': '40000'}},
                             'AcquisitionSettings': {'encoding': 'uint16',
                                                     'bincount': '4096',
                                                     'StreamEncoding': 'uint16',
                                                     'Size': '1048576'}}

        self.assertDictEqual(datasets[0].original_metadata, original_metadata)
        array_100_200 = np.array([2.90475e+05, 2.17745e+05, 1.32847e+05, 4.95570e+04, 1.41030e+04,
                                  2.60900e+03, 3.77000e+02, 6.70000e+01, 2.30000e+01, 1.50000e+01,
                                  4.00000e+00, 6.00000e+00, 7.00000e+00, 6.00000e+00, 5.00000e+00,
                                  6.00000e+00, 5.00000e+00, 1.00000e+01, 5.00000e+00, 2.10000e+01,
                                  2.40000e+01, 6.00000e+01, 1.24000e+02, 1.99000e+02, 3.87000e+02,
                                  4.99000e+02, 5.39000e+02, 5.09000e+02, 3.82000e+02, 2.62000e+02,
                                  1.19000e+02, 4.30000e+01, 2.40000e+01, 3.00000e+00, 1.00000e+00,
                                  3.00000e+00, 3.00000e+00, 5.00000e+00, 2.00000e+00, 4.00000e+00,
                                  4.00000e+00, 3.00000e+00, 4.00000e+00, 3.00000e+00, 4.00000e+00,
                                  4.00000e+00, 7.00000e+00, 1.30000e+01, 1.60000e+01, 2.20000e+01,
                                  1.80000e+01, 3.20000e+01, 1.80000e+01, 2.10000e+01, 1.90000e+01,
                                  9.00000e+00, 3.00000e+00, 1.00000e+00, 0.00000e+00, 1.00000e+00,
                                  1.00000e+00, 1.00000e+00, 2.00000e+00, 0.00000e+00, 4.00000e+00,
                                  1.00000e+00, 2.00000e+00, 1.00000e+00, 2.00000e+00, 1.00000e+00,
                                  2.00000e+00, 0.00000e+00, 1.00000e+00, 2.00000e+00, 2.00000e+00,
                                  2.00000e+00, 3.00000e+00, 1.00000e+00, 2.00000e+00, 0.00000e+00,
                                  8.00000e+00, 3.00000e+00, 0.00000e+00, 4.00000e+00, 0.00000e+00,
                                  3.00000e+00, 2.00000e+00, 2.00000e+00, 1.00000e+00, 2.00000e+00,
                                  4.00000e+00, 3.00000e+00, 3.00000e+00, 9.00000e+00, 3.00000e+00,
                                  7.00000e+00, 3.00000e+00, 2.00000e+00, 2.00000e+00, 1.00000e+00])
        self.assertTrue(np.allclose(np.array(datasets[0])[100:200], array_100_200, rtol=1e-5, atol=1e-2))
        os.remove(file_name)

    def test_read_image(self):
        file_name  = wget.download(
            'https://raw.githubusercontent.com/pycroscopy/SciFiReaders/master/data/fei_emd_image.emd')
        emd_reader = EMDReader(file_name)
        datasets = emd_reader.read()
        emd_reader.close()

        self.assertIsInstance(datasets[0], sidpy.Dataset)
        self.assertTrue(datasets[0].data_type.name, 'IMAGE')
        self.assertTrue(datasets[0].ndim == 2)
        self.assertTrue(len(datasets) == 1)
        print(datasets[0].original_metadata)
        original_metadata = datasets[0].original_metadata

        self.assertTrue(datasets[0].units == 'counts')
        self.assertTrue(datasets[0].shape == (512, 512))
        self.assertTrue(datasets[0].quantity == 'intensity')
        self.assertIsInstance(datasets[0].x, sidpy.Dimension)
        self.assertTrue(original_metadata['Core']['MetadataDefinitionVersion'] == '7.9')
        self.assertTrue(original_metadata['Instrument']['Manufacturer'] == 'FEI Company')
        self.assertTrue(original_metadata['Acquisition']['SourceType'] == 'XFEG')
        self.assertTrue(original_metadata['Optics']['AccelerationVoltage'] == '200000')
        os.remove(file_name)

    def test_read_spectrum_image(self):
        file_name  = wget.download(
            'https://raw.githubusercontent.com/pycroscopy/SciFiReaders/master/data/fei_emd_si.emd')
        emd_reader = EMDReader(file_name)
        datasets = emd_reader.read()
        emd_reader.close()

        self.assertIsInstance(datasets[0], sidpy.Dataset)
        self.assertTrue(datasets[0].data_type.name, 'IMAGE_STACK')
        self.assertTrue(datasets[0].data_type.name, 'SPECTRAL_IMAGE')
        self.assertTrue(datasets[1].ndim == 3)
        self.assertTrue(len(datasets) == 2)
        print(datasets[0].original_metadata)
        original_metadata = datasets[0].original_metadata

        self.assertTrue(datasets[0].units == 'counts')
        self.assertTrue(datasets[0].shape == (5, 16, 16))
        self.assertTrue(datasets[1].shape == (512, 512, 4096))
        self.assertTrue(datasets[0].quantity == 'intensity')
        self.assertIsInstance(datasets[0].x, sidpy.Dimension)
        self.assertTrue(original_metadata['Core']['MetadataDefinitionVersion'] == '7.9')
        self.assertTrue(original_metadata['Instrument']['Manufacturer'] == 'FEI Company')
        self.assertTrue(original_metadata['Acquisition']['SourceType'] == 'XFEG')
        self.assertTrue(original_metadata['Optics']['AccelerationVoltage'] == '200000')
        os.remove(file_name)

if __name__ == '__main__':
    unittest.main()
