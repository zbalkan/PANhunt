import os
from io import IOBase
from typing import Optional, Union


class Job:

    basename: str
    dirname: str
    payload: Optional[Union[bytes, IOBase]]
    abspath: str

    def __init__(self, basename: str, dirname: str, payload: Optional[Union[bytes, IOBase]] = None) -> None:
        self.basename = basename
        self.dirname = dirname
        self.payload = payload
        self.abspath = os.path.join(self.dirname, self.basename)
