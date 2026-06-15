import logging
import os
import re
import time

from buffer import JobBuffer
from config import ScanConfiguration
from dispatcher import Dispatcher
from finding import Finding
from job import Job


class Hunter:

    def __init__(self, dispatcher: Dispatcher, buffer: JobBuffer) -> None:
        self._dispatcher = dispatcher
        self._buffer = buffer

    def hunt(self, config: ScanConfiguration) -> tuple[list[Finding], list[Finding]]:
        self._dispatcher.start()

        logging.info(f"Search base: {config.search_dir}")

        if config.file_path is not None:
            p = str(config.file_path)
            basename: str = os.path.basename(p)
            dirname: str = os.path.dirname(p)
            if not self._is_directory_excluded(dirname, config):
                self._buffer.enqueue(Job(basename, dirname=dirname))
        else:
            for root, _, files in os.walk(config.search_dir):
                if self._is_directory_excluded(root, config):
                    continue
                for file in files:
                    self._buffer.enqueue(Job(basename=file, dirname=root, payload=None))

        self._buffer.mark_input_complete()

        while not self._buffer.is_finished():
            time.sleep(0.1)

        return self._dispatcher.findings, self._dispatcher.failures

    def _is_directory_excluded(self, dirname: str, config: ScanConfiguration) -> bool:
        for excluded_dir in config.excluded_directories:
            if os.name == 'nt':
                if re.match(f"{re.escape(excluded_dir.lower())}\\.*", re.escape(dirname.lower())):
                    return True
            else:
                if re.match(f"{re.escape(excluded_dir)}/.*", re.escape(dirname)):
                    return True
        return False
