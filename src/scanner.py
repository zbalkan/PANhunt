import io
import os
from abc import ABC, abstractmethod
from typing import Optional

from eml import Eml
from job import Job, JobQueue
from mbox import Mbox
from msmsg import MSMSG
from PAN import PAN
from patterns import CardPatterns
from pdf import Pdf
from pst import PST
from pst import Attachment as pstAttachment

''' If file size is 30MB or bigger, read line by line for better memory management '''
LARGE_FILE_LIMIT_BYTES: int = 31_457_280  # 30MB


class ScannerBase(ABC):

    filename: str
    sub_path: str = ''  # Only if it is a nested object
    encoding: str
    payload: Optional[bytes]

    patterns: CardPatterns

    def __init__(self, patterns: CardPatterns, encoding: str = 'utf8') -> None:
        self.encoding = encoding
        self.filename = ''
        self.patterns = patterns
        self.payload = None

    def from_file(self, path: str, sub_path: str = '') -> None:
        self.filename = path
        self.sub_path = sub_path

    def from_buffer(self, buffer: bytes) -> None:
        self.payload = buffer

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


class BasicFileScanner(ScannerBase):

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        matches: list[PAN] = []

        text: str
        if self.payload:

            text = self.payload.decode(
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


class MsgScanner(ScannerBase):

    __msg: Optional[MSMSG] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.__msg is None:
            if self.payload:
                self.__msg = MSMSG(msg_file_path=self.payload)
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
                    # Create a job for the attachment and add it to the JobQueue
                    job = Job(
                        filename=att.Filename,  # Use the attachment filename
                        file_dir=self.filename,  # The parent filename
                        payload=att.BinaryData  # Pass the binary content directly
                    )
                    JobQueue().enqueue(job)

        return matches


class EmlScanner(ScannerBase):
    __eml: Optional[Eml] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.__eml is None:
            if self.payload:
                self.__eml = Eml(path=self.filename,
                                 payload=self.payload)
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
                # Create a job for the attachment and add it to the JobQueue
                job = Job(
                    filename=att.Filename,  # Use the attachment filename
                    file_dir=self.filename,  # The parent filename
                    payload=att.BinaryData  # Pass the binary content directly
                )
                JobQueue().enqueue(job)

        return matches


class MboxScanner(ScannerBase):
    __mbox: Optional[Mbox] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.__mbox is None:
            if self.payload:
                self.__mbox = Mbox(path=self.filename,
                                   payload=self.payload)
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
                    # Create a job for the attachment and add it to the JobQueue
                    job = Job(
                        filename=att.Filename,  # Use the attachment filename
                        file_dir=self.filename,  # The parent filename
                        payload=att.BinaryData  # Pass the binary content directly
                    )
                    JobQueue().enqueue(job)

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
                                    # Create a job for the attachment and add it to the JobQueue
                                    job = Job(
                                        filename=att.Filename,  # Use the attachment filename
                                        file_dir=self.filename,  # The parent filename
                                        payload=att.BinaryData  # Pass the binary content directly
                                    )
                                    JobQueue().enqueue(job)
            self.pst.close()

        return matches


class PdfScanner(ScannerBase):
    pdf: Optional[Pdf] = None

    def scan(self, excluded_pans_list: list[str]) -> list[PAN]:

        if self.pdf is None:
            if self.payload:
                self.pdf = Pdf(file=io.BytesIO(initial_bytes=self.payload))
            else:
                self.pdf = Pdf(file=self.filename)

        ifs = SimpleTextScanner(patterns=self.patterns)
        ifs.filename = self.filename
        ifs.sub_path = self.sub_path
        ifs.text = self.pdf.get_text()

        matches: list[PAN] = ifs.scan(
            excluded_pans_list=excluded_pans_list)
        return matches
