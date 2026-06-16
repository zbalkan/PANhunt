import io
import logging
import os
from abc import ABC, abstractmethod
from io import IOBase
from typing import Optional

from .buffer import JobBuffer
from .config import ScanConfiguration
from .constants import BLOCK_SIZE_BYTES, MIN_PAN_LENGTH, STREAM_CHUNK_SIZE_BYTES
from .finder import PanFinder
from .formats.eml import Eml
from .formats.mbox import Mbox
from .formats.msmsg import MSMSG
from .formats.pdf import Pdf
from .formats.pst import PST
from .formats.pst import Attachment as PstAttachment
from .job import Job
from .pan import PAN


class ScannerBase(ABC):

    def __init__(self, buffer: JobBuffer, config: ScanConfiguration, pan_finder: Optional[PanFinder] = None) -> None:
        self._buffer = buffer
        self._config = config
        self._pan_finder = pan_finder if pan_finder is not None else PanFinder(config)

    @abstractmethod
    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        raise NotImplementedError()


class PlainTextFileScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        if job.payload:
            if isinstance(job.payload, IOBase):
                return self._scan_stream(job.payload, encoding)
            return self._scan_bytes(job.payload, encoding)
        return self._scan_file(job.abspath, encoding)

    def _scan_bytes(self, payload: bytes, encoding: str = 'utf8') -> list[PAN]:
        if encoding == 'binary':
            encoding = 'utf8'

        text = payload.decode(encoding=encoding, errors='backslashreplace')

        if len(text) < MIN_PAN_LENGTH:
            return []

        return self._pan_finder.find(text)

    def _scan_file(self, filepath: str, encoding: str = 'utf8') -> list[PAN]:
        matches: list[PAN] = []

        file_size: int = os.stat(path=filepath).st_size

        if file_size < MIN_PAN_LENGTH:
            return []

        if 0 < file_size < BLOCK_SIZE_BYTES:
            with open(file=filepath, mode='r', encoding=encoding, errors='backslashreplace') as f:
                text = f.read()
            matches.extend(self._pan_finder.find(text))
        else:
            with open(file=filepath, mode='r', encoding=encoding, errors='backslashreplace') as f:
                for line in f:
                    matches.extend(self._pan_finder.find(line))

        return matches

    def _scan_stream(self, stream: IOBase, encoding: str = 'utf8') -> list[PAN]:
        matches: list[PAN] = []

        if encoding == 'binary':
            encoding = 'utf8'

        try:
            stream.seek(0)
        except io.UnsupportedOperation:
            pass  # non-seekable stream; read from current position
        except OSError as e:
            logging.warning(f"Failed to seek stream to start: {e}")

        buffer = ''
        while True:
            chunk = stream.read(STREAM_CHUNK_SIZE_BYTES)
            if not chunk:
                if buffer and len(buffer) >= MIN_PAN_LENGTH:
                    matches.extend(self._pan_finder.find(buffer))
                break

            if isinstance(chunk, bytes):
                chunk = chunk.decode(encoding=encoding, errors='backslashreplace')

            buffer += chunk

            lines = buffer.split('\n')
            for line in lines[:-1]:
                if len(line) >= MIN_PAN_LENGTH:
                    matches.extend(self._pan_finder.find(line))

            buffer = lines[-1]

        return matches


class MsgScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        msg = MSMSG(msg_file_path=job.payload if job.payload else job.abspath)

        matches: list[PAN] = []

        if msg.validMSG:
            if msg.Body:
                matches.extend(self._pan_finder.find(msg.Body))
            if msg.attachments:
                for att in msg.attachments:
                    self._buffer.enqueue(Job(
                        basename=att.Filename,
                        dirname=job.abspath,
                        payload=att.BinaryData
                    ))

        return matches


class EmlScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        eml = (
            Eml(path=job.abspath, payload=job.payload, size_limit=self._config.size_limit)
            if job.payload
            else Eml(path=job.abspath, size_limit=self._config.size_limit)
        )

        matches: list[PAN] = []

        if eml.body:
            matches.extend(self._pan_finder.find(eml.body))
        if eml.attachments:
            for att in eml.attachments:
                self._buffer.enqueue(Job(
                    basename=att.Filename,
                    dirname=job.abspath,
                    payload=att.BinaryData
                ))

        return matches


class MboxScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        mbox = (
            Mbox(path=job.basename, payload=job.payload, size_limit=self._config.size_limit)
            if job.payload
            else Mbox(path=job.abspath, size_limit=self._config.size_limit)
        )

        matches: list[PAN] = []

        for mail in mbox.mails:
            if mail.body:
                matches.extend(self._pan_finder.find(mail.body))
            if mail.attachments:
                for att in mail.attachments:
                    self._buffer.enqueue(Job(
                        basename=att.Filename,
                        dirname=job.abspath,
                        payload=att.BinaryData
                    ))

        return matches


class PstScanner(ScannerBase):

    def __init__(self, buffer: JobBuffer, config: ScanConfiguration, pan_finder: Optional[PanFinder] = None) -> None:
        super().__init__(buffer, config, pan_finder)
        self._pst: Optional[PST] = None  # instance variable, not class variable

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        if self._pst is None:
            self._pst = PST(pst_file=job.abspath)

        matches: list[PAN] = []

        if self._pst.header.validPST:
            pst_path: str = os.path.abspath(job.abspath)
            for folder in self._pst.folder_generator():
                for message in self._pst.message_generator(folder=folder):
                    if message.Body:
                        matches.extend(self._pan_finder.find(message.Body))

                    if message.HasAttachments:
                        msg_path = os.path.join(folder.path, message.Subject or '[NoSubject]')
                        dirname = ':'.join([pst_path, msg_path])
                        for subattachment in message.subattachments:
                            if subattachment.Filename:
                                att: Optional[PstAttachment] = message.get_attachment(subattachment=subattachment)
                                if att and att.Filename:
                                    self._buffer.enqueue(Job(
                                        basename=att.Filename,
                                        dirname=dirname,
                                        payload=att.BinaryData
                                    ))
            self._pst.close()

        return matches


class PdfScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        pdf = Pdf(file=io.BytesIO(initial_bytes=job.payload)) if job.payload else Pdf(file=job.abspath)
        return self._pan_finder.find(pdf.get_text())
