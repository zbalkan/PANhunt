from __future__ import annotations

import logging
import os
import threading

from .buffer import JobBuffer
from .config import ScanConfiguration
from .dispatcher import Dispatcher
from .finding import Finding
from .job import Job


class Hunter:
    def __init__(self, dispatcher: Dispatcher, buffer: JobBuffer) -> None:
        self._dispatcher = dispatcher
        self._buffer = buffer

    def hunt(self, config: ScanConfiguration) -> tuple[list[Finding], list[Finding]]:
        self._dispatcher.start()

        logging.info("Search base: %s", config.target_path)
        if not config.quiet:
            print(f"Scanning {config.target_path}...", flush=True)

        done = threading.Event()
        progress_thread = None

        if not config.quiet:
            progress_thread = threading.Thread(
                target=self._print_progress,
                args=(done,),
                daemon=True,
            )
            progress_thread.start()

        target_path = str(config.target_path)
        if os.path.isfile(target_path):
            basename = os.path.basename(target_path)
            dirname = os.path.dirname(target_path)
            if not self._is_directory_excluded(dirname, config):
                self._buffer.enqueue(Job(basename, dirname=dirname))
        else:
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [
                    d for d in dirs
                    if not self._is_directory_excluded(os.path.join(root, d), config)
                ]
                for file in files:
                    self._buffer.enqueue(
                        Job(basename=file, dirname=root, payload=None))

        self._buffer.mark_input_complete()

        # Prefer a blocking wait method on the buffer if you can add one.
        while not self._buffer.is_finished():
            done.wait(0.25)  # cheap wait for reporter cadence; not a busy loop

        done.set()
        if progress_thread is not None:
            progress_thread.join()
            print(flush=True)

        self._dispatcher.stop()
        self._dispatcher.join()

        return self._dispatcher.get_findings(), self._dispatcher.get_failures()

    def _print_progress(self, done: threading.Event) -> None:
        while not done.wait(0.25):
            print(".", end="", flush=True)

    def _is_directory_excluded(self, dirname: str, config: ScanConfiguration) -> bool:
        sep = os.sep
        lower_dirname = dirname.lower()
        for excluded_dir in config.excluded_directories:
            if lower_dirname == excluded_dir or lower_dirname.startswith(excluded_dir + sep):
                return True
        return False
