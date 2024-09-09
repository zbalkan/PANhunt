import io
import os
from abc import ABC, abstractmethod
from typing import Optional, Type, Union

import mappings
import panutils
from eml import Attachment as emlAttachment
from eml import Eml
from mbox import Attachment as mboxAttachment
from mbox import Mbox
from msmsg import MSMSG
from msmsg import Attachment as msgAttachment
from PAN import PAN
from patterns import CardPatterns
from pdf import Pdf
from pst import PST
from pst import Attachment as pstAttachment

''' If file size is 30MB or bigger, read line by line for better memory management '''
LARGE_FILE_LIMIT_BYTES: int = 31_457_280  # 30MB
# TODO: Return ScannableFile instead of PAN
# TODO: Accept Job as input instead of filename and value_bytes


class ScannerBase(ABC):

    filename: str
    sub_path: str = ''  # Only if it is a nested object
    encoding: str
    value_bytes: Optional[bytes]

    patterns: CardPatterns

    def __init__(self, patterns: CardPatterns, encoding: str = 'utf8') -> None:
        self.encoding = encoding
        self.filename = ''
        self.patterns = patterns
        self.value_bytes = None

    def from_file(self, path: str, sub_path: str = '') -> None:
        self.filename = path
        self.sub_path = sub_path

    def from_buffer(self, buffer: bytes) -> None:
        self.value_bytes = buffer

    @abstractmethod
    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:
        raise NotImplementedError()


class SimpleTextScanner(ScannerBase):
    text: str

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        matches: list[PAN] = []
        for brand, regex in self.patterns.brands():
            pans: list[str] = regex.findall(self.text)
            if pans:
                for pan in pans:
                    if PAN.is_valid_luhn_checksum(pan=pan) and not PAN.is_excluded(pan=pan, excluded_pans=excluded_pans_list):
                        matches.append(
                            PAN(filename=os.path.basename(self.filename), sub_path=self.sub_path, brand=brand, pan=pan))
        return matches


class BasicScanner(ScannerBase):

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        matches: list[PAN] = []

        text: str
        if self.value_bytes:

            text = self.value_bytes.decode(
                encoding=self.encoding, errors='backslashreplace')
            ifs = SimpleTextScanner(patterns=self.patterns)
            ifs.from_file(path=self.filename, sub_path=self.sub_path)
            ifs.text = text
            matches.extend(ifs.scan(
                excluded_pans_list=excluded_pans_list))
        else:
            s: os.stat_result = os.stat(path=self.filename)
            file_size: int = s.st_size

            if file_size == 0:
                return []

            if 0 < file_size < LARGE_FILE_LIMIT_BYTES:
                with open(file=self.filename, mode='r', encoding=self.encoding, errors='backslashreplace') as f:
                    text = f.read()

                ifs = SimpleTextScanner(patterns=self.patterns)
                ifs.from_file(path=self.filename, sub_path=self.sub_path)
                ifs.text = text
                matches.extend(ifs.scan(
                    excluded_pans_list=excluded_pans_list))
            else:
                with open(file=self.filename, mode='r', encoding=self.encoding, errors='backslashreplace') as f:
                    for line in f:
                        ifs = SimpleTextScanner(patterns=self.patterns)
                        ifs.from_file(path=self.filename,
                                      sub_path=self.sub_path)
                        ifs.text = line
                        matches.extend(ifs.scan(
                            excluded_pans_list=excluded_pans_list))
        return matches


class AttachmentScanner(ScannerBase):
    attachment: Union[msgAttachment, pstAttachment,
                      emlAttachment, mboxAttachment]

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        matches: list[PAN] = []

        if self.attachment.BinaryData:
            mime_type, _ = panutils.__get_mime_data_from_buffer(
                self.attachment.BinaryData)

            scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
                mime_type=mime_type, extension=panutils.get_ext(file_name=self.attachment.Filename))
            if scanner_init is None:
                return []

            scanner_instance = scanner_init(patterns=self.patterns)
            scanner_instance.from_file(
                path=self.filename, sub_path=self.attachment.Filename)
            scanner_instance.from_buffer(buffer=self.attachment.BinaryData)

            res: list[PAN] = scanner_instance.scan(
                excluded_pans_list=excluded_pans_list)
            if len(res) > 0:
                matches.extend(res)

        return matches


