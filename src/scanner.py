import io
import os
import zipfile
from abc import ABC, abstractmethod
from typing import Final, Optional, Type

import mappings
import panutils
from eml import Attachment as emlAttachment
from eml import Eml
from enums import FileCategoryEnum
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
LARGE_FILE_LIMIT_BYTES: Final[int] = 31_457_280  # 30MB


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
    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        raise NotImplementedError()


class SimpleTextScanner(ScannerBase):
    text: str

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        matches: list[PAN] = []
        for brand, regex in self.patterns.brands():
            pans: list[str] = regex.findall(self.text)
            if pans:
                for pan in pans:
                    if PAN.is_valid_luhn_checksum(pan) and not PAN.is_excluded(pan, excluded_pans_list):
                        matches.append(
                            PAN(os.path.basename(self.filename), self.sub_path, brand, pan))
        return matches


class BasicScanner(ScannerBase):

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        matches: list[PAN] = []

        text:str
        if self.value_bytes:
            text = self.value_bytes.decode('utf-8')
            ifs = SimpleTextScanner(patterns=self.patterns)
            ifs.from_file(path=self.filename, sub_path=self.sub_path)
            ifs.text = text
            matches.extend(ifs.scan(
                        excluded_pans_list=excluded_pans_list, search_extensions=search_extensions))
        else:
            s: os.stat_result = os.stat(self.filename)
            file_size: int = s.st_size

            if file_size == 0:
                return []


            if 0 < file_size < LARGE_FILE_LIMIT_BYTES:
                with open(self.filename, 'r', encoding=self.encoding, errors='backslashreplace') as f:
                    text = f.read()

                ifs = SimpleTextScanner(patterns=self.patterns)
                ifs.from_file(path=self.filename, sub_path=self.sub_path)
                ifs.text = text
                matches.extend(ifs.scan(
                        excluded_pans_list=excluded_pans_list, search_extensions=search_extensions))
            else:
                with open(self.filename, 'r', encoding=self.encoding, errors='backslashreplace') as f:
                    for line in f:
                        ifs = SimpleTextScanner(patterns=self.patterns)
                        ifs.from_file(path=self.filename, sub_path=self.sub_path)
                        ifs.text = line
                        matches.extend(ifs.scan(
                                excluded_pans_list=excluded_pans_list, search_extensions=search_extensions))
        return matches


