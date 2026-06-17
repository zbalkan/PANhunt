"""Tests for Dispatcher multi-worker pool."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from panhunt import enums
from panhunt.buffer import InMemoryJobBuffer
from panhunt.config import ScanConfiguration
from panhunt.dispatcher import Dispatcher
from panhunt.finding import Finding
from panhunt.job import Job


def _make_job(name: str = 'test.txt') -> Job:
    return Job(basename=name, dirname='/tmp')


def _make_config(worker_count: int = 1) -> ScanConfiguration:
    return ScanConfiguration.from_args(target_path='/tmp', quiet=True, worker_count=worker_count)


def _success_finding() -> Finding:
    f = MagicMock(spec=Finding)
    f.status = enums.ScanStatusEnum.Success
    return f


def _failure_finding() -> Finding:
    f = MagicMock(spec=Finding)
    f.status = enums.ScanStatusEnum.Failure
    return f


def _wait_for_finish(buffer: InMemoryJobBuffer, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not buffer.is_finished():
        if time.monotonic() > deadline:
            raise TimeoutError("Buffer did not finish within timeout")
        time.sleep(0.01)


class TestDispatcherLifecycle:
    def test_start_stop_join_empty_buffer(self):
        buffer = InMemoryJobBuffer()
        buffer.mark_input_complete()
        d = Dispatcher(buffer=buffer, config=_make_config())
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

    def test_join_completes_after_stop(self):
        buffer = InMemoryJobBuffer()
        buffer.mark_input_complete()
        d = Dispatcher(buffer=buffer, config=_make_config())
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()
        assert all(not t.is_alive() for t in d._threads)

    def test_multi_worker_all_threads_start(self):
        buffer = InMemoryJobBuffer()
        buffer.mark_input_complete()
        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=4))
        d.start()
        assert len(d._threads) == 4
        _wait_for_finish(buffer)
        d.stop()
        d.join()


class TestSingleWorkerCompatibility:
    def test_single_worker_processes_job(self):
        buffer = InMemoryJobBuffer()
        buffer.enqueue(_make_job('file.txt'))
        buffer.mark_input_complete()
        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=1))
        d._dispatch_job = MagicMock(return_value=_success_finding())
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()
        assert d._dispatch_job.call_count == 1
        assert len(d.get_findings()) == 1
        assert len(d.get_failures()) == 0

    def test_single_worker_collects_failure(self):
        buffer = InMemoryJobBuffer()
        buffer.enqueue(_make_job())
        buffer.mark_input_complete()
        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=1))
        d._dispatch_job = MagicMock(return_value=_failure_finding())
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()
        assert len(d.get_failures()) == 1
        assert len(d.get_findings()) == 0

    def test_single_worker_none_result_not_collected(self):
        buffer = InMemoryJobBuffer()
        buffer.enqueue(_make_job())
        buffer.mark_input_complete()
        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=1))
        d._dispatch_job = MagicMock(return_value=None)
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()
        assert len(d.get_findings()) == 0
        assert len(d.get_failures()) == 0


class TestMultiWorkerProcessing:
    def test_all_jobs_processed_no_duplicates(self):
        num_jobs = 50
        buffer = InMemoryJobBuffer()
        for i in range(num_jobs):
            buffer.enqueue(_make_job(f'file_{i}.txt'))
        buffer.mark_input_complete()

        processed = []
        lock = threading.Lock()

        def mock_dispatch(job):
            with lock:
                processed.append(job.basename)
            return None

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=4))
        d._dispatch_job = mock_dispatch
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert len(processed) == num_jobs
        assert len(set(processed)) == num_jobs

    def test_no_missed_jobs_under_load(self):
        num_jobs = 100
        buffer = InMemoryJobBuffer()
        job_names = {f'job_{i}.txt' for i in range(num_jobs)}
        for name in job_names:
            buffer.enqueue(_make_job(name))
        buffer.mark_input_complete()

        seen: set[str] = set()
        lock = threading.Lock()

        def mock_dispatch(job):
            with lock:
                seen.add(job.basename)
            return None

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=8))
        d._dispatch_job = mock_dispatch
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert seen == job_names

    def test_worker_count_greater_than_job_count(self):
        buffer = InMemoryJobBuffer()
        for i in range(3):
            buffer.enqueue(_make_job(f'file_{i}.txt'))
        buffer.mark_input_complete()

        call_count = [0]
        lock = threading.Lock()

        def mock_dispatch(job):
            with lock:
                call_count[0] += 1
            return None

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=10))
        d._dispatch_job = mock_dispatch
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert call_count[0] == 3


class TestConcurrentResultCollection:
    def test_concurrent_findings_count(self):
        num_jobs = 60
        buffer = InMemoryJobBuffer()
        for i in range(num_jobs):
            buffer.enqueue(_make_job(f'file_{i}.txt'))
        buffer.mark_input_complete()

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=4))
        d._dispatch_job = MagicMock(side_effect=lambda job: _success_finding())
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert len(d.get_findings()) == num_jobs

    def test_concurrent_failures_count(self):
        num_jobs = 40
        buffer = InMemoryJobBuffer()
        for i in range(num_jobs):
            buffer.enqueue(_make_job(f'file_{i}.txt'))
        buffer.mark_input_complete()

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=4))
        d._dispatch_job = MagicMock(side_effect=lambda job: _failure_finding())
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert len(d.get_failures()) == num_jobs
        assert len(d.get_findings()) == 0

    def test_get_findings_returns_snapshot(self):
        buffer = InMemoryJobBuffer()
        buffer.mark_input_complete()
        d = Dispatcher(buffer=buffer, config=_make_config())
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        snapshot1 = d.get_findings()
        snapshot2 = d.get_findings()
        assert snapshot1 is not snapshot2


class TestArchiveChildJobs:
    def test_archive_children_are_processed(self):
        buffer = InMemoryJobBuffer()
        buffer.enqueue(_make_job('archive.zip'))
        buffer.mark_input_complete()

        processed = []
        lock = threading.Lock()

        def mock_dispatch(job):
            with lock:
                processed.append(job.basename)
            if job.basename == 'archive.zip':
                buffer.enqueue(_make_job('child.txt'))
            return None

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=2))
        d._dispatch_job = mock_dispatch
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert 'archive.zip' in processed
        assert 'child.txt' in processed
        assert len(processed) == 2

    def test_archive_with_multiple_children(self):
        buffer = InMemoryJobBuffer()
        buffer.enqueue(_make_job('archive.zip'))
        buffer.mark_input_complete()

        child_names = [f'child_{i}.txt' for i in range(5)]
        processed = []
        lock = threading.Lock()

        def mock_dispatch(job):
            with lock:
                processed.append(job.basename)
            if job.basename == 'archive.zip':
                for name in child_names:
                    buffer.enqueue(_make_job(name))
            return None

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=2))
        d._dispatch_job = mock_dispatch
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert set(processed) == {'archive.zip'} | set(child_names)

    def test_nested_archive_children_processed(self):
        buffer = InMemoryJobBuffer()
        buffer.enqueue(_make_job('outer.zip'))
        buffer.mark_input_complete()

        processed = []
        lock = threading.Lock()

        def mock_dispatch(job):
            with lock:
                processed.append(job.basename)
            if job.basename == 'outer.zip':
                buffer.enqueue(_make_job('inner.zip'))
            elif job.basename == 'inner.zip':
                buffer.enqueue(_make_job('leaf.txt'))
            return None

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=2))
        d._dispatch_job = mock_dispatch
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert set(processed) == {'outer.zip', 'inner.zip', 'leaf.txt'}

    def test_invalid_zip_magic_falls_back_without_failure(self, tmp_path: Path):
        fake_zip = tmp_path / 'fake.zip'
        fake_zip.write_bytes(b'PK\x03\x04not a complete zip file')

        buffer = InMemoryJobBuffer()
        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=1))
        job = Job(basename=fake_zip.name, dirname=str(tmp_path))

        with patch('panhunt.dispatcher.panutils.get_mimetype', return_value=('application/zip', 'binary', None)):
            result = d._dispatch_job(job)

        assert result is None
        assert buffer.dequeue(timeout=0) is None


class TestWorkerResilience:
    def test_unhandled_exception_does_not_kill_worker(self):
        buffer = InMemoryJobBuffer()
        buffer.enqueue(_make_job('crash.txt'))
        buffer.enqueue(_make_job('ok.txt'))
        buffer.mark_input_complete()

        call_count = [0]
        lock = threading.Lock()

        def mock_dispatch(job):
            with lock:
                call_count[0] += 1
            if job.basename == 'crash.txt':
                raise FileNotFoundError('file vanished')
            return None

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=1))
        d._dispatch_job = mock_dispatch
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        assert call_count[0] == 2
        assert len(d.get_failures()) == 1
        assert buffer.is_finished()

    def test_exception_records_failure_finding(self):
        buffer = InMemoryJobBuffer()
        buffer.enqueue(_make_job('bad.txt'))
        buffer.mark_input_complete()

        def mock_dispatch(job):
            raise PermissionError('access denied')

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=1))
        d._dispatch_job = mock_dispatch
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        failures = d.get_failures()
        assert len(failures) == 1
        assert failures[0].status == enums.ScanStatusEnum.Failure
        assert any('access denied' in error for error in failures[0].errors)


class TestShutdownBehavior:

    def test_join_timeout_is_total_not_per_thread(self, monkeypatch):
        d = Dispatcher(buffer=InMemoryJobBuffer(), config=_make_config(worker_count=3))
        calls = []

        class SlowThread:
            def join(self, timeout=None):
                calls.append(timeout)

        times = iter([0.0, 1.0, 2.0, 3.0])
        monkeypatch.setattr('panhunt.dispatcher.time.monotonic', lambda: next(times))
        d._threads = [SlowThread(), SlowThread(), SlowThread()]

        d.join(timeout=2.5)

        assert calls == [1.5, 0.5, 0.0]

    def test_stop_signals_workers_to_exit(self):
        buffer = InMemoryJobBuffer()
        buffer.mark_input_complete()
        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=2))
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()
        assert all(not t.is_alive() for t in d._threads)

    def test_complete_job_called_exactly_once_per_job(self):
        num_jobs = 20
        buffer = InMemoryJobBuffer()
        for i in range(num_jobs):
            buffer.enqueue(_make_job(f'file_{i}.txt'))
        buffer.mark_input_complete()

        d = Dispatcher(buffer=buffer, config=_make_config(worker_count=4))
        d._dispatch_job = MagicMock(return_value=None)
        d.start()
        _wait_for_finish(buffer)
        d.stop()
        d.join()

        # is_finished() only returns True when all jobs are completed exactly once
        assert buffer.is_finished()
