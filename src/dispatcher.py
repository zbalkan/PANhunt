import threading
import time
from typing import Optional

import mappings
import panutils
from archive import Archive
from doc import Document
from job import Job, JobQueue
from scanner import ScannerBase


class Dispatcher:
    def __init__(self, excluded_pans_list, patterns) -> None:
        self.excluded_pans_list = excluded_pans_list
        self.patterns = patterns
        self._stop_flag = False
        self.results: list[Document] = []

    def start(self) -> None:
        """Start the dispatcher loop in a separate thread."""
        self._stop_flag = False
        dispatch_thread = threading.Thread(
            target=self._run_dispatch_loop, daemon=True)
        dispatch_thread.start()

    def stop(self) -> None:
        """Stop the dispatcher loop."""
        self._stop_flag = True

    def _run_dispatch_loop(self) -> None:
        job_queue = JobQueue()
        while not self._stop_flag and not job_queue.is_finished():
            if job_queue.has_jobs():
                job = job_queue.dequeue()
                if job:
                    try:
                        res = self._dispatch_job(job)
                        if res is not None:
                            self.results.append(res)
                    finally:
                        # Mark the job as completed
                        job_queue.complete_job()
            else:
                time.sleep(0.1)

    def _dispatch_job(self, job: Job) -> Optional[Document]:
        # Dispatch job logic goes here
        mime_type, encoding, error = panutils.get_mimetype(
            path=job.path, payload=job.payload)

        if error:
            return Document(filename=job.filename, file_dir=job.file_dir, payload=job.payload, mimetype=mime_type, encoding=encoding, err=error)

        archive_type: Optional[type[Archive]] = mappings.get_archive_by_file(
            mime_type=mime_type,
            extension=panutils.get_ext(job.filename)
        )

        if archive_type is not None:
            # It's an archive, extract children and re-enqueue them as jobs
            archive = archive_type(path=job.path, payload=job.payload)
            children: list[Job] = archive.get_children()
            for child in children:
                JobQueue().enqueue(child)
            return None
        else:
            # Scan the file
            return self._scan_file(job, mime_type, encoding)

    def _scan_file(self, job: Job,
                   mimetype: str, encoding: str) -> None | Document:
        # Scanning logic
        scanner: Optional[type[ScannerBase]] = mappings.get_scanner_by_file(
            mime_type=mimetype,
            extension=panutils.get_ext(job.filename)
        )
        if not scanner:
            return None

        scanner_instance = scanner(patterns=self.patterns)
        if job.payload is not None:
            scanner_instance.payload = job.payload
        else:
            scanner_instance.filename = job.path

        scannable_file = None
        try:
            matches = scanner_instance.scan(self.excluded_pans_list)
            if matches and len(matches) > 0:
                scannable_file = Document(
                    filename=job.filename, file_dir=job.file_dir, payload=job.payload, mimetype=mimetype, encoding=encoding)
                scannable_file.matches = matches
        except Exception as ex:
            scannable_file = Document(
                filename=job.filename, file_dir=job.file_dir, payload=job.payload, mimetype=mimetype, encoding=encoding)
            scannable_file.set_error(str(ex))
        finally:
            return scannable_file
