import time

import pytest

from panhunt.parser_isolation import ParserTimeoutError, ParserWorkerError, SubprocessParserRunner


def _return_value(value):
    return value


def _sleep_for(seconds):
    time.sleep(seconds)
    return 'done'


def _raise_error():
    raise ValueError('boom')


class TestSubprocessParserRunner:
    def test_returns_parser_result(self):
        runner = SubprocessParserRunner(timeout_seconds=5)
        assert runner.run(_return_value, 'ok') == 'ok'

    def test_times_out_parser(self):
        runner = SubprocessParserRunner(timeout_seconds=1)
        with pytest.raises(ParserTimeoutError):
            runner.run(_sleep_for, 5)

    def test_converts_parser_exception(self):
        runner = SubprocessParserRunner(timeout_seconds=5)
        with pytest.raises(ParserWorkerError, match='ValueError: boom'):
            runner.run(_raise_error)
