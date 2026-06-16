from io import IOBase
from typing import Any

from . import panutils
from .exceptions import PANHuntException


class LimitedReader(IOBase):
    """Reader wrapper that enforces a maximum number of bytes returned."""

    def __init__(self, stream: IOBase, limit: int, name: str = '<stream>') -> None:
        self._stream = stream
        self._limit = limit
        self._name = name
        self._bytes_read = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return self._stream.seekable()

    def read(self, size: int = -1) -> Any:
        if size is None or size < 0:
            remaining = self._limit - self._bytes_read + 1
            data = self._stream.read(remaining)
        else:
            remaining = self._limit - self._bytes_read + 1
            data = self._stream.read(min(size, remaining))

        data_len = len(data) if data else 0
        self._bytes_read += data_len
        if self._bytes_read > self._limit:
            raise PANHuntException(
                f'Read limit exceeded for "{self._name}": '
                f'{panutils.size_friendly(size=self._bytes_read)} over '
                f'{panutils.size_friendly(size=self._limit)}'
            )
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        pos = self._stream.seek(offset, whence)
        if whence == 0 and offset == 0:
            self._bytes_read = 0
        return pos

    def tell(self) -> int:
        return self._stream.tell()

    def close(self) -> None:
        self._stream.close()
        super().close()


def read_limited(stream: IOBase, limit: int, chunk_size: int = 1024 * 1024) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(min(chunk_size, limit - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise PANHuntException(
                f'Read limit exceeded: {panutils.size_friendly(size=total)} over '
                f'{panutils.size_friendly(size=limit)}'
            )
        chunks.append(chunk)
    return b''.join(chunks)
