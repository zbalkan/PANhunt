"""Tests for ScanConfiguration."""

import os
from pathlib import Path

import pytest

from panhunt.config import ScanConfiguration


class TestDefaults:
    def test_default_target_path(self):
        c = ScanConfiguration()
        expected = 'C:\\' if os.name == 'nt' else '/'
        assert c.target_path == expected

    def test_default_excluded_dirs_not_empty(self):
        c = ScanConfiguration()
        assert isinstance(c.excluded_directories, list)
        assert len(c.excluded_directories) > 0

    def test_default_file_path_is_none(self):
        assert ScanConfiguration().file_path is None

    def test_default_json_dir_is_none(self):
        assert ScanConfiguration().json_dir is None

    def test_default_quiet_is_false(self):
        assert ScanConfiguration().quiet is False

    def test_default_size_limit(self):
        assert ScanConfiguration().size_limit == 8 * 1_073_741_824

    def test_default_worker_count(self):
        assert ScanConfiguration().worker_count == 1

    def test_default_scan_limits(self):
        c = ScanConfiguration()
        assert c.max_scan_depth == 25
        assert c.max_child_jobs == 100_000
        assert c.max_total_expanded_bytes == c.size_limit
        assert c.max_attachment_size == c.size_limit
        assert c.max_attachments_per_message == 1_000
        assert c.max_total_attachment_bytes == c.size_limit

    def test_report_file_has_timestamp(self):
        c = ScanConfiguration()
        assert c.report_file.startswith('panhunt_')
        assert c.report_file.endswith('.report')

    def test_json_file_has_timestamp(self):
        c = ScanConfiguration()
        assert c.json_file.startswith('panhunt_')
        assert c.json_file.endswith('.json')

    def test_report_and_json_share_same_timestamp(self):
        c = ScanConfiguration()
        report_ts = c.report_file.removeprefix('panhunt_').removesuffix('.report')
        json_ts = c.json_file.removeprefix('panhunt_').removesuffix('.json')
        assert report_ts == json_ts


class TestFromArgs:
    def test_target_path_is_resolved(self):
        c = ScanConfiguration.from_args(target_path='/tmp')
        assert c.target_path == os.path.abspath('/tmp')

    def test_quiet_flag(self):
        c = ScanConfiguration.from_args(quiet=True)
        assert c.quiet is True

    def test_excluded_dirs_split_by_comma(self):
        c = ScanConfiguration.from_args(excluded_directories_string='/a,/b,/c')
        assert '/a' in c.excluded_directories
        assert '/b' in c.excluded_directories
        assert '/c' in c.excluded_directories

    def test_excluded_pans_split_by_comma(self):
        c = ScanConfiguration.from_args(excluded_pans_string='1234,5678')
        assert '1234' in c.excluded_pans
        assert '5678' in c.excluded_pans

    def test_size_limit_override(self):
        c = ScanConfiguration.from_args(size_limit=512)
        assert c.size_limit == 512

    def test_worker_count_override(self):
        c = ScanConfiguration.from_args(worker_count=4)
        assert c.worker_count == 4

    def test_scan_limit_overrides(self):
        c = ScanConfiguration.from_args(
            max_scan_depth=3,
            max_child_jobs=7,
            max_total_expanded_bytes=2048,
            max_attachment_size=128,
            max_attachments_per_message=9,
            max_total_attachment_bytes=4096
        )
        assert c.max_scan_depth == 3
        assert c.max_child_jobs == 7
        assert c.max_total_expanded_bytes == 2048
        assert c.max_attachment_size == 128
        assert c.max_attachments_per_message == 9
        assert c.max_total_attachment_bytes == 4096

    def test_invalid_worker_count_raises(self):
        with pytest.raises(ValueError, match='worker_count'):
            ScanConfiguration.from_args(worker_count=0)

    def test_negative_worker_count_raises(self):
        with pytest.raises(ValueError, match='worker_count'):
            ScanConfiguration.from_args(worker_count=-1)

    def test_none_string_is_ignored(self):
        c = ScanConfiguration.from_args(target_path='None')
        default = ScanConfiguration()
        assert c.target_path == default.target_path

    def test_file_target_path_is_resolved(self, tmp_path):
        p = tmp_path / 'test.txt'
        p.write_text('x')
        c = ScanConfiguration.from_args(target_path=str(p))
        assert c.target_path == str(p.resolve())

    def test_json_dir_resolved(self, tmp_path: Path):
        c = ScanConfiguration.from_args(json_dir=str(tmp_path))
        assert c.json_dir == str(tmp_path.resolve())


