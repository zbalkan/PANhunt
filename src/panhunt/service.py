import logging
from datetime import datetime
from typing import Callable, Optional

from .buffer import InMemoryJobBuffer, JobBuffer
from .config import ScanConfiguration
from .dispatcher import Dispatcher
from .hunter import Hunter
from .models import ScanResult


class PanHuntService:
    """Orchestrates a full scan session. No UI concerns."""

    def __init__(self, buffer_factory: Optional[Callable[[], JobBuffer]] = None) -> None:
        self._buffer_factory: Callable[[], JobBuffer] = buffer_factory or InMemoryJobBuffer

    def scan(self, config: ScanConfiguration) -> ScanResult:
        """Run a scan and return structured results."""
        start_time = datetime.now()
        logging.info("Started searching in file(s).")

        buffer = self._buffer_factory()
        dispatcher = Dispatcher(buffer=buffer, config=config)
        hunter = Hunter(dispatcher=dispatcher, buffer=buffer)

        findings, failures = hunter.hunt(config)
        logging.info("Finished searching.")

        return ScanResult(
            matched_files=findings,
            interesting_files=failures,
            start_time=start_time,
            end_time=datetime.now(),
            config=config,
        )
