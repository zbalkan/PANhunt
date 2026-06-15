"""Tests for InMemoryJobBuffer."""

import threading
import time

import pytest

from buffer import InMemoryJobBuffer
from job import Job


def _make_job(name: str = 'test.txt') -> Job:
    return Job(basename=name, dirname='/tmp')


class TestEnqueueDequeue:
    def test_enqueue_increases_count(self):
        b = InMemoryJobBuffer()
        b.enqueue(_make_job())
        assert b.has_jobs()

    def test_dequeue_returns_job(self):
        b = InMemoryJobBuffer()
        job = _make_job()
        b.enqueue(job)
        out = b.dequeue()
        assert out is not None
        assert out.basename == 'test.txt'

    def test_empty_buffer_has_no_jobs(self):
        b = InMemoryJobBuffer()
        assert not b.has_jobs()

    def test_fifo_order(self):
        b = InMemoryJobBuffer()
        b.enqueue(_make_job('a.txt'))
        b.enqueue(_make_job('b.txt'))
        assert b.dequeue().basename == 'a.txt'
        assert b.dequeue().basename == 'b.txt'


class TestLifecycle:
    def test_not_finished_when_jobs_pending(self):
        b = InMemoryJobBuffer()
        b.enqueue(_make_job())
        b.mark_input_complete()
        assert not b.is_finished()

    def test_finished_when_all_processed(self):
        b = InMemoryJobBuffer()
        b.enqueue(_make_job())
        b.mark_input_complete()
        b.dequeue()
        b.complete_job()
        assert b.is_finished()

    def test_not_finished_without_mark_input_complete(self):
        b = InMemoryJobBuffer()
        assert not b.is_finished()

    def test_finished_with_no_jobs(self):
        b = InMemoryJobBuffer()
        b.mark_input_complete()
        assert b.is_finished()


class TestThreadSafety:
    def test_concurrent_enqueue(self):
        b = InMemoryJobBuffer()
        errors = []

        def producer():
            try:
                for i in range(50):
                    b.enqueue(_make_job(f'file_{i}.txt'))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=producer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        count = 0
        while b.has_jobs():
            b.dequeue()
            b.complete_job()
            count += 1
        assert count == 200


class TestMemoryCheck:
    def test_large_payload_raises_memory_error(self):
        from unittest.mock import MagicMock, patch
        import psutil

        b = InMemoryJobBuffer()
        payload = b'\x00' * 1024  # 1 KB — small, but we mock totals so it looks huge

        mock_vm = MagicMock()
        mock_vm.total = 512          # 512 bytes total
        mock_vm.free = 256           # 256 bytes free

        with patch('psutil.virtual_memory', return_value=mock_vm):
            job = Job(basename='huge.bin', dirname='/tmp', payload=payload)
            with pytest.raises(MemoryError):
                b.enqueue(job)

    def test_none_payload_skips_memory_check(self):
        b = InMemoryJobBuffer()
        job = Job(basename='file.txt', dirname='/tmp', payload=None)
        b.enqueue(job)
        assert b.has_jobs()
