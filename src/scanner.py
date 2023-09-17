import gzip
import io
import lzma
import os
import tarfile
import zipfile
from abc import ABC, abstractmethod
from typing import IO, Optional, Type, Union

import gzinfo

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


class ScannerBase(ABC):

    filename: str
    sub_path: str  # Only if it is a nested object
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
    # list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:
        # self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]
        raise NotImplementedError()


class SimpleTextScanner(ScannerBase):
    text: str

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        # list[PAN]
        matches: list = []
        for brand, regex in self.patterns.brands():
            # list[str]
            pans: list = regex.findall(self.text)
            if pans:
                for pan in pans:
                    if PAN.is_valid_luhn_checksum(pan=pan) and not PAN.is_excluded(pan=pan, excluded_pans=excluded_pans_list):
                        matches.append(
                            PAN(filename=os.path.basename(self.filename), sub_path=self.sub_path, brand=brand, pan=pan))
        return matches


class BasicScanner(ScannerBase):

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        # list[PAN]
        matches: list = []

        text: str
        if self.value_bytes:
            _, encoding = panutils.get_mime_data_from_buffer(
                value_bytes=self.value_bytes)
            text = self.value_bytes.decode(
                encoding=encoding, errors='backslashreplace')
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

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        # list[PAN]
        matches: list = []

        if self.attachment.BinaryData:
            mime_type, _ = panutils.get_mime_data_from_buffer(
                self.attachment.BinaryData)

            scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
                mime_type=mime_type, extension=panutils.get_ext(file_name=self.attachment.Filename))
            if scanner_init is None:
                return []

            scanner_instance = scanner_init(patterns=self.patterns)
            scanner_instance.from_file(
                path=self.filename, sub_path=self.attachment.Filename)
            scanner_instance.from_buffer(buffer=self.attachment.BinaryData)

            # list[PAN]
            res: list = scanner_instance.scan(
                excluded_pans_list=excluded_pans_list)
            if len(res) > 0:
                matches.extend(res)

        return matches


class MsgScanner(ScannerBase):

    __msg: Optional[MSMSG] = None

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        if self.__msg is None:
            if self.value_bytes:
                self.__msg = MSMSG(msg_file_path=self.value_bytes)
            else:
                self.__msg = MSMSG(msg_file_path=self.filename)

        # list[PAN]
        matches: list = []

        if self.__msg.validMSG:
            if self.__msg.Body:
                text_scanner = SimpleTextScanner(patterns=self.patterns)
                text_scanner.text = self.__msg.Body
                text_scanner.filename = self.filename

                # list[PAN]
                body_matches: list = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list)
                if len(body_matches) > 0:
                    matches.extend(body_matches)
            if self.__msg.attachments:
                for _, att in enumerate(iterable=self.__msg.attachments):
                    att_scanner = AttachmentScanner(patterns=self.patterns)
                    att_scanner.from_file(path=self.filename)
                    att_scanner.attachment = att

                    # list[PAN]
                    att_matches: list = att_scanner.scan(
                        excluded_pans_list=excluded_pans_list)
                    if len(att_matches) > 0:
                        matches.extend(att_matches)
        return matches


class EmlScanner(ScannerBase):
    __eml: Optional[Eml] = None

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        if self.__eml is None:
            if self.value_bytes:
                self.__eml = Eml(path=self.filename,
                                 value_bytes=self.value_bytes)
            else:
                self.__eml = Eml(path=self.filename)

        # list[PAN]
        matches: list = []

        if self.__eml.body:
            text_scanner = SimpleTextScanner(patterns=self.patterns)
            text_scanner.from_file(path=self.filename)
            text_scanner.text = self.__eml.body

            # list[PAN]
            body_matches: list = text_scanner.scan(
                excluded_pans_list=excluded_pans_list)
            if len(body_matches) > 0:
                matches.extend(body_matches)
        if self.__eml.attachments:
            for _, att in enumerate(iterable=self.__eml.attachments):
                att_scanner = AttachmentScanner(patterns=self.patterns)
                att_scanner.from_file(path=self.filename)
                att_scanner.attachment = att

                # list[PAN]
                att_matches: list = att_scanner.scan(
                    excluded_pans_list=excluded_pans_list)
                if len(att_matches) > 0:
                    matches.extend(att_matches)
        return matches


