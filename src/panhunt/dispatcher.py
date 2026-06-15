import logging
import os
import threading
from io import IOBase
from typing import Optional

from . import enums
from . import panutils
from .archive import Archive
from .buffer import JobBuffer
from .config import ScanConfiguration
from .exceptions import PANHuntException
from .factory import ArchiveFactory, ScannerFactory
from .finding import Finding
from .job import Job
from .pan import PAN


class Dispatcher:
    findings: list[Finding]
    failures: list[Finding]

    _stop_event: threading.Event
    _threads: list[threading.Thread]
    __findings_lock: threading.Lock

    def __init__(self, buffer: JobBuffer, config: ScanConfiguration) -> None:
        self._buffer = buffer
        self._config = config
        self._scanner_factory = ScannerFactory(buffer=buffer, config=config)
        self._stop_event = threading.Event()
        self._threads = []
        self.findings = []
        self.failures = []
        self.__findings_lock = threading.Lock()

    def start(self) -> None:
        self._stop_event.clear()
        self._threads = [
            threading.Thread(
                target=self._run_dispatch_loop,
                name=f"panhunt-worker-{i}",
                daemon=False,
            )
            for i in range(self._config.worker_count)
        ]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def join(self) -> None:
        for thread in self._threads:
            thread.join()

    def get_findings(self) -> list[Finding]:
        with self.__findings_lock:
            return list(self.findings)

    def get_failures(self) -> list[Finding]:
        with self.__findings_lock:
            return list(self.failures)

    def _run_dispatch_loop(self) -> None:
        while not self._stop_event.is_set():
            job: Optional[Job] = self._buffer.dequeue(timeout=0.1)
            if job is None:
                if self._buffer.is_finished():
                    break
                continue
            try:
                res: Optional[Finding] = self._dispatch_job(job)
                if res is not None:
                    with self.__findings_lock:
                        if res.status == enums.ScanStatusEnum.Success:
                            self.findings.append(res)
                        else:
                            self.failures.append(res)
            finally:
                if job.payload and isinstance(job.payload, IOBase):
                    try:
                        job.payload.close()
                    except Exception as e:
                        logging.warning(f"Failed to close payload for {job.abspath}: {e}")
                job.payload = None
                job = None
                self._buffer.complete_job()

    def _dispatch_job(self, job: Job) -> Optional[Finding]:
        logging.info(f"Processing job: {job.abspath}")

        if job.payload is not None:
            if isinstance(job.payload, IOBase):
                try:
                    job.payload.seek(0, 2)
                    size = job.payload.tell()
                    job.payload.seek(0)
                except (OSError, IOError):
                    size = 0
            else:
                size = len(job.payload)
        else:
            size = os.stat(job.abspath).st_size

        if size > self._config.size_limit:
            return Finding(
                basename=job.basename, dirname=job.dirname, payload=job.payload,
                mimetype='Unknown', encoding='Unknown',
                err=PANHuntException(
                    f'File size {panutils.size_friendly(size=size)} over limit of '
                    f'{panutils.size_friendly(size=self._config.size_limit)} for file "{job.basename}"'
                )
            )  # type: ignore

        mime_type, encoding, error = panutils.get_mimetype(path=job.abspath, payload=job.payload)

        if error:
            return Finding(
                basename=job.basename, dirname=job.dirname, payload=job.payload,
                mimetype=mime_type, encoding=encoding, err=error
            )

        archive_type: Optional[type[Archive]] = ArchiveFactory.get_archive(
            mime_type=mime_type,
            extension=panutils.get_ext(job.basename)
        )

        if archive_type is not None:
            archive = archive_type(path=job.abspath, payload=job.payload)
            try:
                children, e = archive.get_children()
                if e:
                    return Finding(
                        basename=job.basename, dirname=job.dirname, payload=job.payload,
                        mimetype=mime_type, encoding=encoding, err=e
                    )  # type: ignore
                for child in children:
                    self._buffer.enqueue(child)
                return None
            except Exception as ex:
                return Finding(
                    basename=job.basename, dirname=job.dirname, payload=job.payload,
                    mimetype=mime_type, encoding=encoding, err=ex
                )  # type: ignore

        return self._scan_file(job, mime_type, encoding)

    def _scan_file(self, job: Job, mimetype: str, encoding: str) -> Optional[Finding]:
        scanner_instance = self._scanner_factory.get_scanner(
            mime_type=mimetype,
            extension=panutils.get_ext(job.basename)
        )
        if not scanner_instance:
            return None

        finding = None
        try:
            matches: list[PAN] = scanner_instance.scan(job=job, encoding=encoding)
            if matches:
                finding = Finding(
                    basename=job.basename, dirname=job.dirname, payload=job.payload,
                    mimetype=mimetype, encoding=encoding
                )
                finding.matches = matches
        except Exception as ex:
            finding = Finding(
                basename=job.basename, dirname=job.dirname, payload=job.payload,
                mimetype=mimetype, encoding=encoding, err=ex
            )  # type: ignore
        finally:
            return finding
