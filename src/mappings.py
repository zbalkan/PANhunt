from typing import Optional, Type

from enums import FileTypeEnum
from scanner import BasicScanner, EmlScanner, MboxScanner, MsgScanner, PdfScanner, PstScanner, ScannerBase, ZipScanner


def get_scanner_by_file(mime_type: str, extension: str) -> Optional[Type[ScannerBase]]:
    m: dict[FileTypeEnum, Type[ScannerBase]] = __map_file_to_scanner_mapping()
    s: Optional[Type[ScannerBase]] = m.get(
        __map_file_to_filetype(mime_type_text=mime_type, extension=extension))
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


def __map_file_to_filetype(mime_type_text: str, extension: str) -> FileTypeEnum:
    l: list[str] = mime_type_text.split('/')
    mime_type: str = l[0]
    mime_subtype: str = l[1]

    # return early
    if mime_type in ['audio', 'video', 'image', 'chemical', 'model', 'gcode', 'x-conference', 'font' , 'x-world']:
        return FileTypeEnum.Unknown

    if mime_type in ['text', 'message']: # Possible extensions for message: .eml, .mht, .mhtml,.mime,.nws
        if mime_subtype in ['plain'] and extension in [".eml"]:
            return FileTypeEnum.Eml
        elif mime_subtype in ['plain'] and extension in [".mbox"]:
            return FileTypeEnum.Mbox
        else:
            return FileTypeEnum.Plaintext
    elif mime_type in ['application']:
        if mime_subtype in ["octet-stream"]:
            if extension in [".mbox"]:
                return FileTypeEnum.Mbox
            else:
                return FileTypeEnum.Unknown
        elif mime_subtype in ['vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return FileTypeEnum.MsWord
        elif mime_subtype in ['vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            return FileTypeEnum.MsExcel
        elif mime_subtype in ['vnd.openxmlformats-officedocument.presentationml.presentation']:
            return FileTypeEnum.MsPowerpoint
        elif mime_subtype in ['vnd.ms-powerpoint']:
            return FileTypeEnum.Plaintext
        elif mime_subtype in ['vnd.ms-excel']:
            return FileTypeEnum.Plaintext
        elif mime_subtype in ['msword']:
            return FileTypeEnum.Plaintext
        elif mime_subtype in ['vnd.ms-outlook']:
            return FileTypeEnum.MsMsg
        elif mime_subtype in ['pdf']:
            return FileTypeEnum.Pdf
        elif mime_subtype in ['zip']:
            return FileTypeEnum.Zip
        else:
            return FileTypeEnum.Unknown

    else:
        return FileTypeEnum.Unknown
