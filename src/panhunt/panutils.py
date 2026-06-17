from __future__ import annotations

import datetime as dt
import io
import os
import pathlib
import re
import struct
import threading
import unicodedata
import zipfile
from gzip import FEXTRA, FNAME, GzipFile
from typing import Any, Optional, Protocol, Union

try:
    from typing import TypeGuard
except ImportError:
    from typing_extensions import TypeGuard

import magic


_thread_local = threading.local()


class FileLikePayload(Protocol):
    def read(self, __size: int = -1) -> bytes:
        ...


class SeekableFileLikePayload(FileLikePayload, Protocol):
    def seek(self, __offset: int, __whence: int = 0) -> int:
        ...

    def tell(self) -> int:
        ...


def is_file_like(payload: Any) -> TypeGuard[FileLikePayload]:
    """Return True for readable stream objects, including older SpooledTemporaryFile implementations.

    Some Python versions do not register tempfile.SpooledTemporaryFile as an
    IOBase subclass. PANhunt passes spooled archive members between components,
    so use capability detection instead of relying only on isinstance(..., IOBase).
    """
    return hasattr(payload, 'read') and callable(payload.read)


def is_seekable_file_like(payload: Any) -> TypeGuard[SeekableFileLikePayload]:
    """Return True for readable streams that zipfile can probe safely."""
    return (
        is_file_like(payload)
        and callable(getattr(payload, 'seek', None))
        and callable(getattr(payload, 'tell', None))
    )


def get_mimetype(path: Optional[str] = None,
                 payload: Optional[Union[bytes, FileLikePayload]] = None) -> tuple[str, str, Optional[Exception]]:
    mime_type = 'Unknown/Unknown'
    encoding = 'Unknown'
    error: Optional[Exception] = None

    try:
        if payload is not None:
            if isinstance(payload, bytes):
                mime_type, encoding = __get_mime_data_from_buffer(payload)
            elif is_file_like(payload):
                mime_type, encoding = __get_mime_data_from_stream(payload)
        elif path is not None:
            mime_type, encoding = __get_mime_data_from_file(path)
    except Exception as ex:
        error = ex

    return mime_type, encoding, error


def _get_magic() -> magic.Magic:
    """Return a per-thread libmagic detector.

    Initialising ``magic.Magic`` loads the magic database, which is relatively
    expensive and was previously repeated for every file, buffer, and stream.
    Scanner workers are thread-based, so one detector per thread keeps the
    object isolated while avoiding repeated database loads on each scan item.
    """
    detector = getattr(_thread_local, 'magic_detector', None)
    if detector is None:
        detector = magic.Magic(mime=True, mime_encoding=True)
        _thread_local.magic_detector = detector
    return detector


def _parse_mime_data(raw_mime_data: str) -> tuple[str, str]:
    mime_data: list[str] = raw_mime_data.split(';', 1)
    mime_type: str = mime_data[0].strip().lower()
    encoding = 'unknown'
    if len(mime_data) > 1:
        encoding = mime_data[1].replace(' charset=', '').strip().lower()
    return mime_type, encoding


def __get_mime_data_from_buffer(payload: bytes) -> tuple[str, str]:
    buffer: bytes
    if (len(payload) < 2048):
        buffer = payload
    else:
        buffer = payload[:2048]

    return _parse_mime_data(_get_magic().from_buffer(buffer))  # type: ignore


def __get_mime_data_from_file(path: str) -> tuple[str, str]:
    return _parse_mime_data(_get_magic().from_file(filename=path))  # type: ignore


def __get_mime_data_from_stream(stream: FileLikePayload) -> tuple[str, str]:
    seek = getattr(stream, 'seek', None)
    if callable(seek):
        try:
            seek(0)
        except (OSError, IOError):
            pass

    buffer: bytes = stream.read(2048)
    result = _parse_mime_data(_get_magic().from_buffer(buffer))  # type: ignore

    if callable(seek):
        try:
            seek(0)
        except (OSError, IOError):
            pass

    return result


def is_valid_zip(path: Optional[str] = None,
                 payload: Optional[Union[bytes, FileLikePayload]] = None) -> bool:
    """Return True only when Python can locate a valid ZIP central directory.

    libmagic can classify partial or otherwise malformed files as ZIP data from
    their header alone.  ``zipfile.is_zipfile`` performs the same end-of-file
    central-directory check that ``ZipFile`` needs before extraction, so use it
    as a cheap guard before dispatching a job to ZIP archive parsing.
    """
    if payload is not None:
        if isinstance(payload, bytes):
            return zipfile.is_zipfile(io.BytesIO(payload))
        if is_seekable_file_like(payload):
            original_pos: Optional[int] = None
            try:
                original_pos = payload.tell()
            except (OSError, IOError):
                original_pos = None
            try:
                return zipfile.is_zipfile(payload)
            finally:
                try:
                    payload.seek(0 if original_pos is None else original_pos)
                except (OSError, IOError):
                    pass
    if path is not None:
        return zipfile.is_zipfile(path)
    return False


def unicode_to_ascii(unicode_str: str) -> str:
    return unicodedata.normalize('NFKD', unicode_str).encode('ascii', 'ignore').decode("ascii")


def bytes_to_time(datetime_bytes: bytes) -> dt.datetime:
    return dt.datetime(year=1601, month=1, day=1) + dt.timedelta(microseconds=unpack_integer('q', datetime_bytes) / 10.0)


