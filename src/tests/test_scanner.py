"""Tests for PlainTextFileScanner (and shared ScannerBase wiring)."""

import io
import os

import pytest

from panhunt.finder import PanFinder
from panhunt.job import Job
from panhunt.scanner import PlainTextFileScanner


@pytest.fixture
def scanner(mock_buffer, config):
    return PlainTextFileScanner(buffer=mock_buffer, config=config)


@pytest.fixture
def scanner_with_exclusion(mock_buffer):
    # The regex extracts '4111 1111 1111 1111' (with spaces); exclusion must match exactly
    from panhunt.config import ScanConfiguration
    cfg = ScanConfiguration.from_args(
        target_path='/tmp',
        excluded_pans_string='4111 1111 1111 1111',
        quiet=True,
    )
    return PlainTextFileScanner(buffer=mock_buffer, config=cfg)


class TestScanFile:
    def test_no_pan_in_clean_file(self, scanner, tmp_text_file):
        job = Job(basename=os.path.basename(tmp_text_file), dirname=os.path.dirname(tmp_text_file))
        result = scanner.scan(job)
        assert result == []

    def test_finds_visa_pan_in_file(self, scanner, tmp_pan_file):
        job = Job(basename=os.path.basename(tmp_pan_file), dirname=os.path.dirname(tmp_pan_file))
        result = scanner.scan(job)
        assert len(result) == 1
        assert 'Visa' in str(result[0])

    def test_excluded_pan_not_returned(self, scanner_with_exclusion, tmp_pan_file):
        job = Job(basename=os.path.basename(tmp_pan_file), dirname=os.path.dirname(tmp_pan_file))
        result = scanner_with_exclusion.scan(job)
        assert result == []


class TestScanBytes:
    def test_finds_pan_in_bytes_payload(self, scanner, mock_buffer):
        payload = b'Card: 4111111111111111\n'
        job = Job(basename='inline.txt', dirname='/tmp', payload=payload)
        result = scanner.scan(job)
        assert len(result) == 1

    def test_no_pan_in_bytes_payload(self, scanner, mock_buffer):
        payload = b'No card here\n'
        job = Job(basename='inline.txt', dirname='/tmp', payload=payload)
        result = scanner.scan(job)
        assert result == []

    def test_binary_encoding_falls_back_to_utf8(self, scanner):
        payload = b'4111111111111111'
        job = Job(basename='bin.bin', dirname='/tmp', payload=payload)
        result = scanner.scan(job, encoding='binary')
        assert len(result) == 1


class TestScanStream:
    def test_finds_pan_in_stream(self, scanner):
        content = 'Ref: 4111111111111111\n'
        stream = io.StringIO(content)
        job = Job(basename='stream.txt', dirname='/tmp', payload=stream)
        result = scanner.scan(job)
        assert len(result) == 1

    def test_non_seekable_stream(self, scanner):
        class NonSeekable(io.RawIOBase):
            def __init__(self, data: bytes):
                self._data = data
                self._pos = 0

            def readinto(self, b):
                n = len(b)
                chunk = self._data[self._pos:self._pos + n]
                b[:len(chunk)] = chunk
                self._pos += len(chunk)
                return len(chunk)

            def readable(self):
                return True

            def seekable(self):
                return False

            def read(self, n=-1):
                if n == -1:
                    chunk = self._data[self._pos:]
                else:
                    chunk = self._data[self._pos:self._pos + n]
                self._pos += len(chunk)
                return chunk

        stream = NonSeekable(b'4111111111111111\n')
        job = Job(basename='noseek.txt', dirname='/tmp', payload=stream)
        result = scanner.scan(job)
        assert len(result) == 1


    def test_finds_pan_in_file_like_payload_without_iobase(self, scanner):
        class FileLikePayload:
            def __init__(self, data):
                self._data = data
                self._pos = 0

            def read(self, size=-1):
                if size == -1:
                    chunk = self._data[self._pos:]
                else:
                    chunk = self._data[self._pos:self._pos + size]
                self._pos += len(chunk)
                return chunk

            def seek(self, offset, whence=0):
                if whence == 0:
                    self._pos = offset
                elif whence == 1:
                    self._pos += offset
                elif whence == 2:
                    self._pos = len(self._data) + offset
                return self._pos

            def tell(self):
                return self._pos

        stream = FileLikePayload(b'Ref: 4111111111111111\n')
        job = Job(basename='stream.txt', dirname='/tmp', payload=stream)
        result = scanner.scan(job)
        assert len(result) == 1

    def test_empty_stream_returns_empty(self, scanner):
        stream = io.StringIO('')
        job = Job(basename='empty.txt', dirname='/tmp', payload=stream)
        result = scanner.scan(job)
        assert result == []


class TestPanFinderInjection:
    def test_custom_pan_finder_is_used(self, mock_buffer, config):
        custom_finder = PanFinder(config)
        scanner = PlainTextFileScanner(buffer=mock_buffer, config=config, pan_finder=custom_finder)
        assert scanner._pan_finder is custom_finder
