import base64
import json
import mailbox
import quopri
from typing import IO, Any, Optional


class Mbox:

    filename: str
    mails: list  # list['Mail']

    def __init__(self, path: str, value_bytes: Optional[bytes] = None) -> None:
        self.filename = path
        self.mails = []
        mbox: mailbox.mbox
        mbox = mailbox.mbox(path)
        if value_bytes:
            mailbox.mbox(path=path,
                         factory=self.__from_buffer)

        for message in mbox:
            self.mails.append(Mail(message))

    def __from_buffer(self, buffer: IO[Any]) -> mailbox.mboxMessage:
        b: bytes = buffer.read()
        m = mailbox.mboxMessage(message=b)
        return m

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
    attachments: list  # list['Attachment']

    def __init__(self, message: mailbox.mboxMessage) -> None:
        self.subject = self.get_subject(message)
        payloads: Any = message.get_payload()

        if isinstance(payloads, list):
            self.body = ''
            self.attachments = []
            self.extract_body_parts(payloads)
            self.extract_attachments(payloads)
        elif isinstance(payloads, str):
            self.body = payloads
            self.attachments = []
        else:
            raise TypeError(message)

    def get_subject(self, message: mailbox.mboxMessage) -> str:
        headers = dict(message._headers)  # type: ignore
        return str(headers.get('Subject'))

    def extract_body_parts(self, payloads) -> None:
        body_data: Any = payloads[0]
        body_payloads: Any = body_data.get_payload()
        if isinstance(body_payloads, list):
            for body_payload in body_payloads:
                self.parse_body(body_payload)
        if isinstance(body_payloads, str):
            self.body = body_payloads
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
        # Body can be a list of messages when it is signed
        # PGP signed messages are enveloped with two parts: signature and signed message
        body_payload_list: list = []
        if isinstance(body_payload, list):
            body_payload_list = body_payload
        else:
            body_payload_list.append(body_payload)
        for bp in body_payload_list:
            headers: dict = dict(bp._headers)

            # list[str]
            content_type: list = str(
                headers.get('Content-Type')).split(';')

            if content_type[0] == 'text/plain':
                charset: str = content_type[1].lstrip().removeprefix('\n').removeprefix('\t').removeprefix(
                    'charset=').removeprefix('\"').removesuffix('\"').lower()
                if charset == "utf-8":
                    self.body += str(bp.get_payload())
                else:
                    utf8_text: str = str(bp.get_payload()).encode(
                        charset).decode('utf-8')
                    self.body += utf8_text

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
            raw = str(attachment_payload.get_payload())
            binary_data: bytes = base64.b64decode(raw)
            self.attachments.append(Attachment(
                filename=filename, value_bytes=binary_data))
        elif encoding == "7bit" or encoding == 'quoted-printable' or encoding == 'None':
            if str(headers.get('Content-Type')).split(';')[0] == 'application/pgp-signature':
                # Ignore signatures
                return
            else:
                raw = str(attachment_payload.get_payload())
                decoded: bytes = quopri.decodestring(raw)
                self.attachments.append(Attachment(
                    filename=filename, value_bytes=decoded))
        else:
            raise NotImplementedError(encoding)

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

    def __init__(self, filename: str, value_bytes: bytes) -> None:
        self.Filename = filename
        if len(value_bytes) > 0:
            self.BinaryData = value_bytes
