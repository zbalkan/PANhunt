"""Tests for PanHuntService."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from panhunt.buffer import InMemoryJobBuffer, JobBuffer
from panhunt.config import ScanConfiguration
from panhunt.finding import Finding
from panhunt.models import ScanResult
from panhunt.service import PanHuntService


class TestScanReturnType:
    def test_returns_scan_result(self, config):
        svc = PanHuntService()
        with patch('panhunt.service.Hunter') as MockHunter:
            MockHunter.return_value.hunt.return_value = ([], [])
            result = svc.scan(config)
        assert isinstance(result, ScanResult)

    def test_result_has_config(self, config):
        svc = PanHuntService()
        with patch('panhunt.service.Hunter') as MockHunter:
            MockHunter.return_value.hunt.return_value = ([], [])
            result = svc.scan(config)
        assert result.config is config

    def test_result_has_timestamps(self, config):
        svc = PanHuntService()
        with patch('panhunt.service.Hunter') as MockHunter:
            MockHunter.return_value.hunt.return_value = ([], [])
            result = svc.scan(config)
        assert isinstance(result.start_time, datetime)
        assert isinstance(result.end_time, datetime)
        assert result.end_time >= result.start_time


class TestBufferFactory:
    def test_default_factory_creates_in_memory_buffer(self, config):
        created = []

        def tracking_factory():
            b = InMemoryJobBuffer()
            created.append(b)
            return b

        svc = PanHuntService(buffer_factory=tracking_factory)
        with patch('panhunt.service.Hunter') as MockHunter:
            MockHunter.return_value.hunt.return_value = ([], [])
            svc.scan(config)

        assert len(created) == 1
        assert isinstance(created[0], InMemoryJobBuffer)

    def test_custom_buffer_factory_is_used(self, config, mock_buffer):
        factory_called = []

        def custom_factory():
            factory_called.append(True)
            return mock_buffer

        svc = PanHuntService(buffer_factory=custom_factory)
        with patch('panhunt.service.Hunter') as MockHunter:
            MockHunter.return_value.hunt.return_value = ([], [])
            svc.scan(config)

        assert factory_called


class TestResultContent:
    def test_findings_passed_through(self, config, tmp_text_file):
        import os
        finding = Finding(
            basename=os.path.basename(tmp_text_file),
            dirname=os.path.dirname(tmp_text_file),
        )
        svc = PanHuntService()
        with patch('panhunt.service.Hunter') as MockHunter:
            MockHunter.return_value.hunt.return_value = ([finding], [])
            result = svc.scan(config)
        assert len(result.matched_files) == 1

    def test_failures_passed_through(self, config):
        failing = Finding(basename='bad.txt', dirname='/no/such/dir')
        svc = PanHuntService()
        with patch('panhunt.service.Hunter') as MockHunter:
            MockHunter.return_value.hunt.return_value = ([], [failing])
            result = svc.scan(config)
        assert len(result.interesting_files) == 1

class TestServiceValidation:
    def test_scan_rejects_non_configuration(self):
        service = PanHuntService()
        with pytest.raises(TypeError, match='ScanConfiguration'):
            service.scan(object())  # type: ignore[arg-type]

    def test_scan_validates_target_exists(self, tmp_path):
        service = PanHuntService()
        config = ScanConfiguration.from_args(target_path=str(tmp_path / 'missing'), quiet=True)
        with pytest.raises(ValueError, match='target_path does not exist'):
            service.scan(config)
