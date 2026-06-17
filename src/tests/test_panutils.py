import gzip
from io import BytesIO

from panhunt import panutils


def _gzip_payload(filename: str, payload: bytes = b'payload') -> BytesIO:
    stream = BytesIO()
    with gzip.GzipFile(fileobj=stream, mode='wb', filename=filename) as gz_file:
        gz_file.write(payload)
    stream.seek(0)
    return stream


def _gzip_payload_with_raw_filename(filename: bytes, payload: bytes = b'payload') -> BytesIO:
    stream = BytesIO()
    with gzip.GzipFile(fileobj=stream, mode='wb', filename='') as gz_file:
        gz_file.write(payload)
    data = bytearray(stream.getvalue())
    data[3] |= gzip.FNAME
    data[10:10] = filename + b'\x00'
    stream = BytesIO(data)
    stream.seek(0)
    return stream


def test_get_compressed_filename_reads_raw_header_not_payload():
    stream = _gzip_payload('data.txt', b'\x08\x08not a gzip header field')
    gz_file = gzip.GzipFile(fileobj=stream, mode='rb')

    assert panutils.get_compressed_filename(gz_file) == 'data.txt'


def test_get_compressed_filename_decodes_utf8_header_bytes():
    stream = _gzip_payload_with_raw_filename('é.txt'.encode('utf-8'))
    gz_file = gzip.GzipFile(fileobj=stream, mode='rb')

    assert panutils.get_compressed_filename(gz_file) == 'é.txt'


def test_get_compressed_filename_falls_back_for_invalid_utf8_header_bytes():
    stream = _gzip_payload_with_raw_filename(b'\xc3.txt')
    gz_file = gzip.GzipFile(fileobj=stream, mode='rb')

    assert panutils.get_compressed_filename(gz_file) == 'Ã.txt'
