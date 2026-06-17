import gzip
import threading
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


def test_get_mimetype_reuses_magic_detector_for_buffers(monkeypatch):
    class FakeMagic:
        instances = 0

        def __init__(self, **kwargs):
            FakeMagic.instances += 1
            self.kwargs = kwargs

        def from_buffer(self, buffer):
            return 'text/plain; charset=us-ascii'

    monkeypatch.delattr(panutils._thread_local, 'magic_detector', raising=False)
    monkeypatch.setattr(panutils.magic, 'Magic', FakeMagic)

    assert panutils.get_mimetype(payload=b'hello') == ('text/plain', 'us-ascii', None)
    assert panutils.get_mimetype(payload=b'world') == ('text/plain', 'us-ascii', None)
    assert FakeMagic.instances == 1


def test_get_mimetype_reuses_magic_detector_across_file_buffer_and_stream(monkeypatch, tmp_path):
    calls = []

    class FakeMagic:
        instances = 0

        def __init__(self, **kwargs):
            FakeMagic.instances += 1
            self.kwargs = kwargs

        def from_buffer(self, buffer):
            calls.append(('buffer', buffer, self.kwargs))
            return 'text/plain; charset=utf-8'

        def from_file(self, filename):
            calls.append(('file', filename, self.kwargs))
            return 'text/plain; charset=utf-8'

    file_path = tmp_path / 'sample.txt'
    file_path.write_text('hello', encoding='utf-8')
    stream = BytesIO(b'stream payload')
    stream.seek(3)

    monkeypatch.delattr(panutils._thread_local, 'magic_detector', raising=False)
    monkeypatch.setattr(panutils.magic, 'Magic', FakeMagic)

    assert panutils.get_mimetype(path=str(file_path)) == ('text/plain', 'utf-8', None)
    assert panutils.get_mimetype(payload=b'buffer payload') == ('text/plain', 'utf-8', None)
    assert panutils.get_mimetype(payload=stream) == ('text/plain', 'utf-8', None)

    assert FakeMagic.instances == 1
    assert calls == [
        ('file', str(file_path), {'mime': True, 'mime_encoding': True}),
        ('buffer', b'buffer payload', {'mime': True, 'mime_encoding': True}),
        ('buffer', b'stream payload', {'mime': True, 'mime_encoding': True}),
    ]
    assert stream.tell() == 0


def test_get_mimetype_uses_thread_local_magic_cache(monkeypatch):
    class FakeMagic:
        instances = 0

        def __init__(self, **kwargs):
            FakeMagic.instances += 1

    monkeypatch.delattr(panutils._thread_local, 'magic_detector', raising=False)
    monkeypatch.setattr(panutils.magic, 'Magic', FakeMagic)

    barrier = threading.Barrier(2)
    detector_ids_by_thread = []

    def get_detector_ids():
        first = panutils._get_magic()
        barrier.wait(timeout=5)
        second = panutils._get_magic()
        detector_ids_by_thread.append((id(first), id(second)))

    threads = [threading.Thread(target=get_detector_ids) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert FakeMagic.instances == 2
    assert len(detector_ids_by_thread) == 2
    assert detector_ids_by_thread[0][0] == detector_ids_by_thread[0][1]
    assert detector_ids_by_thread[1][0] == detector_ids_by_thread[1][1]
    assert detector_ids_by_thread[0][0] != detector_ids_by_thread[1][0]


def test_get_mimetype_uses_short_buffer_without_padding(monkeypatch):
    seen_buffers = []

    class FakeMagic:
        def __init__(self, **kwargs):
            pass

        def from_buffer(self, buffer):
            seen_buffers.append(buffer)
            return 'application/octet-stream; charset=binary'

    monkeypatch.delattr(panutils._thread_local, 'magic_detector', raising=False)
    monkeypatch.setattr(panutils.magic, 'Magic', FakeMagic)

    assert panutils.get_mimetype(payload=b'abc') == ('application/octet-stream', 'binary', None)
    assert seen_buffers == [b'abc']


def test_get_mimetype_returns_error_fallback(monkeypatch):
    class FakeMagic:
        def __init__(self, **kwargs):
            pass

        def from_buffer(self, buffer):
            raise RuntimeError('libmagic failed')

    monkeypatch.delattr(panutils._thread_local, 'magic_detector', raising=False)
    monkeypatch.setattr(panutils.magic, 'Magic', FakeMagic)

    mime_type, encoding, error = panutils.get_mimetype(payload=b'abc')

    assert mime_type == 'Unknown/Unknown'
    assert encoding == 'Unknown'
    assert isinstance(error, RuntimeError)
    assert str(error) == 'libmagic failed'
