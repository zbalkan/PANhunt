import datetime as dt
import os
import pathlib
import re
import struct
import sys
import unicodedata
from gzip import FEXTRA, FNAME, GzipFile
from typing import Any, Optional, Union

import magic


def get_root_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)
    else:
        return './'


def get_mimetype(path: Optional[str] = None, payload: Optional[bytes] = None) -> tuple[str, str, Optional[Exception]]:

    try:
        error: Optional[Exception] = None
        if payload is not None:
            mime_type, encoding = __get_mime_data_from_buffer(payload)
        elif path is not None:
            mime_type, encoding = __get_mime_data_from_file(path)
        else:
            mime_type, encoding = 'Unknown/Unknown', 'Unknown'
    except Exception as ex:
        mime_type = 'Unknown/Unknown'
        encoding = 'Unknown'
        error = ex
    finally:
        return mime_type, encoding, error


def __get_mime_data_from_buffer(payload: bytes) -> tuple[str, str]:
    m = magic.Magic(mime=True, mime_encoding=True)
    buffer: bytes
    if (len(payload) < 2048):
        buffer = payload
    else:
        buffer = payload[:2048]

    mime_data: list[str] = m.from_buffer(buffer).split(';')
    mime_type: str = mime_data[0].strip().lower()
    encoding: str = mime_data[1].replace(
        ' charset=', '').strip().lower()
    return mime_type, encoding


def __get_mime_data_from_file(path: str) -> tuple[str, str]:
    m = magic.Magic(mime=True, mime_encoding=True)
    mime_data: list[str] = m.from_file(filename=path).split(';')
    mime_type: str = mime_data[0].strip().lower()
    encoding: str = mime_data[1].replace(
        ' charset=', '').strip().lower()
    return mime_type, encoding


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
        return f'{"{:.2f}".format(round(size, 2))}B'
    if size < 1024 * 1024:
        return f'{"{:.2f}".format(round(size / 1024, 2))}KB'
    if size < 1024 * 1024 * 1024:
        return f'{"{:.2f}".format(round(size / (1024 * 1024), 2))}MB'
    if size < 1024 * 1024 * 1024 * 1024:
        return f'{"{:.2f}".format(round(size / (1024 * 1024 * 1024), 2))}GB'
    else:
        return f'{"{:.2f}".format(round(size / (1024 * 1024 * 1024 * 1024), 2))}TB'


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


def get_compressed_filename(gf: GzipFile) -> str:
    gf.seek(0)
    magic: bytes = gf.read(2)
    method, flag = struct.unpack("<BB", gf.read(2))

    if not flag & FNAME:
        # Filename is not stored in the header, use the filename minus .gz
        fname = getattr(gf, 'name', 'unknown')
        if fname.endswith('.gz'):
            fname = os.path.basename(fname)[:-3]
        return fname

    if flag & FEXTRA:
        # Read & discard the extra field, if present
        extra_len = struct.unpack("<H", gf.read(2))[0]
        gf.read(extra_len)

    # Read a null-terminated string containing the original filename
    filename: list[str] = []
    while True:
        s: bytes = gf.read(1)
        if not s or s == b'\000':
            break
        filename.append(s.decode())

    return ''.join(filename)
