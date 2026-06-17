import io
import logging
import os
from abc import ABC, abstractmethod
from io import IOBase
from typing import Optional

from .buffer import JobBuffer
from .config import ScanConfiguration
from .constants import BLOCK_SIZE_BYTES, MIN_PAN_LENGTH, STREAM_CHUNK_SIZE_BYTES
from .exceptions import PANHuntException
from .finder import PanFinder
from .formats.eml import Eml
from .formats.mbox import Mbox
from .formats.msmsg import MSMSG
from .formats.pdf import Pdf
from .formats.pst import PST
from .formats.pst import Attachment as PstAttachment
from .parser_isolation import SubprocessParserRunner
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

    def _validate_attachment(self, parent: Job, basename: str, payload: Optional[bytes], attachment_count: int) -> None:
        payload_size = len(payload) if payload is not None else 0
        if attachment_count > self._config.max_attachments_per_message:
            raise PANHuntException(
                f'Attachment count limit exceeded for "{parent.abspath}": '
                f'{attachment_count} over {self._config.max_attachments_per_message}'
            )
        if payload_size > self._config.max_attachment_size:
            raise PANHuntException(f'Attachment "{basename}" exceeds configured size limit')
        if parent.context:
            parent.context.reserve_attachment(basename, payload_size, attachment_count)

    def _child_job(self, parent: Job, basename: str, payload: Optional[bytes]) -> Job:
        payload_size = len(payload) if payload is not None else 0
        context = parent.context.child(basename=basename, payload_size=payload_size) if parent.context else None
        return Job(
            basename=basename,
            dirname=parent.abspath,
            payload=payload,
            context=context
        )

    def _payload_bytes(self, job: Job) -> Optional[bytes]:
        payload: bytes | IOBase | None = job.payload
        if payload is None:
            return None
        if isinstance(payload, bytes):
            return payload
        if not isinstance(payload, IOBase):
            return bytes(payload)

        try:
            payload.seek(0)
        except io.UnsupportedOperation:
            pass  # non-seekable stream; read from current position
        except OSError as e:
            logging.warning(f"Failed to seek stream to start: {e}")

        stream_payload = payload.read()
        if isinstance(stream_payload, bytes):
            return stream_payload
        return stream_payload.encode('utf8', errors='backslashreplace')


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
        payload = self._payload_bytes(job)
        msg = MSMSG(msg_target_path=payload if payload is not None else job.abspath)

        matches: list[PAN] = []

        if msg.validMSG:
            if msg.Body:
                matches.extend(self._pan_finder.find(msg.Body))
            if msg.attachments:
                for index, att in enumerate(msg.attachments, start=1):
                    self._validate_attachment(job, att.Filename, att.BinaryData, index)
                    self._buffer.enqueue(self._child_job(job, att.Filename, att.BinaryData))

        return matches


class EmlScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        payload = self._payload_bytes(job)
        eml = (
            Eml(
                path=job.abspath,
                payload=payload,
                size_limit=self._config.max_attachment_size,
                max_attachments=self._config.max_attachments_per_message,
                max_total_attachment_bytes=self._config.max_total_attachment_bytes,
                context=job.context
            )
            if payload is not None
            else Eml(
                path=job.abspath,
                size_limit=self._config.max_attachment_size,
                max_attachments=self._config.max_attachments_per_message,
                max_total_attachment_bytes=self._config.max_total_attachment_bytes,
                context=job.context
            )
        )

        matches: list[PAN] = []

        if eml.body:
            matches.extend(self._pan_finder.find(eml.body))
        if eml.attachments:
            for att in eml.attachments:
                self._buffer.enqueue(self._child_job(job, att.Filename, att.BinaryData))

        return matches


class MboxScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        payload = self._payload_bytes(job)
        mbox = (
            Mbox(
                path=job.basename,
                payload=payload,
                size_limit=self._config.max_attachment_size,
                max_attachments_per_message=self._config.max_attachments_per_message,
                max_total_attachment_bytes=self._config.max_total_attachment_bytes,
                context=job.context
            )
            if payload is not None
            else Mbox(
                path=job.abspath,
                size_limit=self._config.max_attachment_size,
                max_attachments_per_message=self._config.max_attachments_per_message,
                max_total_attachment_bytes=self._config.max_total_attachment_bytes,
                context=job.context
            )
        )

        matches: list[PAN] = []

        for mail in mbox.mails:
            if mail.body:
                matches.extend(self._pan_finder.find(mail.body))
            if mail.attachments:
                for att in mail.attachments:
                    self._buffer.enqueue(self._child_job(job, att.Filename, att.BinaryData))

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
            folder_count = 0
            message_count = 0
            attachment_count = 0
            for folder in self._pst.folder_generator():
                folder_count += 1
                for message in self._pst.message_generator(folder=folder):
                    message_count += 1
                    if message.Body:
                        matches.extend(self._pan_finder.find(message.Body))

                    if message.HasAttachments:
                        msg_path = os.path.join(folder.path, message.Subject or '[NoSubject]')
                        dirname = ':'.join([pst_path, msg_path])
                        for index, subattachment in enumerate(message.subattachments, start=1):
                            attachment_count += 1
                            if subattachment.Filename:
                                att: Optional[PstAttachment] = message.get_attachment(subattachment=subattachment)
                                if att and att.Filename:
                                    self._validate_attachment(job, att.Filename, att.BinaryData, index)
                                    self._buffer.enqueue(Job(
                                        basename=att.Filename,
                                        dirname=dirname,
                                        payload=att.BinaryData,
                                        context=job.context.child(
                                            basename=att.Filename,
                                            payload_size=len(att.BinaryData) if att.BinaryData is not None else 0
                                        ) if job.context else None
                                    ))
            self._pst.close()

        return matches


class PdfScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        runner = SubprocessParserRunner(
            timeout_seconds=self._config.parser_timeout_seconds,
            memory_limit_bytes=self._config.parser_memory_limit_bytes
        )
        payload = self._payload_bytes(job)
        pdf = Pdf(
            file=io.BytesIO(initial_bytes=payload) if payload is not None else job.abspath,
            runner=runner,
            max_pages=self._config.max_pdf_pages,
            max_text_bytes=self._config.max_pdf_text_bytes
        )
        return self._pan_finder.find(pdf.get_text())
