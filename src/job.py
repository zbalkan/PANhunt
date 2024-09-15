import os
from queue import Queue
from threading import Lock
from typing import Optional


class Job:

    basename: str
    dirname: str
    payload: Optional[bytes]
    abspath: str

    def __init__(self, basename: str, dirname: str, payload: Optional[bytes] = None) -> None:
        self.basename = basename
        self.dirname = dirname
        self.payload = payload
        self.abspath = os.path.join(self.dirname, self.basename)


class JobQueue:
    _instance: Optional['JobQueue'] = None
    _lock = Lock()

    _job_queue: Queue[Job]  # Queue to hold jobs
    _jobs_enqueued: int = 0  # Total jobs added to the queue
    _jobs_processed: int = 0  # Total jobs processed (completed)
    _jobs_in_progress: int = 0  # Jobs that are currently being processed
    _finished: bool = False    # Flag to indicate no more initial jobs will be added

    def __new__(cls) -> "JobQueue":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(JobQueue, cls).__new__(cls)
                    cls._instance._job_queue = Queue()
        return cls._instance

    def enqueue(self, job: Job) -> None:
        """Push a job onto the queue and increment the enqueued job count."""
        with self._lock:
            self._job_queue.put(job)
            self._jobs_enqueued += 1  # Increment job count

    def dequeue(self) -> Optional[Job]:
        """Pop a job from the queue and increment the in-progress job count."""
        if self._job_queue:
            job = self._job_queue.get()
            with self._lock:
                self._jobs_in_progress += 1  # Increment in-progress job count
            return job
        return None

    def complete_job(self) -> None:
        """Decrement the in-progress job count and increment the processed job count."""
        with self._lock:
            self._jobs_in_progress -= 1  # Job has finished processing
            self._jobs_processed += 1  # Increment processed job count

    def has_jobs(self) -> bool:
        """Check if there are jobs in the queue."""
        return not self._job_queue.empty()

    def mark_input_complete(self) -> None:
        """Signal that no more initial jobs will be added."""
        with self._lock:
            self._finished = True

    def is_finished(self) -> bool:
        """Check if all jobs have been processed and no more jobs are expected."""
        with self._lock:
            return (
                self._finished                # No more initial jobs will be added
                and self._jobs_enqueued == self._jobs_processed  # All enqueued jobs are processed
                and self._jobs_in_progress == 0  # No jobs are currently being processed
            )
