"""Tests for Finding class."""

import os
import tempfile

import pytest

from panhunt.enums import ScanStatusEnum
from panhunt.finding import Finding
from panhunt.pan import PAN


class TestInit:
    def test_abspath_constructed_from_parts(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        assert f.abspath == tmp_text_file

    def test_status_defaults_to_success(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        assert f.status == ScanStatusEnum.Success

    def test_errors_empty_by_default(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        assert f.errors == []

    def test_matches_empty_by_default(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        assert f.matches == []

    def test_size_read_from_real_file(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        assert f.size > 0

    def test_size_from_payload(self):
        payload = b'hello world'
        f = Finding(
            basename='payload.txt',
            dirname='/tmp',
            payload=payload,
            mimetype='text/plain',
            encoding='us-ascii',
        )
        assert f.size == len(payload)

    def test_explicit_exception_sets_failure(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
            err=Exception('test error'),
        )
        assert f.status == ScanStatusEnum.Failure
        assert any('test error' in e for e in f.errors)

    def test_nonexistent_file_sets_failure(self):
        f = Finding(basename='ghost.txt', dirname='/no/such/dir')
        assert f.status == ScanStatusEnum.Failure
        assert len(f.errors) > 0


class TestEquality:
    def test_same_path_equal(self, tmp_text_file):
        f1 = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        f2 = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        assert f1 == f2

    def test_different_path_not_equal(self, tmp_text_file):
        f1 = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        f2 = Finding(basename='other.txt', dirname='/tmp')
        assert f1 != f2

    def test_case_insensitive_equality(self, tmp_text_file):
        basename = os.path.basename(tmp_text_file)
        dirname = os.path.dirname(tmp_text_file)
        f1 = Finding(basename=basename.upper(), dirname=dirname.upper(),
                     mimetype='text/plain', encoding='us-ascii', payload=b'x')
        f2 = Finding(basename=basename.lower(), dirname=dirname.lower(),
                     mimetype='text/plain', encoding='us-ascii', payload=b'x')
        assert f1 == f2

    def test_comparison_with_non_finding_returns_not_implemented(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        result = f.__eq__('not a finding')
        assert result is NotImplemented


class TestExtensions:
    def test_extension_extracted(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        assert f.extension == '.txt'

    def test_str_representation(self, tmp_text_file):
        f = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        s = str(f)
        assert tmp_text_file in s
