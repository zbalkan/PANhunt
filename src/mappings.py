from typing import Optional, Type

from archive import Archive, GzipArchive, TarArchive, XzArchive, ZipArchive
from enums import FileTypeEnum
from scanner import PlainTextFileScanner, EmlScanner, MboxScanner, MsgScanner, PdfScanner, PstScanner, ScannerBase

# This dictionary is defined at the module level to ensure that only one instance
# of internal_map exists throughout the program's runtime. This prevents unnecessary
# re-creation of the dictionary on each function call, optimizing both memory usage
# and performance.
file_type_to_scanner_map: dict[FileTypeEnum, Type[ScannerBase]] = {
    FileTypeEnum.Plaintext: PlainTextFileScanner,
    FileTypeEnum.Rtf: PlainTextFileScanner,
    FileTypeEnum.MsMsg: MsgScanner,
    FileTypeEnum.MsPst: PstScanner,
    FileTypeEnum.Eml: EmlScanner,
    FileTypeEnum.Mbox: MboxScanner,
    FileTypeEnum.Pdf: PdfScanner,
}

file_type_to_archive_map: dict[FileTypeEnum, Type[Archive]] = {
    FileTypeEnum.MsWord: ZipArchive,
    FileTypeEnum.MsExcel: ZipArchive,
    FileTypeEnum.MsPowerpoint: ZipArchive,
    FileTypeEnum.Zip: ZipArchive,
    FileTypeEnum.Tar: TarArchive,
    FileTypeEnum.Gzip: GzipArchive,
    FileTypeEnum.Xz: XzArchive
}


def get_scanner_by_file(mime_type: str, extension: str) -> Optional[Type[ScannerBase]]:
    m: dict[FileTypeEnum, Type[ScannerBase]] = __map_file_to_scanner_mapping()
    s: Optional[Type[ScannerBase]] = m.get(
        __get_filetype(mime_type_text=mime_type, extension=extension))
    return s


def __map_file_to_scanner_mapping() -> dict[FileTypeEnum, Type[ScannerBase]]:
    return file_type_to_scanner_map


def get_archive_by_file(mime_type: str, extension: str) -> Optional[Type[Archive]]:
    m: dict[FileTypeEnum, Type[Archive]
            ] = __map_file_to_archive_mapping()
    s: Optional[Type[Archive]] = m.get(
        __get_filetype(mime_type_text=mime_type, extension=extension))
    return s


def __map_file_to_archive_mapping() -> dict[FileTypeEnum, Type[Archive]]:
    return file_type_to_archive_map


def __get_filetype(mime_type_text: str, extension: str) -> FileTypeEnum:

    l: list[str] = mime_type_text.split(sep='/')
    mime_type: str = l[0]
    mime_subtype: str = l[1]

    # return early
    if mime_type in ['Unknown', 'audio', 'video', 'image', 'chemical', 'model', 'gcode', 'x-conference', 'font', 'x-world']:
        return FileTypeEnum.Unknown

    # Possible extensions for message: .eml, .mht, .mhtml,.mime,.nws
    if mime_type in ['text', 'message']:
        if mime_subtype in ['plain', 'rfc822'] and extension in [".eml"]:
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
        elif mime_subtype in ['x-tar']:
            return FileTypeEnum.Tar
        elif mime_subtype in ['x-gzip']:
            return FileTypeEnum.Gzip
        elif mime_subtype in ['x-xz']:
            return FileTypeEnum.Xz
        else:
            return FileTypeEnum.Unknown

    else:
        return FileTypeEnum.Unknown