class AttachmentScanner(ScannerBase):
    attachment: msgAttachment | pstAttachment | emlAttachment | mboxAttachment

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        match_list: list[PAN] = []

        if self.attachment.BinaryData:
            mime_type, _ = panutils.get_mime_data_from_buffer(
                self.attachment.BinaryData)

            scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
                mime_type=mime_type, extension=panutils.get_ext(self.attachment.Filename))
            if scanner_init is None:
                return []

            scanner_instance = scanner_init(patterns=self.patterns)
            scanner_instance.from_file(
                path=self.filename, sub_path=self.attachment.Filename)
            scanner_instance.from_buffer(self.attachment.BinaryData)
            res: list[PAN] = scanner_instance.scan(
                excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
            if len(res) > 0:
                match_list.extend(res)

        return match_list


class MsgScanner(ScannerBase):

    __msg: Optional[MSMSG] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        if self.__msg is None:
            if self.value_bytes:
                self.__msg = MSMSG(msg_file_path=self.value_bytes)
            else:
                self.__msg = MSMSG(msg_file_path=self.filename)

        match_list: list[PAN] = []

        if self.__msg.validMSG:
            if self.__msg.Body:
                text_scanner = SimpleTextScanner(patterns=self.patterns)
                text_scanner.text = self.__msg.Body
                text_scanner.filename = self.filename
                body_matches: list[PAN] = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(body_matches) > 0:
                    match_list.extend(body_matches)
            if self.__msg.attachments:
                for _, att in enumerate(self.__msg.attachments):
                    att_scanner = AttachmentScanner(patterns=self.patterns)
                    att_scanner.from_file(path=self.filename)
                    att_scanner.attachment = att
                    att_matches: list[PAN] = att_scanner.scan(
                        excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                    if len(att_matches) > 0:
                        match_list.extend(att_matches)
        return match_list


class EmlScanner(ScannerBase):
    __eml: Optional[Eml] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        if self.__eml is None:
            if self.value_bytes:
                self.__eml = Eml(path=self.filename, value_bytes=self.value_bytes)
            else:
                self.__eml = Eml(path=self.filename)

        match_list: list[PAN] = []

        if self.__eml.body:
            text_scanner = SimpleTextScanner(patterns=self.patterns)
            text_scanner.from_file(path=self.filename)
            text_scanner.text = self.__eml.body
            body_matches: list[PAN] = text_scanner.scan(
                excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
            if len(body_matches) > 0:
                match_list.extend(body_matches)
        if self.__eml.attachments:
            for _, att in enumerate(self.__eml.attachments):
                att_scanner = AttachmentScanner(patterns=self.patterns)
                att_scanner.from_file(path=self.filename)
                att_scanner.attachment = att
                att_matches: list[PAN] = att_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(att_matches) > 0:
                    match_list.extend(att_matches)
        return match_list


class MboxScanner(ScannerBase):
    __mbox: Optional[Mbox] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        if self.__mbox is None:
            if self.value_bytes:
                self.__mbox = Mbox(path= self.filename, value_bytes=self.value_bytes)
            else:
                self.__mbox = Mbox(self.filename)

        match_list: list[PAN] = []

        for mail in self.__mbox.mails:
            if mail.body:
                text_scanner = SimpleTextScanner(patterns=self.patterns)
                text_scanner.text = mail.body
                body_matches: list[PAN] = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(body_matches) > 0:
                    match_list.extend(body_matches)
            if mail.attachments:
                for _, att in enumerate(mail.attachments):
                    att_scanner = AttachmentScanner(patterns=self.patterns)
                    att_scanner.from_file(path=self.filename)
                    att_scanner.attachment = att
                    att_matches: list[PAN] = att_scanner.scan(
                        excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                    if len(att_matches) > 0:
                        match_list.extend(att_matches)

        return match_list


class PstScanner(ScannerBase):
    pst: Optional[PST] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        if self.pst is None:
            self.pst = PST(self.filename)

        match_list: list[PAN] = []

        if self.pst.header.validPST:
            for folder in self.pst.folder_generator():
                for message in self.pst.message_generator(folder):
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
                            excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                        if len(body_matches) > 0:
                            match_list.extend(body_matches)

                    if message.HasAttachments:
                        for _, subattachment in enumerate(message.subattachments):
                            if subattachment.Filename and panutils.get_ext(subattachment.Filename) in search_extensions[FileCategoryEnum.Text] + search_extensions[FileCategoryEnum.Zip]:
                                att: Optional[pstAttachment] = message.get_attachment(
                                    subattachment=subattachment)
                                if att:
                                    att_scanner = AttachmentScanner(
                                        patterns=self.patterns)
                                    att_scanner.from_file(path=self.filename)
                                    att_scanner.attachment = att
                                    att_matches: list[PAN] = att_scanner.scan(
                                        excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                                    if len(att_matches) > 0:
                                        match_list.extend(att_matches)
            self.pst.close()

        return match_list


class ZipScanner(ScannerBase):

    __zip_file: Optional[zipfile.ZipFile] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        if self.__zip_file is None:
            if self.value_bytes:
                self.__zip_file = zipfile.ZipFile(file=io.BytesIO(self.value_bytes))
            else:
                self.__zip_file = zipfile.ZipFile(file=self.filename)

        match_list: list[PAN] = []

        all_extensions: list[str] = [ext for ext_list in list(
            search_extensions.values()) for ext in ext_list]

        files_in_zip: list[str] = [file_in_zip for file_in_zip in self.__zip_file.namelist(
        ) if panutils.get_ext(file_in_zip) in all_extensions]

        for file_in_zip in files_in_zip:
            b: bytes = self.__zip_file.open(name=file_in_zip).read()
            if b:
                mime_type, _ = panutils.get_mime_data_from_buffer(b)

                scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
                    mime_type=mime_type, extension=panutils.get_ext(file_in_zip))
                if scanner_init is None:
                    return []

                scanner_instance = scanner_init(patterns=self.patterns)
                scanner_instance.from_file(
                    path=self.filename, sub_path=file_in_zip)
                scanner_instance.from_buffer(b)
                res: list[PAN] = scanner_instance.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(res) > 0:
                    match_list.extend(res)
        return match_list


class PdfScanner(ScannerBase):
    pdf: Optional[Pdf] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]]) -> list[PAN]:
        if self.pdf is None:
            if self.value_bytes:
                self.pdf = Pdf(io.BytesIO(self.value_bytes))
            else:
                self.pdf = Pdf(self.filename)

        ifs = SimpleTextScanner(patterns=self.patterns)
        ifs.filename = self.filename
        ifs.sub_path = self.sub_path
        ifs.text = self.pdf.get_text()
        matches: list[PAN] = ifs.scan(
            excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
        return matches