class MboxScanner(ScannerBase):
    __mbox: Optional[Mbox] = None

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        if self.__mbox is None:
            if self.value_bytes:
                self.__mbox = Mbox(path=self.filename,
                                   value_bytes=self.value_bytes)
            else:
                self.__mbox = Mbox(path=self.filename)

        # list[PAN]
        matches: list = []

        for mail in self.__mbox.mails:
            if mail.body:
                text_scanner = SimpleTextScanner(patterns=self.patterns)
                text_scanner.text = mail.body
                # list[PAN]
                body_matches: list = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list)
                if len(body_matches) > 0:
                    matches.extend(body_matches)
            if mail.attachments:
                for _, att in enumerate(iterable=mail.attachments):
                    att_scanner = AttachmentScanner(patterns=self.patterns)
                    att_scanner.from_file(path=self.filename)
                    att_scanner.attachment = att
                    # list[PAN]
                    att_matches: list = att_scanner.scan(
                        excluded_pans_list=excluded_pans_list)
                    if len(att_matches) > 0:
                        matches.extend(att_matches)

        return matches


class PstScanner(ScannerBase):
    pst: Optional[PST] = None

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        if self.pst is None:
            self.pst = PST(pst_file=self.filename)

        # list[PAN]
        matches: list = []

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

                        # list[PAN]
                        body_matches: list = text_scanner.scan(
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

                                    # list[PAN]
                                    att_matches: list = att_scanner.scan(
                                        excluded_pans_list=excluded_pans_list)
                                    if len(att_matches) > 0:
                                        matches.extend(att_matches)
            self.pst.close()

        return matches


class ZipScanner(ScannerBase):

    __zip_file: Optional[zipfile.ZipFile] = None

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        if self.__zip_file is None:
            if self.value_bytes:
                self.__zip_file = zipfile.ZipFile(
                    file=io.BytesIO(initial_bytes=self.value_bytes))
            else:
                self.__zip_file = zipfile.ZipFile(file=self.filename)

        # list[PAN]
        matches: list = []

        # list[str]
        files_in_zip: list = [file_in_zip for file_in_zip in self.__zip_file.namelist(
        )]

        for file_in_zip in files_in_zip:
            b: bytes = self.__zip_file.open(name=file_in_zip).read()
            if b:
                mime_type, _ = panutils.get_mime_data_from_buffer(
                    value_bytes=b)

                scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
                    mime_type=mime_type, extension=panutils.get_ext(file_name=file_in_zip))
                if scanner_init is None:
                    return []

                scanner_instance = scanner_init(patterns=self.patterns)
                scanner_instance.from_file(
                    path=self.filename, sub_path=file_in_zip)
                scanner_instance.from_buffer(buffer=b)

                # list[PAN]
                res: list = scanner_instance.scan(
                    excluded_pans_list=excluded_pans_list)
                if len(res) > 0:
                    matches.extend(res)
        return matches


class TarScanner(ScannerBase):

    __archive_file: Optional[tarfile.TarFile] = None

    def scan(self, excluded_pans_list: list) -> list:

        if self.__archive_file is None:
            if self.value_bytes:
                file_like_object = io.BytesIO(initial_bytes=self.value_bytes)
                self.__archive_file = tarfile.open(
                    fileobj=file_like_object)
            else:
                self.__archive_file = tarfile.open(name=self.filename)

        matches: list = []

        files_in_archive: list[tarfile.TarInfo] = [
            m for m in self.__archive_file.getmembers() if m.isfile()]

        for member in files_in_archive:

            extracted: Optional[IO[bytes]] = self.__archive_file.extractfile(
                member=member)
            if extracted is None:
                continue
            b: bytes = extracted.read()

            if b:
                mime_type, _ = panutils.get_mime_data_from_buffer(
                    value_bytes=b)

                scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
                    mime_type=mime_type, extension=panutils.get_ext(file_name=member.name))
                if scanner_init is None:
                    return []

                scanner_instance = scanner_init(patterns=self.patterns)
                scanner_instance.from_file(
                    path=self.filename, sub_path=member.name)
                scanner_instance.from_buffer(buffer=b)

                res: list = scanner_instance.scan(
                    excluded_pans_list=excluded_pans_list)
                if len(res) > 0:
                    matches.extend(res)
        return matches


