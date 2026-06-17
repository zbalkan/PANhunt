"""Tests for PANhunt's command-line entrypoint behavior."""

import logging

from panhunt import _log_uncaught_exception


def test_uncaught_exception_hook_logs_exception_tuple(caplog):
    error = RuntimeError('boom')

    with caplog.at_level(logging.CRITICAL):
        _log_uncaught_exception(RuntimeError, error, error.__traceback__)

    assert 'Unhandled fatal error' in caplog.text
    assert 'RuntimeError: boom' in caplog.text


def test_keyboard_interrupt_hook_does_not_log_error(caplog, capsys):
    interrupt = KeyboardInterrupt()

    with caplog.at_level(logging.ERROR):
        _log_uncaught_exception(KeyboardInterrupt, interrupt, interrupt.__traceback__)

    assert capsys.readouterr().out == '\nInterrupted. Exiting cleanly.\n'
    assert caplog.text == ''


def test_run_delegates_to_main(monkeypatch):
    import panhunt

    called = False

    def fake_main():
        nonlocal called
        called = True

    monkeypatch.setattr(panhunt, 'main', fake_main)

    panhunt.run()

    assert called is True


def test_run_converts_keyboard_interrupt_to_exit_code(monkeypatch, capsys):
    import pytest
    import panhunt

    def fake_main():
        raise KeyboardInterrupt

    monkeypatch.setattr(panhunt, 'main', fake_main)

    with pytest.raises(SystemExit) as exc_info:
        panhunt.run()

    assert exc_info.value.code == 130
    assert capsys.readouterr().out == '\nInterrupted. Exiting cleanly.\n'


def test_run_converts_fatal_exception_to_exit_code(monkeypatch, capsys):
    import pytest
    import panhunt

    def fake_main():
        raise RuntimeError('boom')

    monkeypatch.setattr(panhunt, 'main', fake_main)

    with pytest.raises(SystemExit) as exc_info:
        panhunt.run()

    assert exc_info.value.code == 1
    assert capsys.readouterr().out == 'ERROR: boom\n'
