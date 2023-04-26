import datetime as dt
import hashlib
import os
import re
import struct
import sys
import unicodedata
from ctypes import ArgumentError
from typing import Any


def get_root_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)
    else:
        return './'


def unicode_to_ascii(unicode_str: str) -> str:
    return unicodedata.normalize('NFKD', unicode_str).encode('ascii', 'ignore').decode("ascii")


def bytes_to_time(datetime_bytes: bytes) -> dt.datetime:
    return dt.datetime(year=1601, month=1, day=1) + dt.timedelta(microseconds=unpack_integer('q', datetime_bytes) / 10.0)


def to_zeropaddedhex(value: int, fixed_length: int) -> str:
    return f"{value:0{fixed_length}x}".upper()


def decode_zip_filename(filename: str | bytes) -> Any:

    if isinstance(filename, str):
        return filename
    return filename.decode('cp437')


def decode_zip_text(zip_text: str | bytes) -> str:

    if isinstance(zip_text, bytes):
        return zip_text.decode('cp437')
    elif isinstance(zip_text, str):
        return zip_text
    else:
        raise ValueError()


def get_ext(file_name: str) -> str:

    return os.path.splitext(file_name)[1].lower()


def get_safe_filename(filename: str) -> str:

    return re.sub(r'[/\\;,><&\*:%=\+@!#\^\(\)|\?]', '', filename)


def size_friendly(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    if size < 1024 * 1024:
        return f"{(size / 1024)}KB"
    if size < 1024 * 1024 * 1024:
        return f"{(size / (1024 * 1024))}MB"
    return f"{(size / (1024 * 1024 * 1024))}GB"


def unpack_integer(format: str, buffer: bytes) -> int:
    if format in ['b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q', 'n', 'N', 'P']:
        return int(struct.unpack(format, buffer)[0])
    else:
        raise ArgumentError(format, buffer)


def unpack_float(format: str, buffer: bytes) -> float:
    if format in ['e', 'f', 'd']:
        return float(struct.unpack(format, buffer)[0])
    else:
        raise ArgumentError(format, buffer)


def unpack_bytes(format: str, buffer: bytes) -> bytes:
    if re.compile(r'\d+s').match(format):
        return bytes(struct.unpack(format, buffer)[0])
    else:
        raise ArgumentError(format, buffer)


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


def get_text_hash(text: str | bytes) -> str:
    encoded_text: bytes

    if isinstance(text, str):
        encoded_text = text.encode('utf-8')
    else:
        encoded_text = text

    return hashlib.sha512(encoded_text + 'PAN'.encode('utf-8')).hexdigest()