class GzipScanner(ScannerBase):

    __gz_file: Optional[gzip.GzipFile] = None

    def scan(self, excluded_pans_list: list) -> list:

        if self.__gz_file is None:
            if self.value_bytes:
                file_like_object = io.BytesIO(initial_bytes=self.value_bytes)
                self.__gz_file = gzip.GzipFile(
                    fileobj=file_like_object)
            else:
                self.__gz_file = gzip.GzipFile(filename=self.filename)

        matches: list = []
        b: bytes = self.__gz_file.read1()
        gz_info = gzinfo.read_gz_info(filename=self.filename)
        if gz_info:
            compressed_filename: str = gz_info.fname
        else:
            compressed_filename = self.filename.replace('.gz', '')

        if b:
            mime_type, _ = panutils.get_mime_data_from_buffer(
                value_bytes=b)

            scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
                mime_type=mime_type, extension=panutils.get_ext(file_name=compressed_filename))
            if scanner_init is None:
                return []

            scanner_instance = scanner_init(patterns=self.patterns)
            scanner_instance.from_file(
                path=self.filename, sub_path=compressed_filename)
            scanner_instance.from_buffer(buffer=b)

            res: list = scanner_instance.scan(
                excluded_pans_list=excluded_pans_list)
            if len(res) > 0:
                matches.extend(res)
        return matches


class XzScanner(ScannerBase):

    __xz_file: Optional[lzma.LZMAFile] = None

    def scan(self, excluded_pans_list: list) -> list:

        if self.__xz_file is None:
            if self.value_bytes:
                file_like_object = io.BytesIO(initial_bytes=self.value_bytes)
                self.__xz_file = lzma.LZMAFile(filename=file_like_object)
            else:
                self.__xz_file = lzma.LZMAFile(filename=self.filename)

        matches: list = []
        b: bytes = self.__xz_file.read1()

        compressed_filename: str = self.filename.replace('.xz', '')

        if b:
            mime_type, _ = panutils.get_mime_data_from_buffer(
                value_bytes=b)

            scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
                mime_type=mime_type, extension=panutils.get_ext(file_name=compressed_filename))
            if scanner_init is None:
                return []

            scanner_instance = scanner_init(patterns=self.patterns)
            scanner_instance.from_file(
                path=self.filename, sub_path=compressed_filename)
            scanner_instance.from_buffer(buffer=b)

            res: list = scanner_instance.scan(
                excluded_pans_list=excluded_pans_list)
            if len(res) > 0:
                matches.extend(res)
        return matches


class PdfScanner(ScannerBase):
    pdf: Optional[Pdf] = None

    # def scan(self, excluded_pans_list: list[str][FileCategoryEnum, list[str]]) -> list[PAN]:
    def scan(self, excluded_pans_list: list) -> list:

        if self.pdf is None:
            if self.value_bytes:
                self.pdf = Pdf(file=io.BytesIO(initial_bytes=self.value_bytes))
            else:
                self.pdf = Pdf(file=self.filename)

        ifs = SimpleTextScanner(patterns=self.patterns)
        ifs.filename = self.filename
        ifs.sub_path = self.sub_path
        ifs.text = self.pdf.get_text()

        # list[PAN]
        matches: list = ifs.scan(
            excluded_pans_list=excluded_pans_list)
        return matches
