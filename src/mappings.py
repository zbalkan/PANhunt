from typing import Optional, Type

from enums import FileTypeEnum
from scanner import BasicScanner, EmlScanner, MboxScanner, MsgScanner, PdfScanner, PstScanner, ScannerBase, ZipScanner


def get_scanner_by_file(mime_type: str, extension: str) -> Optional[Type[ScannerBase]]:
    m: dict[FileTypeEnum, Type[ScannerBase]] = __map_file_to_scanner_mapping()
    s: Optional[Type[ScannerBase]] = m.get(
        __map_file_to_filetype(mime_type=mime_type, extension=extension))
    return s


def __map_file_to_scanner_mapping() -> dict[FileTypeEnum, Type[ScannerBase]]:
    return {
        FileTypeEnum.Plaintext: BasicScanner,
        FileTypeEnum.Rtf: BasicScanner,
        FileTypeEnum.MsWord: ZipScanner,
        FileTypeEnum.MsExcel: ZipScanner,
        FileTypeEnum.MsPowerpoint: ZipScanner,
        FileTypeEnum.MsMsg: MsgScanner,
        FileTypeEnum.MsPst: PstScanner,
        FileTypeEnum.Eml: EmlScanner,
        FileTypeEnum.Mbox: MboxScanner,
        FileTypeEnum.Pdf: PdfScanner,
        FileTypeEnum.Zip: ZipScanner
    }


def __map_file_to_filetype(mime_type: str, extension: str) -> FileTypeEnum:
    if mime_type in ['text/plain']:
        if mime_type in ['text/plain'] and extension in [".eml"]:
            return FileTypeEnum.Eml
        elif mime_type in ['text/plain'] and extension in [".mbox"]:
            return FileTypeEnum.Mbox
        else:
            return FileTypeEnum.Plaintext
    elif mime_type in ["application/octet-stream"]:
        if extension in [".mbox"]:
            return FileTypeEnum.Mbox
        else:
            return FileTypeEnum.Plaintext
    elif mime_type in ["message/rfc822"]:
        if extension in [".eml"]:
            return FileTypeEnum.Eml
        else:
            return FileTypeEnum.Plaintext
    elif mime_type in ['text/xml']:
        return FileTypeEnum.Plaintext
    elif mime_type in ['text/html']:
        return FileTypeEnum.Plaintext
    elif mime_type in ['text/rtf']:
        return FileTypeEnum.Plaintext
    # and extension in [".docx"]:
    elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        return FileTypeEnum.MsWord
    # and extension in [".xlsx"]:
    elif mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        return FileTypeEnum.MsExcel
    # and extension in [".pptx"]:
    elif mime_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation']:
        return FileTypeEnum.MsPowerpoint
    # and extension in [".ppt"]:
    elif mime_type in ['application/vnd.ms-powerpoint']:
        return FileTypeEnum.Plaintext
    # and extension in [".xls"]:
    elif mime_type in ['application/vnd.ms-excel']:
        return FileTypeEnum.Plaintext
    # and extension in [".doc"]:
    elif mime_type in ['application/msword']:
        return FileTypeEnum.Plaintext
    # and extension in [".msg"]:
    elif mime_type in ['application/vnd.ms-outlook']:
        return FileTypeEnum.MsMsg
    elif mime_type in ['application/pdf']:  # and extension in [".pdf"]:
        return FileTypeEnum.Pdf
    elif mime_type in ['application/zip']:  # and extension in [".zip"]:
        return FileTypeEnum.Zip
    else:
        return FileTypeEnum.Unknown
