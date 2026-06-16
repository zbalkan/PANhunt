import io

import pytest

from panhunt.config import ScanConfiguration
from panhunt.formats import pdf as pdf_module
from panhunt.formats.pdf import Pdf
from panhunt.job import Job
from panhunt.parser_isolation import SubprocessParserRunner
from panhunt.scanner import PdfScanner


class InlineRunner(SubprocessParserRunner):
    def __init__(self):
        pass

    def run(self, func, *args):
        return func(*args)


def test_pdf_text_limit(monkeypatch):
    monkeypatch.setattr(pdf_module, 'extract_text', lambda source, maxpages=0: 'x' * 20)
    pdf = Pdf(file=io.BytesIO(b'%PDF'), runner=InlineRunner(), max_pages=1, max_text_bytes=4)
    with pytest.raises(Exception, match='exceeds configured limit'):
        pdf.get_text()


def test_pdf_scanner_uses_isolated_limits(monkeypatch, mock_buffer):
    captured = {}

    class CapturingRunner:
        def __init__(self, timeout_seconds, memory_limit_bytes):
            captured['timeout_seconds'] = timeout_seconds
            captured['memory_limit_bytes'] = memory_limit_bytes

        def run(self, func, *args):
            captured['args'] = args
            return 'Card 4111111111111111'

    monkeypatch.setattr('panhunt.scanner.SubprocessParserRunner', CapturingRunner)
    config = ScanConfiguration.from_args(
        parser_timeout_seconds=3,
        parser_memory_limit_bytes=4096,
        max_pdf_pages=2,
        max_pdf_text_bytes=128,
    )
    scanner = PdfScanner(buffer=mock_buffer, config=config)
    result = scanner.scan(Job(basename='inline.pdf', dirname='/tmp', payload=b'%PDF'))

    assert len(result) == 1
    assert captured['timeout_seconds'] == 3
    assert captured['memory_limit_bytes'] == 4096
    assert captured['args'][1:] == (2, 128)
