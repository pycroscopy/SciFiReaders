from enum import IntEnum

class MDTFrameType(IntEnum):
    MDT_FRAME_SCANNED      = 0
    MDT_FRAME_SPECTROSCOPY = 1
    MDT_FRAME_TEXT         = 3
    MDT_FRAME_OLD_MDA      = 105
    MDT_FRAME_MDA          = 106
    MDT_FRAME_PALETTE      = 107
    MDT_FRAME_CURVES_NEW   = 190
    MDT_FRAME_CURVES       = 201

class MDADataType(IntEnum):
    MDA_DATA_INT8          = -1
    MDA_DATA_UINT8         =  1
    MDA_DATA_INT16         = -2
    MDA_DATA_UINT16        =  2
    MDA_DATA_INT32         = -4
    MDA_DATA_UINT32        =  4
    MDA_DATA_INT64         = -8
    MDA_DATA_UINT64        =  8
    MDA_DATA_FLOAT32       = -(4 + 23 * 256) # -5892
    MDA_DATA_FLOAT48       = -(6 + 39 * 256) # -9990
    MDA_DATA_FLOAT64       = -(8 + 52 * 256) # -13320
    MDA_DATA_FLOAT80       = -(10 + 63 * 256) # -16138
    MDA_DATA_FLOATFIX      = -(8 + 256 * 256) # -65544

class MDTUnit(IntEnum):
    MDT_UNIT_RAMAN_SHIFT     = -10
    MDT_UNIT_RESERVED0       = -9
    MDT_UNIT_RESERVED1       = -8
    MDT_UNIT_RESERVED2       = -7
    MDT_UNIT_RESERVED3       = -6
    MDT_UNIT_METER           = -5
    MDT_UNIT_CENTIMETER      = -4
    MDT_UNIT_MILLIMETER      = -3
    MDT_UNIT_MIKROMETER      = -2
    MDT_UNIT_NANOMETER       = -1
    MDT_UNIT_ANGSTROM        = 0
    MDT_UNIT_NANOAMPERE      = 1
    MDT_UNIT_VOLT            = 2
    MDT_UNIT_NONE            = 3
    MDT_UNIT_KILOHERZ        = 4
    MDT_UNIT_DEGREES         = 5
    MDT_UNIT_PERCENT         = 6
    MDT_UNIT_CELSIUM_DEGREE  = 7
    MDT_UNIT_VOLT_HIGH       = 8
    MDT_UNIT_SECOND          = 9
    MDT_UNIT_MILLISECOND     = 10
    MDT_UNIT_MIKROSECOND     = 11
    MDT_UNIT_NANOSECOND      = 12
    MDT_UNIT_COUNTS          = 13
    MDT_UNIT_PIXELS          = 14
    MDT_UNIT_RESERVED_SFOM0  = 15
    MDT_UNIT_RESERVED_SFOM1  = 16
    MDT_UNIT_RESERVED_SFOM2  = 17
    MDT_UNIT_RESERVED_SFOM3  = 18
    MDT_UNIT_RESERVED_SFOM4  = 19
    MDT_UNIT_AMPERE2         = 20
    MDT_UNIT_MILLIAMPERE     = 21
    MDT_UNIT_MIKROAMPERE     = 22
    MDT_UNIT_NANOAMPERE2     = 23
    MDT_UNIT_PICOAMPERE      = 24
    MDT_UNIT_VOLT2           = 25
    MDT_UNIT_MILLIVOLT       = 26
    MDT_UNIT_MIKROVOLT       = 27
    MDT_UNIT_NANOVOLT        = 28
    MDT_UNIT_PICOVOLT        = 29
    MDT_UNIT_NEWTON          = 30
    MDT_UNIT_MILLINEWTON     = 31
    MDT_UNIT_MIKRONEWTON     = 32
    MDT_UNIT_NANONEWTON      = 33
    MDT_UNIT_PICONEWTON      = 34
    MDT_UNIT_RESERVED_DOS0   = 35
    MDT_UNIT_RESERVED_DOS1   = 36
    MDT_UNIT_RESERVED_DOS2   = 37
    MDT_UNIT_RESERVED_DOS3   = 38
    MDT_UNIT_RESERVED_DOS4   = 39
    MDT_UNIT_HERZ            = 1170

class MDTMode(IntEnum):
    MDT_MODE_STM = 0
    MDT_MODE_AFM = 1

class MDTInputSignal(IntEnum):
    MDT_INPUT_EXTENSION_SLOT = 0
    MDT_INPUT_BIAS_V         = 1
    MDT_INPUT_GROUND         = 2

