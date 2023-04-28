import logging
import os
from datetime import datetime
from typing import Optional

from enums import FileTypeEnum
from PAN import PAN
from scanner import Dispatcher


class PANFile:
    """ PANFile: class for a file that can check itself for PANs"""

    filename: str
    dir: str
    path: str
    root: str
    ext: str
    filetype: Optional[FileTypeEnum]
    errors: Optional[list[str]] = None
    matches: list[PAN]
    size: int
    accessed: datetime
    modified: datetime
    created: datetime

    def __init__(self, filename: str, file_dir: str) -> None:
        self.filename = filename
        self.dir = file_dir
        self.path = os.path.join(self.dir, self.filename)
        self.root, self.ext = os.path.splitext(self.filename)
        self.filetype = None
        self.matches = []

    def __cmp__(self, other: 'PANFile') -> bool:

        return self.path.lower() == other.path.lower()

    def set_file_stats(self) -> None:

        try:
            stat: os.stat_result = os.stat(self.path)
            self.size = stat.st_size
            self.accessed = self.dtm_from_ts(stat.st_atime)
            self.modified = self.dtm_from_ts(stat.st_mtime)
            self.created = self.dtm_from_ts(stat.st_ctime)
        except WindowsError as ex:
            self.size = -1
            self.set_error(str(ex))

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
        logging.error(error_msg)

    def check_regexs(self, dispatcher: Dispatcher) -> list[PAN]:
        """Checks the file for matching regular expressions: if a ZIP then each file in the ZIP (recursively) or the text in a document"""

        if self.filetype:
            try:
                match_list: list[PAN] = dispatcher.dispatch(
                    file_type=self.filetype, path=self.path)
                self.matches.extend(match_list)
            except IOError as ex:
                self.set_error(str(ex))
            except Exception as ex:
                self.set_error(str(ex))

        if len(self.matches) > 0:
            logging.info(
                f'Found {len(self.matches)} possible PANs in \"{self.path}\"')
        return self.matches
