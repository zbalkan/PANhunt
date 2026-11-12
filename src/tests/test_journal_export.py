"""Journal export format tests: cursor provenance and failure semantics."""
import io
import struct

from panhunt.config import ScanConfiguration
from panhunt.journal import scan_export


def _scan(tmp_path, data):
    config = ScanConfiguration.from_args(target_path=str(tmp_path), quiet=True)
    return scan_export(io.BytesIO(data), config)


def test_text_journal_fields_retain_cursor(tmp_path):
    data = (b'__CURSOR=s=example;i=1\n'
            b'MESSAGE=paid 4111111111111111\n\n'
            b'__CURSOR=s=example;i=2\nMESSAGE=no card\n\n')
    result = _scan(tmp_path, data)
    assert result.pan_count == 1
    assert result.interesting_files == []
    assert result.matched_files[0].source_cursor == 's=example;i=1'
    assert result.matched_files[0].logical_path.endswith('/MESSAGE')


def test_binary_field_preserves_ascii_pan_inside_non_utf8_data(tmp_path):
    payload = b'\xffCard 4111111111111111\x00'
    data = b'__CURSOR=cursor-x\nMESSAGE\n' + struct.pack('<Q', len(payload)) + payload + b'\n\n'
    result = _scan(tmp_path, data)
    assert result.pan_count == 1
    assert result.matched_files[0].source_cursor == 'cursor-x'


def test_malformed_binary_field_marks_scan_incomplete(tmp_path):
    data = b'MESSAGE\n' + struct.pack('<Q', 20) + b'short'
    result = _scan(tmp_path, data)
    assert result.pan_count == 0
    assert result.interesting_files
    assert 'Truncated' in result.interesting_files[0].errors[0]


def test_oversized_field_rejected_before_allocating(tmp_path):
    data = b'MESSAGE\n' + struct.pack('<Q', 9 * 1024 * 1024)
    result = _scan(tmp_path, data)
    assert result.interesting_files


def test_cursor_after_message_is_attached_to_record(tmp_path):
    result = _scan(tmp_path, b'MESSAGE=4111111111111111\n__CURSOR=after\n\n')
    assert result.pan_count == 1
    assert result.matched_files[0].source_cursor == 'after'


def test_two_entries_have_distinct_source_identity(tmp_path):
    result = _scan(tmp_path, b'MESSAGE=4111111111111111\n\n'
                              b'MESSAGE=4111111111111111\n\n')
    assert result.pan_count == 2
    assert result.matched_files[0].logical_path != result.matched_files[1].logical_path


def test_missing_cursor_is_reported_as_incomplete(tmp_path):
    result = _scan(tmp_path, b'MESSAGE=4111111111111111\n\n')
    assert result.pan_count == 1
    assert result.interesting_files
    assert 'no __CURSOR' in result.interesting_files[0].errors[0]


def test_empty_input_is_incomplete(tmp_path):
    result = _scan(tmp_path, b'')
    assert result.pan_count == 0
    assert result.interesting_files
