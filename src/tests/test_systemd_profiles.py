"""Static regression checks for packaged example systemd profiles."""
from pathlib import Path
import configparser


ROOT = Path(__file__).resolve().parents[2] / 'examples' / 'systemd'


def test_template_runs_one_profile_and_alerts_on_failures():
    text = (ROOT / 'panhunt@.service').read_text(encoding='utf-8')
    assert 'ExecStart=/usr/local/bin/panhunt -C /etc/panhunt/panhunt-%i.ini' in text
    assert 'OnFailure=panhunt-alert@%i.service' in text
    assert 'SuccessExitStatus=130' in text
    assert text.count('ExecStart=') == 1


def test_timer_targets_matching_service_instance():
    text = (ROOT / 'panhunt@.timer').read_text(encoding='utf-8')
    assert 'Unit=panhunt@%i.service' in text
    assert 'Persistent=true' in text


def test_profiles_write_to_distinct_instance_directories():
    for name in ('opt', 'var-log'):
        config = configparser.ConfigParser()
        config.read(ROOT / f'panhunt-{name}.ini')
        assert config['DEFAULT']['outfile'] == f'/var/log/panhunt/{name}'
        assert config['DEFAULT']['json'] == f'/var/log/panhunt/{name}'


def test_alert_reports_instance_specific_path():
    text = (ROOT / 'panhunt-alert@.service').read_text(encoding='utf-8')
    assert '/var/log/panhunt/%i' in text
