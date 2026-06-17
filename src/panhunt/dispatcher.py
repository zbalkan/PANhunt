from __future__ import annotations

import logging
import os
import threading
from typing import IO, Optional, cast

from . import enums, panutils
from .archive import Archive, ZipArchive
from .buffer import JobBuffer
from .config import ScanConfiguration
from .exceptions import PANHuntException
from .factory import ArchiveFactory, ScannerFactory
from .finding import Finding
from .job import Job
from .limitedio import LimitedReader
from .pan import PAN
from .scancontext import ResourceBudget, ScanContext, ScanLimits


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
        self._scan_limits = ScanLimits(
            max_depth=self._config.max_scan_depth,
            max_child_jobs=self._config.max_child_jobs,
            max_total_expanded_bytes=self._config.max_total_expanded_bytes,
            max_attachment_size=self._config.max_attachment_size,
            max_attachments_per_message=self._config.max_attachments_per_message,
            max_total_attachment_bytes=self._config.max_total_attachment_bytes,
            max_path_length=self._config.max_archive_path_length
        )
        self._resource_budget = ResourceBudget(self._scan_limits)
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
                if job.payload and panutils.is_file_like(job.payload):
                    close = getattr(job.payload, 'close', None)
                    if callable(close):
                        try:
                            close()
                        except Exception as e:
                            logging.warning(f"Failed to close payload for {job.abspath}: {e}")
                job.payload = None
                job = None
                self._buffer.complete_job()

    def _dispatch_job(self, job: Job) -> Optional[Finding]:
        logging.info(f"Processing job: {job.abspath}")
        if job.context is None:
            job.context = ScanContext.root(
                logical_path=job.abspath,
                limits=self._scan_limits,
                budget=self._resource_budget
            )

        if job.payload is not None:
            if isinstance(job.payload, LimitedReader):
                size = 0
            elif isinstance(job.payload, bytes):
                size = len(job.payload)
            elif panutils.is_file_like(job.payload):
                seek = getattr(job.payload, 'seek', None)
                tell = getattr(job.payload, 'tell', None)
                if callable(seek) and callable(tell):
                    try:
                        seek(0, 2)
                        size = cast(int, tell())
                        seek(0)
                    except (OSError, IOError):
                        size = 0
                else:
                    size = 0
            else:
                size = 0
        else:
            size = os.stat(job.abspath).st_size

        if size > self._config.size_limit:
            return Finding(
                basename=job.basename, dirname=job.dirname, payload=job.payload,
                mimetype='Unknown', encoding='Unknown',
                err=PANHuntException(
                    f'File size {panutils.size_friendly(size=size)} over limit of '
                    f'{panutils.size_friendly(size=self._config.size_limit)} for file "{job.basename}"'
                ),
                context=job.context
            )  # type: ignore

        mime_type, encoding, error = panutils.get_mimetype(path=job.abspath, payload=job.payload)

        if error:
            return Finding(
                basename=job.basename, dirname=job.dirname, payload=job.payload,
                mimetype=mime_type, encoding=encoding, err=error, context=job.context
            )

        archive_type: Optional[type[Archive]] = ArchiveFactory.get_archive(
            mime_type=mime_type,
            extension=panutils.get_ext(job.basename)
        )

        if archive_type is not None:
            if (issubclass(archive_type, ZipArchive)
                    and not panutils.is_valid_zip(path=job.abspath, payload=job.payload)):
                logging.warning(f"Skipping ZIP parser for invalid ZIP container: {job.abspath}")
                return self._scan_file(job, mime_type, encoding)

            archive_name = archive_type.__name__.replace('Archive', '').lower()
            if self._config.allowed_archive_types and archive_name not in self._config.allowed_archive_types:
                return Finding(
                    basename=job.basename, dirname=job.dirname, payload=job.payload,
                    mimetype=mime_type, encoding=encoding,
                    err=PANHuntException(f'Archive type "{archive_name}" is not allowed by policy'),
                    context=job.context
                )  # type: ignore
            if archive_name in self._config.denied_archive_types:
                return Finding(
                    basename=job.basename, dirname=job.dirname, payload=job.payload,
                    mimetype=mime_type, encoding=encoding,
                    err=PANHuntException(f'Archive type "{archive_name}" is denied by policy'),
                    context=job.context
                )  # type: ignore
            archive = archive_type(
                path=job.abspath,
                payload=cast(IO[bytes], job.payload) if job.payload is not None and not isinstance(job.payload, bytes) else job.payload,
                size_limit=self._config.size_limit,
                context=job.context,
                max_members=self._config.max_archive_members,
                compression_ratio_limit=self._config.max_archive_compression_ratio,
                max_path_length=self._config.max_archive_path_length,
                spool_threshold=self._config.archive_spool_threshold
            )
            try:
                children, e = archive.get_children()
                if e:
                    return Finding(
                        basename=job.basename, dirname=job.dirname, payload=job.payload,
                        mimetype=mime_type, encoding=encoding, err=e, context=job.context
                    )  # type: ignore
                for child in children:
                    self._buffer.enqueue(child)
                return None
            except Exception as ex:
                return Finding(
                    basename=job.basename, dirname=job.dirname, payload=job.payload,
                    mimetype=mime_type, encoding=encoding, err=ex, context=job.context
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
                    mimetype=mimetype, encoding=encoding, context=job.context
                )
                finding.matches = matches
        except Exception as ex:
            finding = Finding(
                basename=job.basename, dirname=job.dirname, payload=job.payload,
                mimetype=mimetype, encoding=encoding, err=ex, context=job.context
            )  # type: ignore
        return finding
