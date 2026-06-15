"""Tests for ScannerFactory and ArchiveFactory."""

import pytest

from panhunt.buffer import InMemoryJobBuffer
from panhunt.config import ScanConfiguration
from panhunt.enums import FileTypeEnum
from panhunt.factory import ArchiveFactory, ScannerFactory
from panhunt.scanner import (
    EmlScanner,
    MboxScanner,
    MsgScanner,
    PdfScanner,
    PlainTextFileScanner,
    PstScanner,
)


@pytest.fixture
def factory(buffer, config):
    return ScannerFactory(buffer=buffer, config=config)


class TestScannerFactory:
    def test_plaintext_mime(self, factory):
        s = factory.get_scanner('text/plain', '.txt')
        assert isinstance(s, PlainTextFileScanner)

    def test_pdf_mime(self, factory):
        s = factory.get_scanner('application/pdf', '.pdf')
        assert isinstance(s, PdfScanner)

    def test_msg_mime(self, factory):
        s = factory.get_scanner('application/vnd.ms-outlook', '.msg')
        assert isinstance(s, MsgScanner)

    def test_eml_extension(self, factory):
        s = factory.get_scanner('text/plain', '.eml')
        assert isinstance(s, EmlScanner)

    def test_mbox_extension(self, factory):
        s = factory.get_scanner('text/plain', '.mbox')
        assert isinstance(s, MboxScanner)

    def test_pst_extension(self, factory):
        s = factory.get_scanner('application/octet-stream', '.pst')
        assert isinstance(s, PstScanner)

    def test_unknown_mime_returns_none(self, factory):
        s = factory.get_scanner('video/mp4', '.mp4')
        assert s is None

    def test_image_returns_none(self, factory):
        s = factory.get_scanner('image/jpeg', '.jpg')
        assert s is None

    def test_register_custom_scanner(self, factory):
        factory.register(FileTypeEnum.Plaintext, PdfScanner)
        s = factory.get_scanner('text/plain', '.txt')
        assert isinstance(s, PdfScanner)

    def test_scanners_share_pan_finder(self, factory):
        s1 = factory.get_scanner('text/plain', '.txt')
        s2 = factory.get_scanner('text/plain', '.txt')
        assert s1._pan_finder is s2._pan_finder


class TestArchiveFactory:
    def test_zip_mime(self):
        from panhunt.archive import ZipArchive
        cls = ArchiveFactory.get_archive('application/zip', '.zip')
        assert cls is ZipArchive

    def test_tar_mime(self):
        from panhunt.archive import TarArchive
        cls = ArchiveFactory.get_archive('application/x-tar', '.tar')
        assert cls is TarArchive

    def test_gzip_mime(self):
        from panhunt.archive import GzipArchive
        cls = ArchiveFactory.get_archive('application/gzip', '.gz')
        assert cls is GzipArchive

    def test_xz_mime(self):
        from panhunt.archive import XzArchive
        cls = ArchiveFactory.get_archive('application/x-xz', '.xz')
        assert cls is XzArchive

    def test_docx_is_zip(self):
        from panhunt.archive import ZipArchive
        cls = ArchiveFactory.get_archive(
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.docx',
        )
        assert cls is ZipArchive

    def test_unknown_returns_none(self):
        cls = ArchiveFactory.get_archive('video/mp4', '.mp4')
        assert cls is None

    def test_plaintext_returns_none(self):
        cls = ArchiveFactory.get_archive('text/plain', '.txt')
        assert cls is None
