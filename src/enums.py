from enum import Enum


class PTypeEnum(Enum):

    PtypInteger16 = 0x02
    PtypInteger32 = 0x03
    PtypFloating32 = 0x04
    PtypFloating64 = 0x05
    PtypCurrency = 0x06
    PtypFloatingTime = 0x07
    PtypErrorCode = 0x0A
    PtypBoolean = 0x0B
    PtypInteger64 = 0x14
    PtypString = 0x1F
    PtypString8 = 0x1E
    PtypTime = 0x40
    PtypGuid = 0x48
    PtypServerId = 0xFB
    PtypRestriction = 0xFD
    PtypRuleAction = 0xFE
    PtypBinary = 0x102
    PtypMultipleInteger16 = 0x1002
    PtypMultipleInteger32 = 0x1003
    PtypMultipleFloating32 = 0x1004
    PtypMultipleFloating64 = 0x1005
    PtypMultipleCurrency = 0x1006
    PtypMultipleFloatingTime = 0x1007
    PtypMultipleInteger64 = 0x1014
    PtypMultipleString = 0x101F
    PtypMultipleString8 = 0x101E
    PtypMultipleTime = 0x1040
    PtypMultipleGuid = 0x1048
    PtypMultipleBinary = 0x1102
    PtypUnspecified = 0x0
    PtypNull = 0x01
    PtypObject = 0x0D


class PropIdEnum(Enum):

    PidTagNameidBucketCount = 0x0001
    PidTagNameidStreamGuid = 0x0002
    PidTagNameidStreamEntry = 0x0003
    PidTagNameidStreamString = 0x0004
    PidTagNameidBucketBase = 0x1000
    PidTagItemTemporaryFlags = 0x1097
    PidTagPstBestBodyProptag = 0x661D
    PidTagPstIpmsubTreeDescendant = 0x6705
    PidTagPstSubTreeContainer = 0x6772
    PidTagLtpParentNid = 0x67F1
    PidTagLtpRowId = 0x67F2
    PidTagLtpRowVer = 0x67F3
    PidTagPstPassword = 0x67FF
    PidTagMapiFormComposeCommand = 0x682F
    PidTagRecordKey = 0x0FF9
    PidTagDisplayName = 0x3001
    PidTagIpmSubTreeEntryId = 0x35E0
    PidTagIpmWastebasketEntryId = 0x35E3
    PidTagFinderEntryId = 0x35E7
    PidTagContentCount = 0x3602
    PidTagContentUnreadCount = 0x3603
    PidTagSubfolders = 0x360A
    PidTagReplItemid = 0x0E30
    PidTagReplChangenum = 0x0E33
    PidTagReplVersionHistory = 0x0E34
    PidTagReplFlags = 0x0E38
    PidTagContainerClass = 0x3613
    PidTagPstHiddenCount = 0x6635
    PidTagPstHiddenUnread = 0x6636
    PidTagImportance = 0x0017
    PidTagMessageClassW = 0x001A
    PidTagSensitivity = 0x0036
    PidTagSubjectW = 0x0037
    PidTagClientSubmitTime = 0x0039
    PidTagSentRepresentingSearchKey = 0x003B
    PidTagSentRepresentingNameW = 0x0042
    PidTagMessageToMe = 0x0057
    PidTagMessageCcMe = 0x0058
    PidTagConversationTopicW = 0x0070
    PidTagConversationIndex = 0x0071
    PidTagDisplayCcW = 0x0E03
    PidTagDisplayToW = 0x0E04
    PidTagMessageDeliveryTime = 0x0E06
    PidTagMessageFlags = 0x0E07
    PidTagMessageSize = 0x0E08
    PidTagMessageStatus = 0x0E17
    PidTagReplCopiedfromVersionhistory = 0x0E3C
    PidTagReplCopiedfromItemid = 0x0E3D
    PidTagLastModificationTime = 0x3008
    PidTagSmtpAddress = 0x39FE
    PidTagSecureSubmitFlags = 0x65C6
    PidTagOfflineAddressBookName = 0x6800
    PidTagSendOutlookRecallReport = 0x6803
    PidTagOfflineAddressBookTruncatedProperties = 0x6805
    PidTagViewDescriptorFlags = 0x7003
    PidTagViewDescriptorLinkTo = 0x7004
    PidTagViewDescriptorViewFolder = 0x7005
    PidTagViewDescriptorName = 0x7006
    PidTagViewDescriptorVersion = 0x7007
    PidTagCreationTime = 0x3007
    PidTagSearchKey = 0x300B
    PidTagRecipientType = 0x0c15
    PidTagResponsibility = 0x0E0F
    PidTagObjectType = 0x0FFE
    PidTagEntryID = 0x0FFF
    PidTagAddressType = 0x3002
    PidTagEmailAddress = 0x3003
    PidTagDisplayType = 0x3900
    PidTag7BitDisplayName = 0x39FF
    PidTagSendRichInfo = 0x3A40
    PidTagAttachmentSize = 0x0E20
    PidTagAttachFilename = 0x3704
    PidTagAttachMethod = 0x3705
    PidTagRenderingPosition = 0x370B
    PidTagSenderEntryId = 0x0C19
    PidTagSenderName = 0x0C1A
    PidTagSenderSearchKey = 0x0C1D
    PidTagSenderAddressType = 0x0C1E
    PidTagRead = 0x0E69
    PidTagHasAttachments = 0x0E1B
    PidTagBody = 0x1000
    PidTagRtfCompressed = 0x1009
    PidTagAttachDataBinary = 0x3701
    PidTagAttachDataObject = 0x3701
    PidTagOriginalDisplayTo = 0x0074
    PidTagTransportMessageHeaders = 0x007D
    PidTagSenderSmtpAddress = 0x5D01
    PidTagSentRepresentingSmtpAddress = 0x5D02
    PidTagReceivedBySmtpAddress = 0x5D07
    PidTagReceivedRepresentingSmtpAddress = 0x5D08
    PidTagAttachMimeTag = 0x370E
    PidTagAttachExtension = 0x3703
    PidTagAttachLongFilename = 0x3707
    PidTagXOriginatingIp = 0x8028  # Non-standard X-Originating-IP


class ScanStatusEnum(Enum):
    Success = 0
    Failure = 5


class FileTypeEnum(Enum):
    Unknown = 0
    Plaintext = 1
    Rtf = 2
    MsWord = 3
    MsExcel = 4
    MsPowerpoint = 5
    Pdf = 6
    MsMsg = 7
    MsPst = 8
    Eml = 9
    Mbox = 10
    Zip = 11
    Tar = 12
    Gzip = 13
    Xz = 14
