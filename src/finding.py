import logging
import os
from typing import Optional

import panutils
from enums import ScanStatusEnum
from PAN import PAN


class Finding:

    basename: str
    dirname: str
    abspath: str
    status: ScanStatusEnum
    errors: Optional[list[str]] = None
    matches: list[PAN]
    size: int

    mime_type: str
    encoding: str
    extension: str
    extensions: list[str]

    payload: Optional[bytes] = None

    def __init__(self, basename: str, dirname: str, payload: Optional[bytes] = None,
                 mimetype: Optional[str] = None, encoding: Optional[str] = None, err: Optional[Exception] = None) -> None:
        self.basename = basename
        self.dirname = dirname
        self.abspath = os.path.join(self.dirname, self.basename)
        self.status = ScanStatusEnum.Success

        self.payload = payload

        self.matches = []

        self.extension = panutils.get_ext(self.basename)
        self.extensions = panutils.get_exts(self.basename)

        if mimetype is not None:
            self.mime_type = mimetype
        if encoding is not None:
            self.encoding = encoding

        if err is not None:
            self.set_error(str(err))

        if mimetype is None or encoding is None:
            self.mime_type, self.encoding, err = panutils.get_mimetype(self.abspath,
                                                                       payload)
            if err:
                self.set_error(
                    f'Failed to detect mimetype and encoding. Inner exception: {err}')

        self.set_file_stats()
        self.payload = None

    def __cmp__(self, other: 'Finding') -> bool:

        return self.abspath.lower() == other.abspath.lower()

    def set_file_stats(self) -> None:

        try:
            if self.payload:
                self.size = len(self.payload)
            else:
                stat: os.stat_result = os.stat(self.abspath)
                self.size = stat.st_size
        except Exception as ex:
            self.size = -1
            self.set_error(str(ex))
            self.status = ScanStatusEnum.Failure

    def set_error(self, error_msg: str) -> None:
        if self.errors is None:
            self.errors = [error_msg]
        else:
            self.errors.append(error_msg)
        logging.error(f'{error_msg} ({self.abspath})')

    def __str__(self) -> str:
        return f'{self.abspath} ({self.mime_type} : {self.encoding})'
