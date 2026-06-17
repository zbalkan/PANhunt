"""Tests for Finding class."""

import os
from io import BytesIO

from panhunt.enums import ScanStatusEnum
from panhunt.finding import Finding
from panhunt.scancontext import ScanContext, ScanLimits


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

    def test_size_from_file_like_payload_without_iobase(self):
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

            def seekable(self):
                return True

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

        payload = FileLikePayload(b'hello world')
        f = Finding(
            basename='payload.txt',
            dirname='/tmp',
            payload=payload,
            mimetype='text/plain',
            encoding='us-ascii',
        )
        assert f.status == ScanStatusEnum.Success
        assert f.size == 11
        assert payload.tell() == 0

    def test_size_zero_for_non_seekable_file_like_payload(self):
        class NonSeekablePayload:
            def read(self, size=-1):
                return b'payload'

            def seekable(self):
                return False

        f = Finding(
            basename='payload.txt',
            dirname='/tmp',
            payload=NonSeekablePayload(),
            mimetype='text/plain',
            encoding='us-ascii',
        )

        assert f.status == ScanStatusEnum.Success
        assert f.size == 0

    def test_size_error_sets_failure_and_negative_size(self):
        class BrokenSeekablePayload(BytesIO):
            def tell(self):
                raise OSError('cannot tell')

        f = Finding(
            basename='payload.txt',
            dirname='/tmp',
            payload=BrokenSeekablePayload(b'payload'),
            mimetype='text/plain',
            encoding='us-ascii',
        )

        assert f.status == ScanStatusEnum.Failure
        assert f.size == -1
        assert f.errors == ['cannot tell']

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

    def test_context_metadata_is_copied_from_scan_context(self):
        root = ScanContext.root(
            logical_path='/tmp/archive.zip',
            limits=ScanLimits(max_depth=5, max_child_jobs=5, max_total_expanded_bytes=1024),
        )
        child = root.child('nested.txt', payload_size=7)

        f = Finding(
            basename='nested.txt',
            dirname='/tmp',
            payload=b'payload',
            mimetype='text/plain',
            encoding='us-ascii',
            context=child,
        )

        assert f.logical_path == '/tmp/archive.zip!/nested.txt'
        assert f.depth == 1
        assert f.container_chain == ['/tmp/archive.zip']


class TestMimeHandling:
    def test_provided_mimetype_not_overwritten_when_encoding_also_provided(self):
        f = Finding(
            basename='test.txt',
            dirname='/tmp',
            payload=b'hello',
            mimetype='text/plain',
            encoding='us-ascii',
        )
        assert f.mime_type == 'text/plain'
        assert f.encoding == 'us-ascii'

    def test_provided_mimetype_preserved_when_encoding_is_none(self):
        f = Finding(
            basename='test.txt',
            dirname='/tmp',
            payload=b'hello',
            mimetype='application/custom',
            encoding=None,
        )
        assert f.mime_type == 'application/custom'

    def test_provided_encoding_preserved_when_mimetype_is_none(self):
        f = Finding(
            basename='test.txt',
            dirname='/tmp',
            payload=b'hello',
            mimetype=None,
            encoding='utf-8',
        )
        assert f.encoding == 'utf-8'


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
