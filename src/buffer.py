import threading
import time
from abc import ABC, abstractmethod
from io import IOBase
from queue import Empty, Queue
from typing import Optional

import psutil

from constants import MEMORY_CHECK_TIMEOUT_SECONDS
from job import Job


class JobBuffer(ABC):
    """Abstract buffer decoupling job producers (scanners/hunter) from the consumer (dispatcher)."""

    @abstractmethod
    def enqueue(self, job: Job) -> None:
        pass

    @abstractmethod
    def dequeue(self, timeout: float = 0.1) -> Optional[Job]:
        pass

    @abstractmethod
    def complete_job(self) -> None:
        pass

    @abstractmethod
    def mark_input_complete(self) -> None:
        pass

    @abstractmethod
    def is_finished(self) -> bool:
        pass

    @abstractmethod
    def has_jobs(self) -> bool:
        pass


class InMemoryJobBuffer(JobBuffer):
    """Thread-safe in-memory job buffer."""

    def __init__(self) -> None:
        self._job_queue: Queue[Job] = Queue()
        self._jobs_enqueued: int = 0
        self._jobs_processed: int = 0
        self._jobs_in_progress: int = 0
        self._finished: bool = False
        self._lock = threading.Lock()

    def enqueue(self, job: Job) -> None:
        self._ensure_memory_ready(job)
        with self._lock:
            self._job_queue.put(job)
            self._jobs_enqueued += 1

    def dequeue(self, timeout: float = 0.1) -> Optional[Job]:
        try:
            job = self._job_queue.get(timeout=timeout)
            # self._lock is intentional: Queue's internal lock guards only the
            # queue itself, not _jobs_in_progress, which is also read/written
            # by complete_job() and is_finished() under the same lock.
            with self._lock:
                self._jobs_in_progress += 1
            return job
        except Empty:
            return None

    def complete_job(self) -> None:
        with self._lock:
            self._jobs_in_progress -= 1
            self._jobs_processed += 1

    def mark_input_complete(self) -> None:
        with self._lock:
            self._finished = True

    def is_finished(self) -> bool:
        with self._lock:
            return (
                self._finished
                and self._jobs_enqueued == self._jobs_processed
                and self._jobs_in_progress == 0
            )

    def has_jobs(self) -> bool:
        return not self._job_queue.empty()

    def _ensure_memory_ready(self, job: Job) -> None:
        if job.payload is None or isinstance(job.payload, IOBase):
            return

        size = len(job.payload)
        if size >= psutil.virtual_memory().total:
            raise MemoryError(f"Insufficient memory to process job: {job.abspath}")

        sleep_time = 0.0
        while size >= psutil.virtual_memory().available / 2:
            sleep_time += 0.1
            if sleep_time >= MEMORY_CHECK_TIMEOUT_SECONDS:
                raise MemoryError(f"Insufficient memory to process job: {job.abspath}")
            time.sleep(0.1)
