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
