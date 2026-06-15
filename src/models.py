from dataclasses import dataclass
from datetime import datetime, timedelta

from config import ScanConfiguration
from finding import Finding


@dataclass
class ScanResult:
    """Data transfer object carrying all output from a completed scan."""

    matched_files: list[Finding]
    interesting_files: list[Finding]
    start_time: datetime
    end_time: datetime
    config: ScanConfiguration

    @property
    def elapsed(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def pan_count(self) -> int:
        return sum(len(f.matches) for f in self.matched_files if f.matches)
