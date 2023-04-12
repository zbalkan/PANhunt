import datetime
from dataclasses import dataclass

from PANFile import PANFile


@dataclass
class Stats:
    """A basic value object to store statistics
    """
    files_total: int
    pans_found: int
    all_files: list[PANFile]
    start: datetime.datetime
    end: datetime.datetime
