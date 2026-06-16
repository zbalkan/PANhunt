from typing import Optional, Type

from . import enums
from .archive import Archive, GzipArchive, OpenDocumentArchive, TarArchive, XzArchive, ZipArchive
from .buffer import JobBuffer
from .config import ScanConfiguration
from .finder import PanFinder
from .scanner import (
    EmlScanner,
    MboxScanner,
    MsgScanner,
    PdfScanner,
    PlainTextFileScanner,
    PstScanner,
    ScannerBase,
)


class ScannerFactory:
    """Creates scanner instances with properly injected dependencies."""

    def __init__(self, buffer: JobBuffer, config: ScanConfiguration) -> None:
        self._buffer = buffer
        self._config = config
        self._pan_finder = PanFinder(config)
        self._registry: dict[enums.FileTypeEnum, Type[ScannerBase]] = self._build_registry()

    def get_scanner(self, mime_type: str, extension: str) -> Optional[ScannerBase]:
        """Get a scanner instance for the given file type."""
        file_type = self._detect_file_type(mime_type, extension)
        scanner_class = self._registry.get(file_type)

        if not scanner_class:
            return None

        return scanner_class(
            buffer=self._buffer,
            config=self._config,
            pan_finder=self._pan_finder
        )

    def register(self, file_type: enums.FileTypeEnum, scanner_class: Type[ScannerBase]) -> None:
        """Register a custom scanner implementation."""
        self._registry[file_type] = scanner_class

    def _build_registry(self) -> dict[enums.FileTypeEnum, Type[ScannerBase]]:
        """Build the scanner registry."""
        return {
            enums.FileTypeEnum.Plaintext: PlainTextFileScanner,
            enums.FileTypeEnum.Rtf: PlainTextFileScanner,
            enums.FileTypeEnum.MsMsg: MsgScanner,
            enums.FileTypeEnum.MsPst: PstScanner,
            enums.FileTypeEnum.Eml: EmlScanner,
            enums.FileTypeEnum.Mbox: MboxScanner,
            enums.FileTypeEnum.Pdf: PdfScanner,
        }

    def _detect_file_type(self, mime_type: str, extension: str) -> enums.FileTypeEnum:
        """Detect file type from MIME type and extension."""
        return self._get_filetype(mime_type, extension)

    @staticmethod
    def _get_filetype(mime_type_text: str, extension: str) -> enums.FileTypeEnum:
        """Extract file type from MIME type and extension."""
        parts = mime_type_text.split(sep='/')
        mime_type = parts[0]
        mime_subtype = parts[1] if len(parts) > 1 else ''

        # Early return for non-document types
        if mime_type in ['Unknown', 'audio', 'video', 'image', 'chemical', 'model', 'gcode', 'x-conference', 'font', 'x-world']:
            return enums.FileTypeEnum.Unknown

        # Text/message types
        if mime_type in ['text', 'message']:
            if mime_subtype == 'rfc822':
                return enums.FileTypeEnum.Eml
            if mime_subtype == 'plain':
                if extension == '.eml':
                    return enums.FileTypeEnum.Eml
                if extension == '.mbox':
                    return enums.FileTypeEnum.Mbox
            return enums.FileTypeEnum.Plaintext

        # Application types
        if mime_type == 'application':
            extension_file_type = ScannerFactory._get_filetype_from_extension(extension)

            if mime_subtype == 'octet-stream':
                if extension_file_type != enums.FileTypeEnum.Unknown:
                    return extension_file_type
                return enums.FileTypeEnum.Unknown

            if (mime_subtype in ['zip', 'x-zip-compressed']
                    and extension_file_type in ScannerFactory._opendocument_filetypes()):
                return extension_file_type

            if mime_subtype == 'vnd.openxmlformats-officedocument.wordprocessingml.document':
                return enums.FileTypeEnum.MsWord
            elif mime_subtype == 'vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                return enums.FileTypeEnum.MsExcel
            elif mime_subtype == 'vnd.openxmlformats-officedocument.presentationml.presentation':
                return enums.FileTypeEnum.MsPowerpoint
            elif mime_subtype in ['vnd.oasis.opendocument.text', 'vnd.oasis.opendocument.text-template']:
                return enums.FileTypeEnum.OpenDocumentText
            elif mime_subtype == 'vnd.oasis.opendocument.text-flat-xml':
                return enums.FileTypeEnum.Plaintext
            elif mime_subtype in ['vnd.oasis.opendocument.spreadsheet', 'vnd.oasis.opendocument.spreadsheet-template']:
                return enums.FileTypeEnum.OpenDocumentSpreadsheet
            elif mime_subtype == 'vnd.oasis.opendocument.spreadsheet-flat-xml':
                return enums.FileTypeEnum.Plaintext
            elif mime_subtype in ['vnd.oasis.opendocument.presentation', 'vnd.oasis.opendocument.presentation-template']:
                return enums.FileTypeEnum.OpenDocumentPresentation
            elif mime_subtype == 'vnd.oasis.opendocument.presentation-flat-xml':
                return enums.FileTypeEnum.Plaintext
            elif mime_subtype in ['vnd.oasis.opendocument.graphics', 'vnd.oasis.opendocument.graphics-template']:
                return enums.FileTypeEnum.OpenDocumentDrawing
            elif mime_subtype == 'vnd.oasis.opendocument.formula':
                return enums.FileTypeEnum.OpenDocumentFormula
            elif mime_subtype == 'vnd.oasis.opendocument.text-master':
                return enums.FileTypeEnum.OpenDocumentMaster
            elif mime_subtype in ['vnd.ms-powerpoint', 'vnd.ms-excel', 'msword']:
                return enums.FileTypeEnum.Plaintext
            elif mime_subtype == 'vnd.ms-outlook':
                return enums.FileTypeEnum.MsMsg
            elif mime_subtype == 'pdf':
                return enums.FileTypeEnum.Pdf
            elif mime_subtype == 'zip':
                return enums.FileTypeEnum.Zip
            elif mime_subtype == 'x-tar':
                return enums.FileTypeEnum.Tar
            elif mime_subtype in ['gzip', 'x-gzip', 'gzip-compressed', 'gzipped', 'x-gunzip', 'x-compress', 'x-compressed']:
                return enums.FileTypeEnum.Gzip
            elif mime_subtype == 'x-xz':
                return enums.FileTypeEnum.Xz

        return enums.FileTypeEnum.Unknown

    @staticmethod
    def _opendocument_filetypes() -> set[enums.FileTypeEnum]:
        return {
            enums.FileTypeEnum.OpenDocumentText,
            enums.FileTypeEnum.OpenDocumentSpreadsheet,
            enums.FileTypeEnum.OpenDocumentPresentation,
            enums.FileTypeEnum.OpenDocumentDrawing,
            enums.FileTypeEnum.OpenDocumentFormula,
            enums.FileTypeEnum.OpenDocumentMaster,
        }

    @staticmethod
    def _get_filetype_from_extension(extension: str) -> enums.FileTypeEnum:
        extension_map = {
            '.mbox': enums.FileTypeEnum.Mbox,
            '.pst': enums.FileTypeEnum.MsPst,
            '.odt': enums.FileTypeEnum.OpenDocumentText,
            '.ott': enums.FileTypeEnum.OpenDocumentText,
            '.ods': enums.FileTypeEnum.OpenDocumentSpreadsheet,
            '.ots': enums.FileTypeEnum.OpenDocumentSpreadsheet,
            '.odp': enums.FileTypeEnum.OpenDocumentPresentation,
            '.otp': enums.FileTypeEnum.OpenDocumentPresentation,
            '.odg': enums.FileTypeEnum.OpenDocumentDrawing,
            '.otg': enums.FileTypeEnum.OpenDocumentDrawing,
            '.odf': enums.FileTypeEnum.OpenDocumentFormula,
            '.odm': enums.FileTypeEnum.OpenDocumentMaster,
            '.fodt': enums.FileTypeEnum.Plaintext,
            '.fods': enums.FileTypeEnum.Plaintext,
            '.fodp': enums.FileTypeEnum.Plaintext,
        }
        return extension_map.get(extension, enums.FileTypeEnum.Unknown)