def to_zeropaddedhex(value: int, fixed_length: int) -> str:
    return f"{value:0{fixed_length}x}".upper()


def decode_zip_filename(filename: Union[str, bytes]) -> Any:

    if isinstance(filename, str):
        return filename

    if isinstance(filename, memoryview):
        return filename
    return filename.decode('cp437')


def decode_zip_text(zip_text: Union[str, bytes]) -> str:

    if isinstance(zip_text, bytes):
        return zip_text.decode('cp437')
    elif isinstance(zip_text, str):
        return zip_text
    else:
        raise ValueError()


def get_ext(file_name: str) -> str:

    return pathlib.Path(file_name).suffix.lower()


def get_exts(file_name: str) -> list[str]:

    return [ext.lower() for ext in pathlib.Path(file_name).suffixes]


def get_safe_filename(filename: str) -> str:

    return re.sub(r'[/\\;,><&\*:%=\+@!#\^\(\)|\?]', '', filename)


def size_friendly(size: int) -> str:
    if size < 1024:
        return f'{size:.2f}B'
    if size < 1024 * 1024:
        return f'{size / 1024:.2f}KB'
    if size < 1024 * 1024 * 1024:
        return f'{size / (1024 * 1024):.2f}MB'
    if size < 1024 * 1024 * 1024 * 1024:
        return f'{size / (1024 * 1024 * 1024):.2f}GB'
    else:
        return f'{size / (1024 * 1024 * 1024 * 1024):.2f}TB'


def unpack_integer(format: str, buffer: bytes) -> int:
    if format in ['b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q', 'n', 'N', 'P']:
        return int(struct.unpack(format, buffer)[0])
    else:
        raise ValueError(format, buffer)


def unpack_float(format: str, buffer: bytes) -> float:
    if format in ['e', 'f', 'd']:
        return float(struct.unpack(format, buffer)[0])
    else:
        raise ValueError(format, buffer)


def unpack_bytes(format: str, buffer: bytes) -> bytes:
    if re.compile(r'\d+s').match(format):
        return bytes(struct.unpack(format, buffer)[0])
    else:
        raise ValueError(format, buffer)


def as_binary(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    raise TypeError(
        f'Expected type "bytes" got "{type(value)}". \nValue: {value!r}')


def as_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise TypeError(
        f'Expected type "str" got "{type(value)}". \nValue: {value!r}')


def as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    raise TypeError(
        f'Expected type "int" got "{type(value)}". \nValue: {value!r}')


def as_datetime(value: Any) -> dt.datetime:
    if isinstance(value, dt.datetime):
        return value
    raise TypeError(
        f'Expected type "datetime" got "{type(value)}". \nValue: {value!r}')


def memoryview_to_bytes(mem_view: memoryview) -> Optional[bytes]:
    try:
        # Convert memory view to bytes using bytes()
        bytes_data = bytes(mem_view)
        return bytes_data
    except Exception:
        return None


def _fallback_compressed_filename(gf: GzipFile) -> str:
    fname = getattr(gf, 'name', 'unknown')
    if fname.endswith('.gz'):
        fname = os.path.basename(fname)[:-3]
    return fname


def _decode_gzip_header_filename(filename: bytes) -> str:
    try:
        return filename.decode('utf-8')
    except UnicodeDecodeError:
        return filename.decode('latin-1')


def get_compressed_filename(gf: GzipFile) -> str:
    raw_file = getattr(gf, 'fileobj', None)
    original_position = None

    if raw_file is None:
        return _fallback_compressed_filename(gf)

    try:
        original_position = raw_file.tell()
        raw_file.seek(0)
    except (AttributeError, OSError):
        return _fallback_compressed_filename(gf)

    try:
        magic = raw_file.read(2)
        if magic != b'\x1f\x8b':
            return _fallback_compressed_filename(gf)

        method_flag = raw_file.read(2)
        if len(method_flag) < 2:
            return _fallback_compressed_filename(gf)
        method, flag = struct.unpack("<BB", method_flag)
        if method != 8:
            return _fallback_compressed_filename(gf)

        if len(raw_file.read(6)) < 6:  # mtime, extra flags, and OS fields
            return _fallback_compressed_filename(gf)

        if flag & FEXTRA:
            extra_len_bytes = raw_file.read(2)
            if len(extra_len_bytes) < 2:
                return _fallback_compressed_filename(gf)
            extra_len = struct.unpack("<H", extra_len_bytes)[0]
            if len(raw_file.read(extra_len)) < extra_len:
                return _fallback_compressed_filename(gf)

        if not flag & FNAME:
            return _fallback_compressed_filename(gf)

        # Read a null-terminated string containing the original filename from
        # the raw gzip header. Prefer UTF-8 for gzip files produced by tools
        # that write Unicode names, but fall back to Latin-1 so every single-byte
        # FNAME value can be represented without raising UnicodeDecodeError.
        filename = bytearray()
        while True:
            s: bytes = raw_file.read(1)
            if not s or s == b'\000':
                break
            filename.extend(s)

        return _decode_gzip_header_filename(bytes(filename)) or _fallback_compressed_filename(gf)
    finally:
        if original_position is not None:
            try:
                raw_file.seek(original_position)
            except OSError:
                pass
