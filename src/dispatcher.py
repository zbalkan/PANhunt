import os
import threading
import time
from typing import Optional

from PAN import PAN
from config import PANHuntConfiguration
import mappings
import panutils
from archive import Archive
from finding import Finding
from job import Job, JobQueue
from scanner import ScannerBase


class Dispatcher:
    # excluded_pans_list: list[str]
    results: list[Finding]
    size_limit: int
    _stop_flag: bool

    def __init__(self) -> None:
        # self.excluded_pans_list = PANHuntConfiguration().excluded_pans
        self.size_limit = PANHuntConfiguration().size_limit
        self._stop_flag = False
        self.results = []

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
                job: Optional[Job] = job_queue.dequeue()
                if job:
                    try:
                        res: Optional[Finding] = self._dispatch_job(job)
                        if res is not None:
                            self.results.append(res)
                    finally:
                        # Mark the job as completed
                        job_queue.complete_job()
            else:
                time.sleep(0.1)

    def _dispatch_job(self, job: Job) -> Optional[Finding]:
        # Dispatch job logic goes here
        # First, check the size of the job
        size: int
        if job.payload is not None:
            size = len(job.payload)
        else:
            size = os.stat(job.path).st_size
        if size > self.size_limit:
            doc = Finding(filename=job.filename, file_dir=job.file_dir,
                          payload=job.payload, mimetype='Unknown', encoding='Unknown', err=None)
            doc.set_error(
                f'File size {panutils.size_friendly(size=size)} over limit of {panutils.size_friendly(size=self.size_limit)} for checking for file \"{job.filename}\"')
            return doc

        mime_type, encoding, error = panutils.get_mimetype(
            path=job.path, payload=job.payload)

        if error:
            return Finding(filename=job.filename, file_dir=job.file_dir, payload=job.payload, mimetype=mime_type, encoding=encoding, err=error)

        archive_type: Optional[type[Archive]] = mappings.get_archive_by_file(
            mime_type=mime_type,
            extension=panutils.get_ext(job.filename)
        )

        if archive_type is not None:
            # It's an archive, extract children and re-enqueue them as jobs
            archive = archive_type(path=job.path, payload=job.payload)
            try:
                children: list[Job] = archive.get_children()
                for child in children:
                    JobQueue().enqueue(child)
                return None
            except Exception as ex:
                doc = Finding(filename=job.filename, file_dir=job.file_dir,
                              payload=job.payload, mimetype=mime_type, encoding=encoding, err=None)
                doc.set_error(str(ex))
                return doc
        else:
            # Scan the file
            return self._scan_file(job, mime_type, encoding)

    def _scan_file(self, job: Job,
                   mimetype: str, encoding: str) -> None | Finding:
        # Scanning logic
        scanner: Optional[type[ScannerBase]] = mappings.get_scanner_by_file(
            mime_type=mimetype,
            extension=panutils.get_ext(job.filename)
        )
        if not scanner:
            return None

        scanner_instance = scanner()

        doc = None
        try:
            matches: list[PAN] = scanner_instance.scan(
                job=job, encoding=encoding)
            if matches and len(matches) > 0:
                doc = Finding(
                    filename=job.filename, file_dir=job.file_dir, payload=job.payload, mimetype=mimetype, encoding=encoding)
                doc.matches = matches
        except Exception as ex:
            doc = Finding(
                filename=job.filename, file_dir=job.file_dir, payload=job.payload, mimetype=mimetype, encoding=encoding)
            doc.set_error(str(ex))
        finally:
            return doc