class TestFromFile:
    def _write_ini(self, tmp_path, content: str) -> str:
        p = tmp_path / 'config.ini'
        p.write_text(content)
        return str(p)

    def test_basic_load(self, tmp_path: Path):
        ini = self._write_ini(tmp_path, '[DEFAULT]\nsearch=/tmp\nquiet=true\n')
        c = ScanConfiguration.from_file(ini)
        assert c.target_path == os.path.abspath('/tmp')
        assert c.quiet is True

    def test_target_takes_precedence(self, tmp_path):
        ini = self._write_ini(
            tmp_path, '[DEFAULT]\ntarget=/var\nsearch=/tmp\nfile=/tmp/file.txt\n')
        c = ScanConfiguration.from_file(ini)
        assert c.target_path == os.path.abspath('/var')

    def test_legacy_file_loads_as_target(self, tmp_path):
        legacy_file = tmp_path / 'legacy.txt'
        legacy_file.write_text('x')
        ini = self._write_ini(tmp_path, f'[DEFAULT]\nfile={legacy_file}\n')
        c = ScanConfiguration.from_file(ini)
        assert c.target_path == str(legacy_file.resolve())

    def test_invalid_file_raises(self):
        with pytest.raises(ValueError, match='Invalid configuration file'):
            ScanConfiguration.from_file('/no/such/file.ini')

    def test_excludepans(self, tmp_path: Path):
        ini = self._write_ini(tmp_path, '[DEFAULT]\nexcludepans=4111111111111111\n')
        c = ScanConfiguration.from_file(ini)
        assert '4111111111111111' in c.excluded_pans

    def test_sizelimit(self, tmp_path: Path):
        ini = self._write_ini(tmp_path, '[DEFAULT]\nsizelimit=1024\n')
        c = ScanConfiguration.from_file(ini)
        assert c.size_limit == 1024

    def test_workers_from_file(self, tmp_path: Path):
        ini = self._write_ini(tmp_path, '[DEFAULT]\nworkers=4\n')
        c = ScanConfiguration.from_file(ini)
        assert c.worker_count == 4


class TestHelpers:
    def test_is_excluded_match(self):
        c = ScanConfiguration.from_args(excluded_pans_string='4111111111111111')
        assert c.is_excluded('4111111111111111') is True

    def test_is_excluded_no_match(self):
        c = ScanConfiguration.from_args(excluded_pans_string='4111111111111111')
        assert c.is_excluded('9999999999999999') is False

    def test_is_excluded_empty(self):
        c = ScanConfiguration()
        assert c.is_excluded('4111111111111111') is False

    def test_get_report_path_contains_filename(self):
        c = ScanConfiguration()
        path = c.get_report_path()
        assert c.report_file in path

    def test_get_json_path_none_when_no_dir(self):
        c = ScanConfiguration()
        assert c.get_json_path() is None

    def test_get_json_path_returns_path_when_dir_set(self, tmp_path: Path):
        c = ScanConfiguration.from_args(json_dir=str(tmp_path))
        path = c.get_json_path()
        assert path is not None
        assert c.json_file in path

    def test_two_instances_are_independent(self):
        c1 = ScanConfiguration.from_args(quiet=True)
        c2 = ScanConfiguration.from_args(quiet=False)
        assert c1.quiet is True
        assert c2.quiet is False
        assert c1 is not c2


class TestParserLimitConfiguration:
    def test_default_parser_limits(self):
        c = ScanConfiguration()
        assert c.parser_timeout_seconds == 30
        assert c.parser_memory_limit_bytes == 512 * 1024 * 1024
        assert c.max_pdf_pages == 100
        assert c.max_pdf_text_bytes == 10 * 1024 * 1024

    def test_parser_limit_overrides(self):
        c = ScanConfiguration.from_args(
            parser_timeout_seconds=5,
            parser_memory_limit_bytes=1024,
            max_pdf_pages=7,
            max_pdf_text_bytes=2048,
        )
        assert c.parser_timeout_seconds == 5
        assert c.parser_memory_limit_bytes == 1024
        assert c.max_pdf_pages == 7
        assert c.max_pdf_text_bytes == 2048


class TestValidation:
    def test_negative_size_limit_raises(self):
        with pytest.raises(ValueError, match='size_limit'):
            ScanConfiguration.from_args(size_limit=-1)

    def test_non_integer_worker_count_raises(self):
        with pytest.raises(ValueError, match='worker_count'):
            ScanConfiguration.from_args(worker_count='many')  # type: ignore[arg-type]

    def test_validate_rejects_missing_target(self, tmp_path: Path):
        c = ScanConfiguration.from_args(target_path=str(tmp_path / 'missing'))
        with pytest.raises(ValueError, match='target_path does not exist'):
            c.validate()

    def test_validate_rejects_json_dir_that_is_a_file(self, tmp_path: Path):
        target = tmp_path / 'target.txt'
        target.write_text('x')
        json_dir = tmp_path / 'json-file'
        json_dir.write_text('not a directory')
        c = ScanConfiguration.from_args(target_path=str(target), json_dir=str(json_dir))
        with pytest.raises(ValueError, match='json_dir'):
            c.validate()

    def test_invalid_config_integer_reports_key(self, tmp_path: Path):
        ini = tmp_path / 'config.ini'
        ini.write_text('[DEFAULT]\nworkers=lots\n')
        with pytest.raises(ValueError, match='Invalid integer value for workers'):
            ScanConfiguration.from_file(str(ini))

    def test_invalid_config_boolean_reports_key(self, tmp_path: Path):
        ini = tmp_path / 'config.ini'
        ini.write_text('[DEFAULT]\nquiet=perhaps\n')
        with pytest.raises(ValueError, match='Invalid boolean value for quiet'):
            ScanConfiguration.from_file(str(ini))
