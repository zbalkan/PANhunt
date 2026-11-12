"""Bounded parser for journalctl -o export (Journal Export Format).

A journal field is either NAME=value\n or NAME\n + uint64le length +
binary bytes + \n. Entries are delimited by blank lines. This parser does
not treat arbitrary stdin as journal export and records input errors.
"""
from __future__ import annotations

import re
import struct
from datetime import datetime
from typing import BinaryIO

from .config import ScanConfiguration
from .finder import PanFinder
from .finding import Finding
from .models import ScanResult

_FIELD = re.compile(rb'^[A-Z_][A-Z0-9_]*$')
_MAX_FIELD = 8 * 1024 * 1024
_MAX_ENTRY = 32 * 1024 * 1024


class JournalFormatError(ValueError):
    pass


def _exact(stream: BinaryIO, count: int) -> bytes:
    chunks = []
    while count:
        part = stream.read(min(count, 64 * 1024))
        if not part:
            raise JournalFormatError('Truncated binary journal field')
        chunks.append(part)
        count -= len(part)
    return b''.join(chunks)


def scan_export(stream: BinaryIO, config: ScanConfiguration) -> ScanResult:
    """Scan individual fields and retain the cursor identifying each record."""
    start_time = datetime.now()
    finder = PanFinder(config)
    findings = []
    failures = []
    current_matches = []
    current_cursor = None
    current_size = 0
    entry_index = 0

    def finish_entry():
        nonlocal current_matches, current_cursor, current_size, entry_index
        if current_size == 0:
            return
        entry_index += 1
        for field, matches in current_matches:
            finding = Finding(field, f'journal/entry-{entry_index}', payload=b'',
                              mimetype='text/plain', encoding='utf-8')
            finding.matches = matches
            finding.source_cursor = current_cursor
            finding.logical_path = f'journal/entry-{entry_index}/{field}'
            findings.append(finding)
        current_matches = []
        current_cursor = None
        current_size = 0

    try:
        while True:
            header = stream.readline(_MAX_FIELD + 512)
            if not header:
                finish_entry()
                break
            if len(header) > _MAX_FIELD + 256:
                raise JournalFormatError('Journal field header exceeds limit')
            if header == b'\n':
                finish_entry()
                continue
            if not header.endswith(b'\n'):
                raise JournalFormatError('Truncated journal field header')
            header = header[:-1]
            if b'=' in header:
                name, payload = header.split(b'=', 1)
                if len(payload) > _MAX_FIELD:
                    raise JournalFormatError('Journal field exceeds limit')
            else:
                name = header
                length = struct.unpack('<Q', _exact(stream, 8))[0]
                if length > _MAX_FIELD:
                    raise JournalFormatError('Journal binary field exceeds limit')
                payload = _exact(stream, length)
                if _exact(stream, 1) != b'\n':
                    raise JournalFormatError('Missing journal binary field terminator')
            if not _FIELD.fullmatch(name):
                raise JournalFormatError('Invalid journal field name')
            current_size += len(name) + len(payload)
            if current_size > _MAX_ENTRY:
                raise JournalFormatError('Journal record exceeds limit')
            if name == b'__CURSOR':
                current_cursor = payload.decode('utf-8', errors='replace')
                continue
            # ASCII PAN candidates survive UTF-8 escaping of non-UTF-8 fields.
            matches = finder.find(payload.decode('utf-8', errors='backslashreplace'))
            if matches:
                current_matches.append((name.decode('ascii'), matches))
    except (OSError, JournalFormatError) as exc:
        # Preserve matches found before an incomplete record; never claim clean.
        finish_entry()
        failures.append(Finding('journal-export', 'stdin', payload=b'',
                                mimetype='application/vnd.fdo.journal',
                                encoding='binary', err=exc))

    if entry_index == 0 and not failures:
        failures.append(Finding('journal-export', 'stdin', payload=b'',
                                mimetype='application/vnd.fdo.journal',
                                encoding='binary',
                                err=JournalFormatError('Empty journal export; no coverage can be established')))

    return ScanResult(matched_files=findings, interesting_files=failures,
                      start_time=start_time, end_time=datetime.now(), config=config)
