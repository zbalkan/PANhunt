import logging
import os
from datetime import datetime
from typing import Optional

import panutils
from enums import ScanStatusEnum
from PAN import PAN

FILE_SIZE_LIMIT: int = 1_073_741_824  # 1Gb


class ScannableFile:
    """ PANFile: class for a file that can check itself for PANs"""

    filename: str
    dir: str
    path: str
    file_category: ScanStatusEnum
    errors: Optional[list[str]] = None
    matches: list[PAN]
    size: int

    mime_type: str
    encoding: str
    extension: str
    extensions: list[str]

    value_bytes: Optional[bytes] = None

    def __init__(self, filename: str, file_dir: str, value_bytes: Optional[bytes] = None) -> None:
        self.filename = filename
        self.dir = file_dir
        self.path = os.path.join(self.dir, self.filename)
        self.file_category = ScanStatusEnum.Scannable

        self.value_bytes = value_bytes

        self.matches = []

        self.extension = panutils.get_ext(self.filename)
        self.extensions = panutils.get_exts(self.filename)

        try:
            if value_bytes:
                self.mime_type, self.encoding = panutils.get_mime_data_from_buffer(
                    value_bytes)
            else:
                self.mime_type, self.encoding = panutils.get_mime_data_from_file(
                    self.path)
        except Exception as ex:
            self.mime_type = 'Unknown/Unknown'
            self.encoding = 'Unknown'
            self.set_error(
                f'Failed to detect mimetype and encoding. Inner exception: {ex}')

        self.set_file_stats()

        if self.size > FILE_SIZE_LIMIT:
            self.set_error(
                error_msg=f'File size {panutils.size_friendly(size=self.size)} over limit of {panutils.size_friendly(size=FILE_SIZE_LIMIT)} for checking for file \"{self.filename}\"')

    def __cmp__(self, other: 'ScannableFile') -> bool:

        return self.path.lower() == other.path.lower()

    def set_file_stats(self) -> None:

        try:
            if self.value_bytes:
                self.size = len(self.value_bytes)
            else:
                stat: os.stat_result = os.stat(self.path)
                self.size = stat.st_size
        except Exception as ex:
            self.size = -1
            self.set_error(str(ex))
            self.file_category = ScanStatusEnum.NotScanned

    def set_error(self, error_msg: str) -> None:
        if self.errors is None:
            self.errors = [error_msg]
        else:
            self.errors.append(error_msg)
        logging.error(f'{error_msg} ({self.path})')

    def __str__(self) -> str:
        return f'{self.path} ({self.mime_type} : {self.encoding})'
