"""SARIF and JSON reporting must never emit complete PAN values."""

import json
from datetime import datetime

from panhunt.config import ScanConfiguration
from panhunt.finding import Finding
from panhunt.models import ScanResult
from panhunt.pan import PAN
from panhunt.report import ReportGenerator


def _result(tmp_path):
    config = ScanConfiguration.from_args(target_path=str(tmp_path), quiet=True)
    finding = Finding('test.log', str(tmp_path), payload=b'4111111111111111',
                      mimetype='text/plain', encoding='utf-8')
    finding.matches = [PAN('Visa', '4111111111111111', start=0, end=16)]
    return ScanResult([finding], [], datetime.now(), datetime.now(), config)


def test_json_findings_are_masked_and_positioned(tmp_path):
    result = ReportGenerator().generate_json(_result(tmp_path))
    assert result['schema_version'] == '1.0.0'
    assert result['findings'][0]['start'] == 0
    assert result['findings'][0]['end'] == 16
    assert '4111111111111111' not in json.dumps(result)


def test_sarif_is_masked_and_has_offsets(tmp_path):
    result = ReportGenerator().generate_sarif(_result(tmp_path))
    assert result['version'] == '2.1.0'
    assert result['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region']['charOffset'] == 0
    assert '4111111111111111' not in json.dumps(result)
