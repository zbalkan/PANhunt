from __future__ import annotations

import json
from email import message, parser
from typing import Optional, Union, cast

from ..exceptions import PANHuntException
from ..scancontext import ScanContext


class Eml:

    filename: str
    body: str
    attachments: list['Attachment']

    __text: str

    def __init__(
            self,
            path: str,
            payload: Optional[bytes] = None,
            size_limit: int = 1_073_741_824,
            max_attachments: int = 1_000,
            max_total_attachment_bytes: int = 1_073_741_824,
            context: Optional[ScanContext] = None) -> None:
        if payload:
            msg = parser.BytesParser().parsebytes(payload)
        else:
            with open(path, "rb") as f:
                msg = parser.BytesParser().parse(f)

        self.filename = path
        self.body = ''
        self.attachments = []
        self._size_limit = size_limit
        self._max_attachments = max_attachments
        self._max_total_attachment_bytes = max_total_attachment_bytes
        self._decoded_attachment_bytes = 0
        self._context = context
        self._extract_message(msg)
        self.__text = self.to_text()

    def _extract_message(self, msg: message.Message) -> None:
        if msg.is_multipart():
            for part in msg.walk():
                if part.is_multipart():
                    continue
                self._parse_part(part)
        else:
            self._parse_part(msg)

    def _parse_part(self, part: message.Message) -> None:
        disposition = part.get_content_disposition()
        filename = part.get_filename()
        if disposition == 'attachment' or filename:
            self.parse_attachment(part)
        elif part.get_content_type() == 'text/plain':
            self.parse_body(part)

    def parse_body(self, body_payload: Union[message.Message, str]) -> None:
        if isinstance(body_payload, message.Message):
            charset = body_payload.get_content_charset() or 'utf-8'
            decoded = cast(Optional[bytes], body_payload.get_payload(decode=True))
            if decoded is None:
                self.body += str(body_payload.get_payload())
            else:
                self.body += decoded.decode(charset, errors='backslashreplace')
        elif isinstance(body_payload, str):
            self.body += body_payload

    def parse_attachment(self, attachment_payload: message.Message) -> None:
        filename = attachment_payload.get_filename() or '[NoFilename]'
        binary_data = cast(Optional[bytes], attachment_payload.get_payload(decode=True))
        if binary_data is None:
            raw = attachment_payload.get_payload()
            if isinstance(raw, str):
                binary_data = raw.encode('utf-8', errors='backslashreplace')
            elif isinstance(raw, bytes):
                binary_data = raw
            else:
                binary_data = str(raw).encode('utf-8', errors='backslashreplace')
        attachment_count = len(self.attachments) + 1
        byte_count = len(binary_data)
        if attachment_count > self._max_attachments:
            raise PANHuntException(f'Attachment count limit exceeded for "{self.filename}": {attachment_count} over {self._max_attachments}')
        if byte_count > self._size_limit:
            raise PANHuntException(f'Attachment "{filename}" exceeds configured size limit')
        if self._decoded_attachment_bytes + byte_count > self._max_total_attachment_bytes:
            raise PANHuntException(f'Decoded attachment bytes exceed configured message limit for "{self.filename}"')
        if self._context:
            self._context.reserve_attachment(filename, byte_count, attachment_count)
        self._decoded_attachment_bytes += byte_count
        self.attachments.append(Attachment(filename=filename, payload=binary_data))

    def to_text(self) -> str:
        d: dict = {}
        d['filename'] = self.filename
        d['body'] = self.body
        d['attachments'] = []
        for a in self.attachments:
            d['attachments'].append(a.Filename)
        return json.dumps(d, sort_keys=True, indent=4)

    def __str__(self) -> str:

        return self.__text


class Attachment:

    Filename: str
    BinaryData: Optional[bytes] = None

    def __init__(self, filename: str, payload: bytes) -> None:
        self.Filename = filename
        if len(payload) > 0:
            self.BinaryData = payload