class ArchiveFactory:
    """Creates archive handler instances for supported archive formats."""

    _registry: dict[enums.FileTypeEnum, Type[Archive]] = {
        enums.FileTypeEnum.MsWord: ZipArchive,
        enums.FileTypeEnum.MsExcel: ZipArchive,
        enums.FileTypeEnum.MsPowerpoint: ZipArchive,
        enums.FileTypeEnum.OpenDocumentText: OpenDocumentArchive,
        enums.FileTypeEnum.OpenDocumentSpreadsheet: OpenDocumentArchive,
        enums.FileTypeEnum.OpenDocumentPresentation: OpenDocumentArchive,
        enums.FileTypeEnum.OpenDocumentDrawing: OpenDocumentArchive,
        enums.FileTypeEnum.OpenDocumentFormula: OpenDocumentArchive,
        enums.FileTypeEnum.OpenDocumentMaster: OpenDocumentArchive,
        enums.FileTypeEnum.Zip: ZipArchive,
        enums.FileTypeEnum.Tar: TarArchive,
        enums.FileTypeEnum.Gzip: GzipArchive,
        enums.FileTypeEnum.Xz: XzArchive,
    }

    @classmethod
    def get_archive(cls, mime_type: str, extension: str) -> Optional[Type[Archive]]:
        """Get archive handler for the given file type."""
        file_type = ScannerFactory._get_filetype(mime_type, extension)
        return cls._registry.get(file_type)

    @classmethod
    def register(cls, file_type: enums.FileTypeEnum, archive_class: Type[Archive]) -> None:
        """Register a custom archive handler."""
        cls._registry[file_type] = archive_class
