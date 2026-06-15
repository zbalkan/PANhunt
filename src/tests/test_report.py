"""Tests for ReportGenerator."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from panhunt.config import ScanConfiguration
from panhunt.finding import Finding
from panhunt.models import ScanResult
from panhunt.pan import PAN
from panhunt.report import ReportGenerator


@pytest.fixture
def generator():
    return ReportGenerator()


def _make_result(config, matched=None, interesting=None, elapsed_secs=1):
    start = datetime(2024, 1, 1, 12, 0, 0)
    end = start + timedelta(seconds=elapsed_secs)
    return ScanResult(
        matched_files=matched or [],
        interesting_files=interesting or [],
        start_time=start,
        end_time=end,
        config=config,
    )


class TestGenerateText:
    def test_contains_searched_dir(self, generator, config):
        result = _make_result(config)
        text = generator.generate_text(result)
        assert config.search_dir in text

    def test_contains_elapsed_time(self, generator, config):
        result = _make_result(config)
        text = generator.generate_text(result)
        assert 'Elapsed time' in text

    def test_zero_pans_reported(self, generator, config):
        result = _make_result(config)
        text = generator.generate_text(result)
        assert 'Found 0 possible PANs' in text

    def test_pan_count_in_text(self, generator, config, tmp_text_file):
        finding = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        finding.matches = [PAN(brand='Visa', pan='4111111111111111')]
        result = _make_result(config, matched=[finding])
        text = generator.generate_text(result)
        assert 'Found 1 possible PANs' in text

    def test_interesting_files_section_when_present(self, generator, config):
        finding = Finding(basename='ghost.txt', dirname='/no/such/dir')
        result = _make_result(config, interesting=[finding])
        text = generator.generate_text(result)
        assert 'Interesting Files' in text

    def test_no_interesting_section_when_empty(self, generator, config):
        result = _make_result(config)
        text = generator.generate_text(result)
        assert 'Interesting Files' not in text

    def test_returns_string(self, generator, config):
        result = _make_result(config)
        assert isinstance(generator.generate_text(result), str)


class TestGenerateJson:
    def test_returns_dict(self, generator, config):
        result = _make_result(config)
        data = generator.generate_json(result)
        assert isinstance(data, dict)

    def test_searched_key_present(self, generator, config):
        result = _make_result(config)
        data = generator.generate_json(result)
        assert 'searched' in data
        assert data['searched'] == config.search_dir

    def test_pans_found_key(self, generator, config):
        result = _make_result(config)
        data = generator.generate_json(result)
        assert data['pans_found'] == 0

    def test_pan_results_populated(self, generator, config, tmp_text_file):
        finding = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        finding.matches = [PAN(brand='Visa', pan='4111111111111111')]
        result = _make_result(config, matched=[finding])
        data = generator.generate_json(result)
        assert data['pans_found'] == 1
        assert tmp_text_file in data['pans_found_results']

    def test_interesting_files_key_only_when_present(self, generator, config):
        result = _make_result(config)
        data = generator.generate_json(result)
        assert 'interesting_files' not in data

    def test_interesting_files_included_when_present(self, generator, config):
        finding = Finding(basename='ghost.txt', dirname='/no/such/dir')
        result = _make_result(config, interesting=[finding])
        data = generator.generate_json(result)
        assert 'interesting_files' in data
        assert data['interesting_files']['total'] == 1

    def test_elapsed_is_string(self, generator, config):
        result = _make_result(config)
        data = generator.generate_json(result)
        assert isinstance(data['elapsed'], str)
