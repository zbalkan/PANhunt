"""Subprocess isolation utilities for high-risk parsers."""

import multiprocessing as mp
import queue
import signal
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .exceptions import PANHuntException

if sys.platform == 'win32':
    resource = None
else:
    import resource


@dataclass
class ParserResult:
    value: Any = None
    error: Optional[str] = None
    traceback_text: Optional[str] = None


class ParserTimeoutError(PANHuntException):
    """Raised when an isolated parser exceeds its wall-clock timeout."""


class ParserWorkerError(PANHuntException):
    """Raised when an isolated parser crashes or reports an exception."""


def _apply_memory_limit(limit_bytes: int) -> None:
    if limit_bytes <= 0:
        return
    if resource is None:
        return
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))


def _worker_main(result_queue: mp.Queue, func: Callable[..., Any], args: tuple[Any, ...], memory_limit: int) -> None:
    try:
        _apply_memory_limit(memory_limit)
        alarm: Any | None = getattr(signal, 'alarm', None)
        if callable(alarm):
            alarm(0)
        result_queue.put(ParserResult(value=func(*args)))
    except BaseException as exc:  # report parser failures to parent process
        result_queue.put(ParserResult(error=f'{type(exc).__name__}: {exc}', traceback_text=traceback.format_exc()))


class SubprocessParserRunner:
    """Run parser callables in a short-lived subprocess with timeout and memory caps."""

    def __init__(self, timeout_seconds: int, memory_limit_bytes: int = 0) -> None:
        self._timeout_seconds = timeout_seconds
        self._memory_limit_bytes = memory_limit_bytes

    def run(self, func: Callable[..., Any], *args: Any) -> Any:
        result_queue: mp.Queue = mp.Queue(maxsize=1)
        proc = mp.Process(
            target=_worker_main,
            args=(result_queue, func, args, self._memory_limit_bytes),
            daemon=True,
        )
        proc.start()
        proc.join(self._timeout_seconds)
        if proc.is_alive():
            proc.terminate()
            proc.join(1)
            if proc.is_alive():
                proc.kill()
                proc.join()
            raise ParserTimeoutError(f'Parser timed out after {self._timeout_seconds} seconds')

        if proc.exitcode not in (0, None) and result_queue.empty():
            raise ParserWorkerError(f'Parser subprocess exited with code {proc.exitcode}')

        try:
            result: ParserResult = result_queue.get_nowait()
        except queue.Empty as exc:
            raise ParserWorkerError('Parser subprocess did not return a result') from exc

        if result.error:
            raise ParserWorkerError(result.error)
        return result.value
