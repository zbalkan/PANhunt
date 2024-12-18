import base64
import io
import json
import logging
import quopri
from email import message, parser
from typing import Any, Optional


class Eml:

    filename: str
    body: str
    attachments: list['Attachment']

    __text: str

    def __init__(self, path: str, payload: Optional[bytes] = None) -> None:
        msg: message.Message
        if payload:
            msg = parser.BytesParser().parsebytes(payload)
        else:
            f: io.BufferedReader = open(path, "rb")
            msg = parser.BytesParser().parse(f)
            f.close()

        self.filename = path
        payloads: Any = msg.get_payload()
        if isinstance(payloads, list):
            self.body = ''
            self.attachments = []
            self.extract_body_parts(payloads)
            self.extract_attachments(payloads)
            self.__text = self.to_text()
        else:
            raise TypeError(msg)

    def extract_body_parts(self, payloads) -> None:
        body_data: message.Message = payloads[0]
        body_payloads = body_data.get_payload()
        if isinstance(body_payloads, list):
            for body_payload in body_payloads:
                self.parse_body(body_payload)
        else:
            self.parse_body(body_payloads)

    def extract_attachments(self, payloads) -> None:
        attachment_payloads: Any = payloads[1:]
        for attachment in attachment_payloads:
            if isinstance(attachment, list):
                for att_payload in attachment:
                    self.parse_attachment(att_payload)
            else:
                self.parse_attachment(attachment)

    def parse_body(self, body_payload: Any) -> None:
        if isinstance(body_payload, message.Message):
            headers: dict = dict(body_payload._headers)  # type: ignore

            content_type: list[str] = str(
                headers.get('Content-Type')).split(';')

            if content_type[0] == 'text/plain':
                charset: str = content_type[1].lstrip().removeprefix(
                    'charset=\"').removesuffix('\"').lower()
                if charset == "utf-8":
                    self.body += str(body_payload.get_payload())
                else:
                    utf8_text: str = str(body_payload.get_payload()).encode(
                        charset).decode('utf-8')
                    self.body += utf8_text
        elif isinstance(body_payload, str):
            self.body += body_payload
        else:
            logging.error(f"Unknown body type: {type(body_payload)}")

    def parse_attachment(self, attachment_payload: Any) -> None:
        headers = dict(attachment_payload._headers)
        filename: str = str(
            headers.get('Content-Disposition'))\
            .removeprefix('attachment;')\
            .removeprefix('\n')\
            .removeprefix('\t')\
            .removeprefix(' ')\
            .removeprefix('filename=')\
            .removeprefix('\"')\
            .removesuffix('"')

        encoding: str = str(headers.get('Content-Transfer-Encoding'))

        if encoding == 'base64':
            data = str(attachment_payload.get_payload())
            binary_data: bytes = base64.b64decode(data)
            self.attachments.append(Attachment(
                filename=filename, payload=binary_data))
        elif encoding == "7bit" or encoding == 'quoted-printable' or encoding == 'None':
            raw = str(attachment_payload.get_payload())
            decoded: bytes = quopri.decodestring(raw)
            self.attachments.append(Attachment(
                filename=filename, payload=decoded))
        else:
            raise NotImplementedError(encoding)

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
