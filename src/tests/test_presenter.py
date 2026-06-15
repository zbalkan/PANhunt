"""Tests for CliPresenter."""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from panhunt.config import ScanConfiguration
from panhunt.models import ScanResult
from panhunt.presenter import CliPresenter, _write_file


def _make_result(config, matched=None, interesting=None):
    start = datetime(2024, 6, 1, 10, 0, 0)
    return ScanResult(
        matched_files=matched or [],
        interesting_files=interesting or [],
        start_time=start,
        end_time=start + timedelta(seconds=5),
        config=config,
    )


class TestWriteFile:
    def test_creates_file_with_content(self, tmp_dir):
        path = os.path.join(tmp_dir, 'out.txt')
        _write_file(path, 'hello')
        with open(path) as f:
            assert f.read() == 'hello'

    def test_creates_parent_directories(self, tmp_dir):
        path = os.path.join(tmp_dir, 'nested', 'deeply', 'out.txt')
        _write_file(path, 'world')
        assert os.path.exists(path)


class TestSaveText:
    def test_text_report_written(self, tmp_dir):
        config = ScanConfiguration.from_args(search_dir=tmp_dir, quiet=True)
        config.report_file = 'test_report.report'
        config.report_dir = tmp_dir
        result = _make_result(config)
        presenter = CliPresenter()
        presenter._save_text(result)
        path = config.get_report_path()
        assert os.path.exists(path)

    def test_text_report_contains_searched_dir(self, tmp_dir):
        config = ScanConfiguration.from_args(search_dir=tmp_dir, quiet=True)
        config.report_file = 'test_report2.report'
        config.report_dir = tmp_dir
        result = _make_result(config)
        presenter = CliPresenter()
        presenter._save_text(result)
        with open(config.get_report_path()) as f:
            content = f.read()
        assert tmp_dir in content


class TestSaveJson:
    def test_json_report_written_when_dir_set(self, tmp_dir):
        config = ScanConfiguration.from_args(search_dir=tmp_dir, json_dir=tmp_dir, quiet=True)
        config.json_file = 'test_report.json'
        result = _make_result(config)
        presenter = CliPresenter()
        presenter._save_json(result)
        path = config.get_json_path()
        assert path is not None
        assert os.path.exists(path)

    def test_json_content_is_valid(self, tmp_dir):
        config = ScanConfiguration.from_args(search_dir=tmp_dir, json_dir=tmp_dir, quiet=True)
        config.json_file = 'test_report2.json'
        result = _make_result(config)
        presenter = CliPresenter()
        presenter._save_json(result)
        with open(config.get_json_path()) as f:
            data = json.load(f)
        assert 'searched' in data

    def test_json_not_written_without_dir(self, tmp_dir):
        config = ScanConfiguration.from_args(search_dir=tmp_dir, quiet=True)
        result = _make_result(config)
        presenter = CliPresenter()
        with patch.object(presenter, '_report_gen') as mock_gen:
            presenter._save_json(result)
            mock_gen.generate_json.assert_not_called()


class TestShow:
    def test_show_quiet_skips_print(self, tmp_dir):
        config = ScanConfiguration.from_args(search_dir=tmp_dir, quiet=True)
        config.report_file = 'show_test.report'
        config.report_dir = tmp_dir
        result = _make_result(config)
        presenter = CliPresenter()
        with patch.object(presenter, '_print') as mock_print:
            presenter.show(result)
            mock_print.assert_not_called()

    def test_show_non_quiet_calls_print(self, tmp_dir):
        config = ScanConfiguration.from_args(search_dir=tmp_dir, quiet=False)
        config.report_file = 'show_test2.report'
        config.report_dir = tmp_dir
        result = _make_result(config)
        presenter = CliPresenter()
        with patch.object(presenter, '_print') as mock_print:
            presenter.show(result)
            mock_print.assert_called_once_with(result)
