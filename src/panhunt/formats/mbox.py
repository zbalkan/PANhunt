import json
import mailbox
import os
import tempfile
from typing import Any, Optional

from ..scancontext import ScanContext

from ..exceptions import PANHuntException


class Mbox:

    filename: str
    mails: list['Mail']

    def __init__(
            self,
            path: str,
            payload: Optional[bytes] = None,
            size_limit: int = 1_073_741_824,
            max_attachments_per_message: int = 1_000,
            max_total_attachment_bytes: int = 1_073_741_824,
            context: Optional[ScanContext] = None) -> None:
        self.filename = path
        self.mails = []
        self._size_limit = size_limit
        self._max_attachments_per_message = max_attachments_per_message
        self._max_total_attachment_bytes = max_total_attachment_bytes
        self._decoded_attachment_bytes = 0
        self._context = context

        if payload:
            if len(payload) > size_limit:
                raise PANHuntException(f'MBOX payload exceeds configured size limit for "{path}"')
            fd, temp_path = tempfile.mkstemp(prefix='panhunt-mbox-')
            try:
                with os.fdopen(fd, 'wb') as temp_file:
                    temp_file.write(payload)
                self._load_mailbox(temp_path)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        else:
            self._load_mailbox(path)

    def _load_mailbox(self, path: str) -> None:
        mbox = mailbox.mbox(path)
        try:
            for message in mbox:
                self.mails.append(Mail(
                    message,
                    size_limit=self._size_limit,
                    max_attachments=self._max_attachments_per_message,
                    max_total_attachment_bytes=self._max_total_attachment_bytes,
                    context=self._context
                ))
                self._decoded_attachment_bytes += self.mails[-1].decoded_attachment_bytes
                if self._decoded_attachment_bytes > self._max_total_attachment_bytes:
                    raise PANHuntException(f'Decoded attachment bytes exceed configured mailbox limit for "{self.filename}"')
        finally:
            mbox.close()

    def __str__(self) -> str:
        d: dict = {}
        d['filename'] = self.filename
        d['mails'] = []
        for mail in self.mails:
            d['mails'].append(mail.__dict__)

        return json.dumps(d, sort_keys=True, indent=4)


class Mail:
    subject: str
    body: str
    attachments: list['Attachment']

    def __init__(
            self,
            message: mailbox.mboxMessage,
            size_limit: int = 1_073_741_824,
            max_attachments: int = 1_000,
            max_total_attachment_bytes: int = 1_073_741_824,
            context: Optional[ScanContext] = None) -> None:
        self.subject = self.get_subject(message)
        self.body = ''
        self.attachments = []
        self._size_limit = size_limit
        self._max_attachments = max_attachments
        self._max_total_attachment_bytes = max_total_attachment_bytes
        self.decoded_attachment_bytes = 0
        self._context = context
        self._extract_message(message)

    def _extract_message(self, msg: mailbox.mboxMessage) -> None:
        if msg.is_multipart():
            for part in msg.walk():
                if part.is_multipart():
                    continue
                disposition = part.get_content_disposition()
                filename = part.get_filename()
                if disposition == 'attachment' or filename:
                    self.parse_attachment(part)
                elif part.get_content_type() == 'text/plain':
                    self.parse_body(part)
        else:
            payloads: Any = msg.get_payload()
            if isinstance(payloads, str):
                self.body = payloads
            else:
                self.parse_body(msg)

    def get_subject(self, message: mailbox.mboxMessage) -> str:
        return str(message.get('Subject'))

    def parse_body(self, body_payload: Any) -> None:
        charset = body_payload.get_content_charset() or 'utf-8'
        decoded = body_payload.get_payload(decode=True)
        if decoded is None:
            payload = body_payload.get_payload()
            self.body += payload if isinstance(payload, str) else str(payload)
        else:
            self.body += decoded.decode(charset, errors='backslashreplace')

    def parse_attachment(self, attachment_payload: Any) -> None:
        filename = attachment_payload.get_filename() or '[NoFilename]'
        binary_data = attachment_payload.get_payload(decode=True)
        if binary_data is None:
            raw = attachment_payload.get_payload()
            binary_data = raw.encode('utf-8', errors='backslashreplace') if isinstance(raw, str) else bytes(raw)
        attachment_count = len(self.attachments) + 1
        byte_count = len(binary_data)
        if attachment_count > self._max_attachments:
            raise PANHuntException(f'Attachment count limit exceeded for "{self.subject}": {attachment_count} over {self._max_attachments}')
        if byte_count > self._size_limit:
            raise PANHuntException(f'Attachment "{filename}" exceeds configured size limit')
        if self.decoded_attachment_bytes + byte_count > self._max_total_attachment_bytes:
            raise PANHuntException(f'Decoded attachment bytes exceed configured message limit for "{self.subject}"')
        if self._context:
            self._context.reserve_attachment(filename, byte_count, attachment_count)
        self.decoded_attachment_bytes += byte_count
        self.attachments.append(Attachment(filename=filename, payload=binary_data))

    def __str__(self) -> str:
        d: dict = {}
        d['subject'] = self.subject
        d['body'] = self.body
        d['attachments'] = []
        for a in self.attachments:
            d['attachments'].append(a.Filename)

        return json.dumps(d, sort_keys=True, indent=4)


class Attachment:

    Filename: str
    BinaryData: Optional[bytes] = None

    def __init__(self, filename: str, payload: bytes) -> None:
        self.Filename = filename
        if len(payload) > 0:
            self.BinaryData = payload
