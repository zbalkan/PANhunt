"""Tests for Hunter."""

import os
from unittest.mock import MagicMock, call, patch

import pytest

from config import ScanConfiguration
from dispatcher import Dispatcher
from finding import Finding
from hunter import Hunter
from job import Job


@pytest.fixture
def mock_dispatcher():
    d = MagicMock(spec=Dispatcher)
    d.findings = []
    d.failures = []
    return d


class TestHuntSingleFile:
    def test_enqueues_file_path_job(self, mock_dispatcher, mock_buffer, tmp_text_file):
        config = ScanConfiguration.from_args(file_path=tmp_text_file, quiet=True)
        mock_buffer.is_finished.return_value = True
        h = Hunter(dispatcher=mock_dispatcher, buffer=mock_buffer)
        h.hunt(config)
        mock_buffer.enqueue.assert_called_once()
        job: Job = mock_buffer.enqueue.call_args[0][0]
        assert job.basename == os.path.basename(tmp_text_file)

    def test_marks_input_complete(self, mock_dispatcher, mock_buffer, tmp_text_file):
        config = ScanConfiguration.from_args(file_path=tmp_text_file, quiet=True)
        mock_buffer.is_finished.return_value = True
        h = Hunter(dispatcher=mock_dispatcher, buffer=mock_buffer)
        h.hunt(config)
        mock_buffer.mark_input_complete.assert_called_once()


class TestHuntDirectory:
    def test_enqueues_files_from_directory(self, mock_dispatcher, mock_buffer, tmp_dir):
        open(os.path.join(tmp_dir, 'a.txt'), 'w').close()
        open(os.path.join(tmp_dir, 'b.txt'), 'w').close()
        config = ScanConfiguration.from_args(search_dir=tmp_dir, quiet=True)
        mock_buffer.is_finished.return_value = True
        h = Hunter(dispatcher=mock_dispatcher, buffer=mock_buffer)
        h.hunt(config)
        assert mock_buffer.enqueue.call_count == 2

    def test_excludes_configured_directories(self, mock_dispatcher, mock_buffer, tmp_dir):
        # Hunter skips files in SUBDIRECTORIES of excluded dirs (pattern: excluded/.*).
        # Files directly inside the excluded dir itself are still visited.
        excl = os.path.join(tmp_dir, 'excluded')
        nested = os.path.join(excl, 'nested')
        os.makedirs(nested)
        open(os.path.join(nested, 'file.txt'), 'w').close()
        config = ScanConfiguration.from_args(
            search_dir=tmp_dir,
            excluded_directories_string=excl,
            quiet=True,
        )
        mock_buffer.is_finished.return_value = True
        h = Hunter(dispatcher=mock_dispatcher, buffer=mock_buffer)
        h.hunt(config)
        mock_buffer.enqueue.assert_not_called()


class TestHuntResults:
    def test_returns_findings_and_failures(self, mock_dispatcher, mock_buffer, tmp_dir):
        finding = MagicMock(spec=Finding)
        failure = MagicMock(spec=Finding)
        mock_dispatcher.findings = [finding]
        mock_dispatcher.failures = [failure]
        config = ScanConfiguration.from_args(search_dir=tmp_dir, quiet=True)
        mock_buffer.is_finished.return_value = True
        h = Hunter(dispatcher=mock_dispatcher, buffer=mock_buffer)
        findings, failures = h.hunt(config)
        assert findings == [finding]
        assert failures == [failure]
