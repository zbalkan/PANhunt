from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Union, cast

from . import panutils
from .panutils import FileLikePayload
from .enums import ScanStatusEnum
from .pan import PAN
from .scancontext import ScanContext


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
    logical_path: str
    depth: int
    container_chain: list[str]

    def __init__(self, basename: str, dirname: str, payload: Optional[Union[bytes, FileLikePayload]] = None,
                 mimetype: Optional[str] = None, encoding: Optional[str] = None,
                 err: Optional[Exception] = None, context: Optional[ScanContext] = None) -> None:
        self.basename = basename
        self.dirname = dirname
        self.abspath = str(Path(dirname) / basename)
        self.status = ScanStatusEnum.Success
        self.errors = []
        self.matches = []
        self.extension = panutils.get_ext(self.basename)
        self.extensions = panutils.get_exts(self.basename)
        self.logical_path = context.logical_path if context else self.abspath
        self.depth = context.depth if context else 0
        self.container_chain = list(context.container_chain) if context else []

        if err is not None:
            self._set_error(str(err))

        if mimetype is None or encoding is None:
            detected_mime, detected_encoding, mime_err = panutils.get_mimetype(self.abspath, payload)
            if mime_err:
                needed = []
                if mimetype is None:
                    needed.append('MIME type')
                if encoding is None:
                    needed.append('encoding')
                self._set_error(
                    f'Failed to detect {" and ".join(needed)}. Inner exception: {mime_err}'
                )
            self.mime_type = mimetype if mimetype is not None else detected_mime
            self.encoding = encoding if encoding is not None else detected_encoding
        else:
            self.mime_type = mimetype
            self.encoding = encoding

        self._set_file_stats(payload)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Finding):
            return NotImplemented
        return self.abspath.lower() == other.abspath.lower()

    def __str__(self) -> str:
        return f'{self.abspath} ({self.mime_type} : {self.encoding})'

    def _set_file_stats(self, payload: Optional[Union[bytes, FileLikePayload]]) -> None:
        try:
            if payload is None:
                self.size = os.stat(self.abspath).st_size
            elif isinstance(payload, bytes):
                self.size = len(payload)
            elif panutils.is_file_like(payload):
                seekable = getattr(payload, 'seekable', None)
                seek = getattr(payload, 'seek', None)
                tell = getattr(payload, 'tell', None)
                if not callable(seekable) or not seekable() or not callable(seek) or not callable(tell):
                    self.size = 0
                else:
                    position = tell()
                    seek(0, os.SEEK_END)
                    self.size = cast(int, tell())
                    seek(position)
        except Exception as ex:
            self.size = -1
            self._set_error(str(ex))

    def _set_error(self, error_msg: str) -> None:
        self.errors.append(error_msg)
        self.status = ScanStatusEnum.Failure
        logging.error(f'{error_msg} ({self.abspath})')