class MsgScanner(ScannerBase):

    __msg: Optional[MSMSG] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.__msg is None:
            if self.value_bytes:
                self.__msg = MSMSG(msg_file_path=self.value_bytes)
            else:
                self.__msg = MSMSG(msg_file_path=self.filename)

        matches: list[PAN] = []

        if self.__msg.validMSG:
            if self.__msg.Body:
                text_scanner = SimpleTextScanner(patterns=self.patterns)
                text_scanner.text = self.__msg.Body
                text_scanner.filename = self.filename

                body_matches: list[PAN] = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list)
                if len(body_matches) > 0:
                    matches.extend(body_matches)
            if self.__msg.attachments:
                for _, att in enumerate(iterable=self.__msg.attachments):
                    att_scanner = AttachmentScanner(patterns=self.patterns)
                    att_scanner.from_file(path=self.filename)
                    att_scanner.attachment = att

                    att_matches: list[PAN] = att_scanner.scan(
                        excluded_pans_list=excluded_pans_list)
                    if len(att_matches) > 0:
                        matches.extend(att_matches)
        return matches


class EmlScanner(ScannerBase):
    __eml: Optional[Eml] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.__eml is None:
            if self.value_bytes:
                self.__eml = Eml(path=self.filename,
                                 value_bytes=self.value_bytes)
            else:
                self.__eml = Eml(path=self.filename)

        matches: list[PAN] = []

        if self.__eml.body:
            text_scanner = SimpleTextScanner(patterns=self.patterns)
            text_scanner.from_file(path=self.filename)
            text_scanner.text = self.__eml.body

            body_matches: list[PAN] = text_scanner.scan(
                excluded_pans_list=excluded_pans_list)
            if len(body_matches) > 0:
                matches.extend(body_matches)
        if self.__eml.attachments:
            for _, att in enumerate(iterable=self.__eml.attachments):
                att_scanner = AttachmentScanner(patterns=self.patterns)
                att_scanner.from_file(path=self.filename)
                att_scanner.attachment = att

                att_matches: list[PAN] = att_scanner.scan(
                    excluded_pans_list=excluded_pans_list)
                if len(att_matches) > 0:
                    matches.extend(att_matches)
        return matches


class MboxScanner(ScannerBase):
    __mbox: Optional[Mbox] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.__mbox is None:
            if self.value_bytes:
                self.__mbox = Mbox(path=self.filename,
                                   value_bytes=self.value_bytes)
            else:
                self.__mbox = Mbox(path=self.filename)

        matches: list[PAN] = []

        for mail in self.__mbox.mails:
            if mail.body:
                text_scanner = SimpleTextScanner(patterns=self.patterns)
                text_scanner.text = mail.body
                body_matches: list[PAN] = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list)
                if len(body_matches) > 0:
                    matches.extend(body_matches)
            if mail.attachments:
                for _, att in enumerate(iterable=mail.attachments):
                    att_scanner = AttachmentScanner(patterns=self.patterns)
                    att_scanner.from_file(path=self.filename)
                    att_scanner.attachment = att
                    att_matches: list[PAN] = att_scanner.scan(
                        excluded_pans_list=excluded_pans_list)
                    if len(att_matches) > 0:
                        matches.extend(att_matches)

        return matches


class PstScanner(ScannerBase):
    pst: Optional[PST] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.pst is None:
            self.pst = PST(pst_file=self.filename)

        matches: list[PAN] = []

        if self.pst.header.validPST:
            for folder in self.pst.folder_generator():
                for message in self.pst.message_generator(folder=folder):
                    if message.Subject:
                        message_path: str = os.path.join(
                            folder.path, message.Subject)
                    else:
                        message_path = os.path.join(
                            folder.path, '[NoSubject]')

                    if message.Body:
                        text_scanner = SimpleTextScanner(
                            patterns=self.patterns)
                        text_scanner.text = message.Body
                        text_scanner.filename = self.filename
                        text_scanner.sub_path = message_path

                        body_matches: list[PAN] = text_scanner.scan(
                            excluded_pans_list=excluded_pans_list)
                        if len(body_matches) > 0:
                            matches.extend(body_matches)

                    if message.HasAttachments:
                        for _, subattachment in enumerate(message.subattachments):
                            if subattachment.Filename:
                                att: Optional[pstAttachment] = message.get_attachment(
                                    subattachment=subattachment)
                                if att:
                                    att_scanner = AttachmentScanner(
                                        patterns=self.patterns)
                                    att_scanner.from_file(path=self.filename)
                                    att_scanner.attachment = att

                                    att_matches: list[PAN] = att_scanner.scan(
                                        excluded_pans_list=excluded_pans_list)
                                    if len(att_matches) > 0:
                                        matches.extend(att_matches)
            self.pst.close()

        return matches


class PdfScanner(ScannerBase):
    pdf: Optional[Pdf] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.pdf is None:
            if self.value_bytes:
                self.pdf = Pdf(file=io.BytesIO(initial_bytes=self.value_bytes))
            else:
                self.pdf = Pdf(file=self.filename)

        ifs = SimpleTextScanner(patterns=self.patterns)
        ifs.filename = self.filename
        ifs.sub_path = self.sub_path
        ifs.text = self.pdf.get_text()

        matches: list[PAN] = ifs.scan(
            excluded_pans_list=excluded_pans_list)
        return matches
