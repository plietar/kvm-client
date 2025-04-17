from construct import (
    Bytes,
    Const,
    FixedSized,
    GreedyBytes,
    Int8ul,
    Int16ul,
    Int32ul,
    Struct,
    Switch,
    this,
)

ASP2000 = Struct(
    "iEngVersion" / Int16ul,
    "wHeaderLen" / Int16ul,
    "SourceMode_X" / Int16ul,
    "SourceMode_Y" / Int16ul,
    "SourceMode_ColorDepth" / Int16ul,
    "SourceMode_RefreshRate" / Int16ul,
    "SourceMode_ModeIndex" / Int8ul,
    "DestinationMode_X" / Int16ul,
    "DestinationMode_Y" / Int16ul,
    "DestinationMode_ColorDepth" / Int16ul,
    "DestinationMode_RefreshRate" / Int16ul,
    "DestinationMode_ModeIndex" / Int8ul,
    "FrameHdr_StartCode" / Int32ul,
    "FrameHdr_FrameNumber" / Int32ul,
    "FrameHdr_HSize" / Int16ul,
    "FrameHdr_VSize" / Int16ul,
    "FrameHdr_Reserved1" / Int32ul,
    "FrameHdr_Reserved2" / Int32ul,
    "FrameHdr_CompressionMode" / Int8ul,
    "FrameHdr_JPEGScaleFactor" / Int8ul,
    "FrameHdr_JPEGTableSelector" / Int8ul,
    "FrameHdr_JPEGYUVTableMapping" / Int8ul,
    "FrameHdr_SharpModeSelection" / Int8ul,
    "FrameHdr_AdvanceTableSelector" / Int8ul,
    "FrameHdr_AdvanceScaleFactor" / Int8ul,
    "FrameHdr_NumberOfMB" / Int32ul,
    "FrameHdr_RC4Enable" / Int8ul,
    "FrameHdr_RC4Reset" / Int8ul,
    "FrameHdr_Mode420" / Int8ul,
    #  INF_DATA
    "InfData_DownScalingMethod" / Int8ul,
    "InfData_DifferentialSetting" / Int8ul,
    "InfData_AnalogDifferentialThreshold" / Int16ul,
    "InfData_DigitalDifferentialThreshold" / Int16ul,
    "InfData_ExternalSignalEnable" / Int8ul,
    "InfData_AutoMode" / Int8ul,
    "InfData_VQMode" / Int8ul,
    #  COMPRESS_DATA
    "CompressData_SourceFrameSize" / Int32ul,
    "CompressData_CompressSize" / Int32ul,
    "CompressData_HDebug" / Int32ul,
    "CompressData_VDebug" / Int32ul,
    "InputSignal" / Int8ul,
    "Cursor_XPos" / Int16ul,
    "Cursor_YPos" / Int16ul,
    "data" / GreedyBytes,
)

VideoEnveloppe = Struct(
    "signature" / Const(b"ASP-2000"),
    "header_length" / Int16ul,
    "data_length" / Int32ul,
    "command" / Int16ul,
    "status" / Int16ul,
    "reserved" / Int16ul,
    "data" / FixedSized(this.data_length, ASP2000),
)

VideoPacket = Struct(
    "a" / Bytes(7),
    "length" / Int32ul,
    "b" / Bytes(10),
    "payload" / FixedSized(this.length, VideoEnveloppe),
)

KVMHeader = Struct("op" / Int8ul, "length" / Int32ul, "status" / Int16ul)
KVMPayload = Switch(
    this.op,
    {
        0x05: VideoPacket,
    },
    default=GreedyBytes,
)

IUSB = Struct(
    "signature" / Const(b"IUSB    "),
    "major" / Const(bytes([1])),
    "minor" / Const(bytes([0])),
    "header_length" / Int8ul,
    "header_checksum" / Int8ul,
    "dataPacketLen" / Int32ul,
    "serverCaps" / Int8ul,
    "deviceType" / Int8ul,
    "protocol" / Int8ul,
    "direction" / Int8ul,
    "deviceNumber" / Int8ul,
    "interfaceNumber" / Int8ul,
    "clientData" / Bytes(2),
    "sequenceNumber" / Int32ul,
    "reserved" / Bytes(4),
)
