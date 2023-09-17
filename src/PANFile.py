import logging
import os
from datetime import datetime
from typing import Optional

import panutils
from dispatcher import Dispatcher
from enums import ScanStatusEnum

TEXT_FILE_SIZE_LIMIT: int = 1_073_741_824  # 1Gb


class PANFile:
    """ PANFile: class for a file that can check itself for PANs"""

    filename: str
    dir: str
    path: str
    file_category: ScanStatusEnum
    # errors: Optional[list[str]] = None
    errors: Optional[list] = None
    # matches: list[PAN]
    matches: list
    size: int
    accessed: datetime
    modified: datetime
    created: datetime

    mime_type: str
    encoding: str
    extension: str
    # extensions: list[str]
    extensions: list

    def __init__(self, filename: str, file_dir: str) -> None:
        self.filename = filename
        self.dir = file_dir
        self.path = os.path.join(self.dir, self.filename)
        self.file_category = ScanStatusEnum.Scannable
        self.matches = []

        self.extension = panutils.get_ext(self.path)
        self.extensions = panutils.get_exts(self.path)

        try:
            self.mime_type, self.encoding = panutils.get_mime_data_from_file(
                self.path)
        except Exception as ex:
            self.mime_type = 'Unknown'
            self.encoding = 'Unknown'
            self.set_error(
                f'Failed to detect mimetype and encoding. Inner exception: {ex}')

        self.set_file_stats()

        if self.size > TEXT_FILE_SIZE_LIMIT:
            self.set_error(
                error_msg=f'File size {panutils.size_friendly(size=self.size)} over limit of {panutils.size_friendly(size=TEXT_FILE_SIZE_LIMIT)} for checking for file \"{self.filename}\"')

    def __cmp__(self, other: 'PANFile') -> bool:

        return self.path.lower() == other.path.lower()

    def set_file_stats(self) -> None:

        try:
            stat: os.stat_result = os.stat(self.path)
            self.size = stat.st_size
            self.accessed = self.dtm_from_ts(stat.st_atime)
            self.modified = self.dtm_from_ts(stat.st_mtime)
            self.created = self.dtm_from_ts(stat.st_ctime)
        except Exception as ex:
            self.size = -1
            self.set_error(str(ex))
            self.file_category = ScanStatusEnum.NotScanned

    def dtm_from_ts(self, ts: float) -> datetime:

        try:
            return datetime.fromtimestamp(ts)
        except ValueError as ex:
            if ts == -753549904:
                # Mac OSX "while copying" thing
                return datetime(1946, 2, 14, 8, 34, 56)
            else:
                self.set_error(str(ex))
                return datetime(1970, 1, 1)

    def set_error(self, error_msg: str) -> None:
        if self.errors is None:
            self.errors = [error_msg]
        else:
            self.errors.append(error_msg)
        logging.error(f'{error_msg} ({self.path})')

    def scan_with(self, dispatcher: Dispatcher, verbose: bool) -> list:
        """Checks the file for matching regular expressions: if a ZIP then each file in the ZIP (recursively) or the text in a document"""
        if verbose:
            logging.info(f'Scanning file: {self.path} ({self.mime_type})')

        try:
            match_list: list = dispatcher.dispatch(
                mime_type=self.mime_type, extension=self.extension, path=self.path, encoding=self.encoding)
            if len(match_list) > 0:
                self.matches.extend(match_list)
        except IOError as ex:
            self.set_error(str(ex))
        except Exception as ex:
            self.set_error(str(ex))

        if len(self.matches) > 0:
            logging.info(
                f'Found {len(self.matches)} possible PANs in \"{self.path}\"')
        return self.matches

    def __str__(self) -> str:
        return f'{self.path} ({self.mime_type} : {self.encoding})'
