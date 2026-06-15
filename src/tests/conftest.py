"""Shared fixtures for the PANhunt test suite."""

import os
import tempfile
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock

import pytest

from buffer import InMemoryJobBuffer, JobBuffer
from config import ScanConfiguration
from finding import Finding
from models import ScanResult


# ---------------------------------------------------------------------------
# Configuration fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> ScanConfiguration:
    """Minimal ScanConfiguration pointing at /tmp."""
    return ScanConfiguration.from_args(search_dir='/tmp', quiet=True)


@pytest.fixture
def config_with_exclusion() -> ScanConfiguration:
    """Config that excludes a known test PAN."""
    return ScanConfiguration.from_args(
        search_dir='/tmp',
        excluded_pans_string='4111111111111111',
        quiet=True,
    )


# ---------------------------------------------------------------------------
# Buffer fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def buffer() -> InMemoryJobBuffer:
    return InMemoryJobBuffer()


@pytest.fixture
def mock_buffer() -> MagicMock:
    b = MagicMock(spec=JobBuffer)
    b.is_finished.return_value = True
    b.has_jobs.return_value = False
    return b


# ---------------------------------------------------------------------------
# Temporary file fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_text_file() -> Generator[str, None, None]:
    """A real plain-text .txt file the scanner can open."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False, encoding='utf-8'
    ) as f:
        f.write('No card numbers here.\n')
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def tmp_pan_file() -> Generator[str, None, None]:
    """A plain-text file that contains a valid Visa PAN."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False, encoding='utf-8'
    ) as f:
        # 4111111111111111 is the canonical Visa test card
        f.write('Payment reference: 4111 1111 1111 1111\n')
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def tmp_dir() -> Generator[str, None, None]:
    """A temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


# ---------------------------------------------------------------------------
# Result / Finding fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_result(config: ScanConfiguration) -> ScanResult:
    now = datetime.now()
    return ScanResult(
        matched_files=[],
        interesting_files=[],
        start_time=now,
        end_time=now,
        config=config,
    )


@pytest.fixture
def finding_no_error(tmp_text_file: str) -> Finding:
    return Finding(
        basename=os.path.basename(tmp_text_file),
        dirname=os.path.dirname(tmp_text_file),
    )
