import logging
import os
from pathlib import Path
from typing import Optional

import panutils
from enums import ScanStatusEnum
from pan import PAN


class Finding:

    basename: str
    dirname: str
    abspath: str
    status: ScanStatusEnum
    errors: list[str]
    matches: list[PAN]
    size: int
    mime_type: str
    encoding: str
    extension: str
    extensions: list[str]

    def __init__(self, basename: str, dirname: str, payload: Optional[bytes] = None,
                 mimetype: Optional[str] = None, encoding: Optional[str] = None,
                 err: Optional[Exception] = None) -> None:
        self.basename = basename
        self.dirname = dirname
        self.abspath = str(Path(dirname) / basename)
        self.status = ScanStatusEnum.Success
        self.errors = []
        self.matches = []
        self.extension = panutils.get_ext(self.basename)
        self.extensions = panutils.get_exts(self.basename)

        if mimetype is not None:
            self.mime_type = mimetype
        if encoding is not None:
            self.encoding = encoding

        if err is not None:
            self._set_error(str(err))

        if mimetype is None or encoding is None:
            self.mime_type, self.encoding, mime_err = panutils.get_mimetype(self.abspath, payload)
            if mime_err:
                self._set_error(f'Failed to detect mimetype and encoding. Inner exception: {mime_err}')

        self._set_file_stats(payload)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Finding):
            return NotImplemented
        return self.abspath.lower() == other.abspath.lower()

    def __str__(self) -> str:
        return f'{self.abspath} ({self.mime_type} : {self.encoding})'

    def _set_file_stats(self, payload: Optional[bytes]) -> None:
        try:
            self.size = len(payload) if payload else os.stat(self.abspath).st_size
        except Exception as ex:
            self.size = -1
            self._set_error(str(ex))

    def _set_error(self, error_msg: str) -> None:
        self.errors.append(error_msg)
        self.status = ScanStatusEnum.Failure
        logging.error(f'{error_msg} ({self.abspath})')
