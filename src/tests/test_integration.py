"""Integration tests — full pipeline from file to ScanResult."""

import os
import zipfile

from panhunt.config import ScanConfiguration
from panhunt.service import PanHuntService


class TestScanCleanFile:
    def test_clean_file_produces_no_matches(self, tmp_dir):
        path = os.path.join(tmp_dir, 'clean.txt')
        with open(path, 'w') as f:
            f.write('No card numbers here.\n')
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        assert result.pan_count == 0
        assert result.matched_files == []

    def test_result_has_elapsed_time(self, tmp_dir):
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        assert result.elapsed.total_seconds() >= 0


class TestScanPanFile:
    def test_finds_visa_pan(self, tmp_dir):
        path = os.path.join(tmp_dir, 'pan.txt')
        with open(path, 'w') as f:
            f.write('Payment: 4111 1111 1111 1111\n')
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        assert result.pan_count == 1

    def test_finds_multiple_pans(self, tmp_dir):
        path = os.path.join(tmp_dir, 'multi.txt')
        with open(path, 'w') as f:
            f.write('Visa: 4111111111111111\n')
            f.write('MC: 5500005555555559\n')
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        assert result.pan_count == 2

    def test_excluded_pan_not_reported(self, tmp_dir):
        path = os.path.join(tmp_dir, 'excluded.txt')
        with open(path, 'w') as f:
            f.write('4111111111111111\n')
        config = ScanConfiguration.from_args(
            target_path=tmp_dir,
            excluded_pans_string='4111111111111111',
            quiet=True,
        )
        result = PanHuntService().scan(config)
        assert result.pan_count == 0


class TestScanSingleFile:
    def test_single_file_mode(self, tmp_pan_file):
        config = ScanConfiguration.from_args(target_path=tmp_pan_file, quiet=True)
        result = PanHuntService().scan(config)
        assert result.pan_count == 1

    def test_single_clean_file(self, tmp_text_file):
        config = ScanConfiguration.from_args(target_path=tmp_text_file, quiet=True)
        result = PanHuntService().scan(config)
        assert result.pan_count == 0


class TestScanResultStructure:
    def test_result_has_config_reference(self, tmp_dir):
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        assert result.config is config

    def test_matched_files_are_findings(self, tmp_dir):
        path = os.path.join(tmp_dir, 'card.txt')
        with open(path, 'w') as f:
            f.write('4111111111111111\n')
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        from panhunt.finding import Finding
        for f in result.matched_files:
            assert isinstance(f, Finding)


class TestScanOpenDocumentFile:
    def _write_odf(self, path, content_xml, manifest_xml=None):
        if manifest_xml is None:
            manifest_xml = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
</manifest:manifest>"""

        with zipfile.ZipFile(path, 'w') as odf:
            odf.writestr('mimetype', 'application/vnd.oasis.opendocument.text')
            odf.writestr('META-INF/manifest.xml', manifest_xml)
            odf.writestr('content.xml', content_xml)

    def test_finds_pan_in_odt_content_xml(self, tmp_dir):
        path = os.path.join(tmp_dir, 'card.odt')
        self._write_odf(path, """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
                         xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body><office:text><text:p>Payment 4111111111111111</text:p></office:text></office:body>
</office:document-content>""")

        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)

        assert result.pan_count == 1

    def test_finds_pan_split_across_odt_xml_text_nodes(self, tmp_dir):
        path = os.path.join(tmp_dir, 'split.odt')
        self._write_odf(path, """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
                         xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body><office:text><text:p>4111<text:span>1111</text:span>1111<text:span>1111</text:span></text:p></office:text></office:body>
</office:document-content>""")

        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)

        assert result.pan_count == 1

    def test_reports_encrypted_odt_as_failure(self, tmp_dir):
        path = os.path.join(tmp_dir, 'encrypted.odt')
        manifest_xml = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
  <manifest:file-entry manifest:full-path="content.xml">
    <manifest:encryption-data />
  </manifest:file-entry>
</manifest:manifest>"""
        self._write_odf(path, '<encrypted />', manifest_xml=manifest_xml)

        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)

        assert result.pan_count == 0
        assert len(result.interesting_files) == 1
        assert 'Encrypted OpenDocument files are not supported' in result.interesting_files[0].errors[0]


class TestCompressedLogPipeline:
    """Gzip must be handled as an archive rather than skipped as opaque data."""

    def test_rotated_gzip_log_detects_pan(self, tmp_dir):
        import gzip
        path = os.path.join(tmp_dir, 'messages.log.1.gz')
        with gzip.open(path, 'wb') as stream:
            stream.write(b'payment 4111111111111111\n')
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        assert result.pan_count == 1, result.interesting_files
        assert result.interesting_files == []

    def test_gzip_buffer_chunk_detects_pan(self, tmp_dir):
        import gzip
        path = os.path.join(tmp_dir, 'buffer.0.gz')
        with gzip.open(path, 'wb') as stream:
            stream.write(b'{"message":"4111111111111111"}\n')
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        assert result.pan_count == 1, result.interesting_files
        assert result.interesting_files == []

    def test_invalid_gzip_is_reported_instead_of_silently_ignored(self, tmp_dir):
        path = os.path.join(tmp_dir, 'corrupt.gz')
        with open(path, 'wb') as stream:
            stream.write(b'\x1f\x8b\x08invalid gzip payload')
        config = ScanConfiguration.from_args(target_path=tmp_dir, quiet=True)
        result = PanHuntService().scan(config)
        assert result.pan_count == 0
        assert result.interesting_files
