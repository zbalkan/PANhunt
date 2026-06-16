import json
from email import message, parser
from typing import Optional

from ..exceptions import PANHuntException


class Eml:

    filename: str
    body: str
    attachments: list['Attachment']

    __text: str

    def __init__(self, path: str, payload: Optional[bytes] = None, size_limit: int = 1_073_741_824) -> None:
        if payload:
            msg = parser.BytesParser().parsebytes(payload)
        else:
            with open(path, "rb") as f:
                msg = parser.BytesParser().parse(f)

        self.filename = path
        self.body = ''
        self.attachments = []
        self._size_limit = size_limit
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

    def parse_body(self, body_payload) -> None:
        if isinstance(body_payload, message.Message):
            charset = body_payload.get_content_charset() or 'utf-8'
            decoded = body_payload.get_payload(decode=True)
            if decoded is None:
                self.body += str(body_payload.get_payload())
            else:
                self.body += decoded.decode(charset, errors='backslashreplace')
        elif isinstance(body_payload, str):
            self.body += body_payload

    def parse_attachment(self, attachment_payload: message.Message) -> None:
        filename = attachment_payload.get_filename() or '[NoFilename]'
        binary_data = attachment_payload.get_payload(decode=True)
        if binary_data is None:
            raw = attachment_payload.get_payload()
            binary_data = raw.encode('utf-8', errors='backslashreplace') if isinstance(raw, str) else bytes(raw)
        if len(binary_data) > self._size_limit:
            raise PANHuntException(f'Attachment "{filename}" exceeds configured size limit')
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