class MDTLiftMode(IntEnum):
    MDT_TUNE_STEP  = 0
    MDT_TUNE_FINE  = 1
    MDT_TUNE_SLOPE = 2

class MDTSPMTechnique(IntEnum):
    MDT_SPM_TECHNIQUE_CONTACT_MODE     = 0
    MDT_SPM_TECHNIQUE_SEMICONTACT_MODE = 1
    MDT_SPM_TECHNIQUE_TUNNEL_CURRENT   = 2
    MDT_SPM_TECHNIQUE_SNOM             = 3

class MDTSPMMode(IntEnum):
    MDT_SPM_MODE_CONSTANT_FORCE               = 0
    MDT_SPM_MODE_CONTACT_CONSTANT_HEIGHT      = 1
    MDT_SPM_MODE_CONTACT_ERROR                = 2
    MDT_SPM_MODE_LATERAL_FORCE                = 3
    MDT_SPM_MODE_FORCE_MODULATION             = 4
    MDT_SPM_MODE_SPREADING_RESISTANCE_IMAGING = 5
    MDT_SPM_MODE_SEMICONTACT_TOPOGRAPHY       = 6
    MDT_SPM_MODE_SEMICONTACT_ERROR            = 7
    MDT_SPM_MODE_PHASE_CONTRAST               = 8
    MDT_SPM_MODE_AC_MAGNETIC_FORCE            = 9
    MDT_SPM_MODE_DC_MAGNETIC_FORCE            = 10
    MDT_SPM_MODE_ELECTROSTATIC_FORCE          = 11
    MDT_SPM_MODE_CAPACITANCE_CONTRAST         = 12
    MDT_SPM_MODE_KELVIN_PROBE                 = 13
    MDT_SPM_MODE_CONSTANT_CURRENT             = 14
    MDT_SPM_MODE_BARRIER_HEIGHT               = 15
    MDT_SPM_MODE_CONSTANT_HEIGHT              = 16
    MDT_SPM_MODE_AFAM                         = 17
    MDT_SPM_MODE_CONTACT_EFM                  = 18
    MDT_SPM_MODE_SHEAR_FORCE_TOPOGRAPHY       = 19
    MDT_SPM_MODE_SFOM                         = 20
    MDT_SPM_MODE_CONTACT_CAPACITANCE          = 21
    MDT_SPM_MODE_SNOM_TRANSMISSION            = 22
    MDT_SPM_MODE_SNOM_REFLECTION              = 23
    MDT_SPM_MODE_SNOM_ALL                     = 24
    MDT_SPM_MODE_SNOM                         = 25

class MDTADCMode(IntEnum):
    MDT_ADC_MODE_OFF       = -1
    MDT_ADC_MODE_HEIGHT    = 0
    MDT_ADC_MODE_DFL       = 1
    MDT_ADC_MODE_LATERAL_F = 2
    MDT_ADC_MODE_BIAS_V    = 3
    MDT_ADC_MODE_CURRENT   = 4
    MDT_ADC_MODE_FB_OUT    = 5
    MDT_ADC_MODE_MAG       = 6
    MDT_ADC_MODE_MAG_SIN   = 7
    MDT_ADC_MODE_MAG_COS   = 8
    MDT_ADC_MODE_RMS       = 9
    MDT_ADC_MODE_CALCMAG   = 10
    MDT_ADC_MODE_PHASE1    = 11
    MDT_ADC_MODE_PHASE2    = 12
    MDT_ADC_MODE_CALCPHASE = 13
    MDT_ADC_MODE_EX1       = 14
    MDT_ADC_MODE_EX2       = 15
    MDT_ADC_MODE_HVX       = 16
    MDT_ADC_MODE_HVY       = 17
    MDT_ADC_MODE_SNAP_BACK = 18

class MDTXMLScanLocation(IntEnum):
    MDT_HLT = 0
    MDT_HLB = 1
    MDT_HRT = 2
    MDT_HRB = 3
    MDT_VLT = 4
    MDT_VLB = 5
    MDT_VRT = 6
    MDT_VRB = 7

class MDTXMLParamType(IntEnum):
    MDT_XML_NONE             = 0
    MDT_XML_LASER_WAVELENGTH = 1
    MDT_XML_UNITS            = 2
    MDT_XML_DATAARRAY        = -1

class ByteSize(IntEnum):
    FILE_HEADER_SIZE      = 32
    FRAME_HEADER_SIZE     = 22
    FRAME_MODE_SIZE       = 8
    AXIS_SCALES_SIZE      = 30
    SCAN_VARS_MIN_SIZE    = 77
    SPECTRO_VARS_MIN_SIZE = 38
