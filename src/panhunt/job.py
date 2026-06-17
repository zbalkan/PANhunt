import os
from typing import Optional, Union

from .panutils import FileLikePayload
from .scancontext import ScanContext


class Job:

    basename: str
    dirname: str
    payload: Optional[Union[bytes, FileLikePayload]]
    abspath: str
    context: Optional[ScanContext]

    def __init__(
            self,
            basename: str,
            dirname: str,
            payload: Optional[Union[bytes, FileLikePayload]] = None,
            context: Optional[ScanContext] = None) -> None:
        self.basename = basename
        self.dirname = dirname
        self.payload = payload
        self.abspath = os.path.join(self.dirname, self.basename)
        self.context = context
