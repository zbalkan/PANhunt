"""Behavior tests for archive expansion and safety limits."""

import io
import tarfile
import zipfile

from panhunt.archive import OpenDocumentArchive, TarArchive, ZipArchive
from panhunt.exceptions import PANHuntException
from panhunt.scancontext import ScanContext, ScanLimits


def _zip_payload(members):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, 'w') as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return payload.getvalue()


def test_zip_archive_returns_scan_jobs_for_files_and_skips_directories():
    payload = _zip_payload({
        'docs/': b'',
        'docs/card.txt': b'Payment 4111111111111111',
        'notes/clean.txt': b'no card here',
    })

    children, error = ZipArchive(path='sample.zip', payload=payload).get_children()

    assert error is None
    assert [child.basename for child in children] == ['docs/card.txt', 'notes/clean.txt']
    assert [child.payload.read() for child in children] == [
        b'Payment 4111111111111111',
        b'no card here',
    ]


def test_zip_archive_refuses_total_uncompressed_content_over_configured_limit():
    payload = _zip_payload({'one.txt': b'12345', 'two.txt': b'67890'})

    children, error = ZipArchive(path='too-large.zip', payload=payload, size_limit=8).get_children()

    assert children == []
    assert isinstance(error, PANHuntException)
    assert 'total uncompressed ZIP size exceeds limit' in str(error)


def test_opendocument_archive_exposes_readable_text_when_pan_is_split_across_xml_tags():
    payload = _zip_payload({
        'mimetype': b'application/vnd.oasis.opendocument.text',
        'META-INF/manifest.xml': b'<manifest />',
        'content.xml': b'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
                         xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body><office:text><text:p>4111<text:span>1111</text:span>1111<text:span>1111</text:span></text:p></office:text></office:body>
</office:document-content>''',
        'Pictures/image.bin': b'embedded data',
    })

    children, error = OpenDocumentArchive(path='card.odt', payload=payload).get_children()

    assert error is None
    payloads = {child.basename: child.payload.read() for child in children}
    assert payloads['content.xml.txt'] == b'4111111111111111'
    assert payloads['mimetype'] == b'application/vnd.oasis.opendocument.text'
    assert payloads['Pictures/image.bin'] == b'embedded data'
    assert 'META-INF/manifest.xml' not in payloads


def test_opendocument_archive_reports_encrypted_documents_without_emitting_children():
    payload = _zip_payload({
        'META-INF/manifest.xml': b'<manifest><encryption-data /></manifest>',
        'content.xml': b'4111111111111111',
    })

    children, error = OpenDocumentArchive(path='encrypted.odt', payload=payload).get_children()

    assert children == []
    assert isinstance(error, PANHuntException)
    assert 'Encrypted OpenDocument files are not supported' in str(error)


def test_tar_archive_preserves_nested_member_path_and_scan_context_budget():
    payload = io.BytesIO()
    data = b'Payment 4111111111111111'
    with tarfile.open(fileobj=payload, mode='w') as archive:
        info = tarfile.TarInfo('nested/card.txt')
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))

    context = ScanContext.root(
        logical_path='bundle.tar',
        limits=ScanLimits(max_depth=3, max_child_jobs=2, max_total_expanded_bytes=1024),
    )
    children, error = TarArchive(path='bundle.tar', payload=payload.getvalue(), context=context).get_children()

    assert error is None
    assert len(children) == 1
    assert children[0].basename == 'nested/card.txt'
    assert children[0].payload.read() == data
    assert children[0].context.logical_path == 'bundle.tar!/nested/card.txt'
    assert context.budget.child_jobs == 1
    assert context.budget.expanded_bytes == len(data)
