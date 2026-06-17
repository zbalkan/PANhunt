"""Behavior tests for byte-limit stream helpers."""

import io

import pytest

from panhunt.exceptions import PANHuntException
from panhunt.limitedio import LimitedReader, read_limited, spool_limited
from panhunt.scancontext import ScanContext, ScanLimits


def test_limited_reader_returns_data_up_to_limit_and_then_reports_overrun():
    reader = LimitedReader(io.BytesIO(b'abcdef'), limit=5, name='payload.bin')

    assert reader.read(3) == b'abc'

    with pytest.raises(PANHuntException) as excinfo:
        reader.read()

    assert 'Read limit exceeded for "payload.bin"' in str(excinfo.value)


def test_limited_reader_updates_scan_budget_as_callers_consume_stream():
    context = ScanContext.root(
        logical_path='archive.zip!/card.txt',
        limits=ScanLimits(max_depth=3, max_child_jobs=3, max_total_expanded_bytes=10),
    )
    reader = LimitedReader(io.BytesIO(b'4111111111111111'), limit=20, context=context)

    assert reader.read(8) == b'41111111'

    with pytest.raises(PANHuntException) as excinfo:
        reader.read()

    assert 'expanded-byte limit exceeded for "archive.zip!/card.txt"' in str(excinfo.value)
    assert context.budget.expanded_bytes == 8


def test_read_limited_returns_all_bytes_for_payload_within_limit():
    payload = read_limited(io.BytesIO(b'Payment 4111111111111111'), limit=30, chunk_size=4)

    assert payload == b'Payment 4111111111111111'


def test_read_limited_reports_when_stream_exceeds_limit():
    with pytest.raises(PANHuntException) as excinfo:
        read_limited(io.BytesIO(b'abcdef'), limit=5, chunk_size=2)

    assert 'Read limit exceeded' in str(excinfo.value)


def test_spool_limited_rewinds_payload_and_reports_size():
    payload, size = spool_limited(io.BytesIO(b'Payment 4111111111111111'), limit=30, spool_threshold=4)

    try:
        assert size == 24
        assert payload.read() == b'Payment 4111111111111111'
    finally:
        payload.close()


def test_spool_limited_closes_partial_payload_when_limit_is_exceeded():
    with pytest.raises(PANHuntException) as excinfo:
        spool_limited(io.BytesIO(b'abcdef'), limit=5, chunk_size=2)

    assert 'Read limit exceeded' in str(excinfo.value)
