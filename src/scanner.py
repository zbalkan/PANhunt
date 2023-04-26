import io
import os
import zipfile
from abc import ABC, abstractmethod
from typing import Optional, Type

import panutils
from eml import Attachment as emlAttachment
from eml import Eml
from enums import FileTypeEnum
from mbox import Attachment as mboxAttachment
from mbox import Mbox
from msmsg import MSMSG
from msmsg import Attachment as msgAttachment
from PAN import PAN
from patterns import CardPatterns
from pst import PST
from pst import Attachment as pstAttachment


class _ScannerBase(ABC):

    filename: str
    sub_path: str = ''  # Only if it is a nested object
    patterns: CardPatterns

    def __init__(self, path: str = '') -> None:
        self.filename = path
        self.patterns = CardPatterns()

    @abstractmethod
    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        raise NotImplementedError()


class _InFileScanner(_ScannerBase):
    text: str

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        matches: list[PAN] = []
        for brand, regex in self.patterns.brands():
            pans: list[str] = regex.findall(self.text)
            if pans:
                for pan in pans:
                    if PAN.is_valid_luhn_checksum(pan) and not PAN.is_excluded(pan, excluded_pans_list):
                        matches.append(
                            PAN(os.path.basename(self.filename), self.sub_path, brand, pan))
        return matches


class _BasicScanner(_ScannerBase):

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        with open(self.filename, 'r', encoding='utf-8', errors='backslashreplace') as f:
            text: str = f.read()

        ifs = _InFileScanner()
        ifs.filename = self.filename
        ifs.sub_path = self.sub_path
        ifs.text = text
        matches: list[PAN] = ifs.scan(
            excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
        return matches


class _AttachmentScanner(_ScannerBase):
    attachment: msgAttachment | pstAttachment | emlAttachment | mboxAttachment

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        match_list: list[PAN] = []

        attachment_ext: str = panutils.get_ext(self.attachment.Filename)
        if attachment_ext in search_extensions[FileTypeEnum.Text]:
            if self.attachment.BinaryData:
                text_scanner = _InFileScanner()
                text_scanner.text = self.attachment.BinaryData.decode(
                    'utf-8', errors='backslashreplace')
                text_scanner.filename = self.filename
                text_scanner.sub_path = self.attachment.Filename
                text_matches: list[PAN] = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(text_matches) > 0:
                    match_list.extend(text_matches)

        elif attachment_ext in search_extensions[FileTypeEnum.Zip]:
            if self.attachment.BinaryData:
                zip_scanner = _ZipScanner(path=self.attachment.Filename)
                zip_scanner.zip_file = zipfile.ZipFile(
                    io.BytesIO(self.attachment.BinaryData))
                zip_scanner.filename = self.attachment.Filename
                zip_scanner.sub_path = self.attachment.Filename
                zip_matches: list[PAN] = zip_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)

                if len(zip_matches) > 0:
                    match_list.extend(zip_matches)

        elif attachment_ext in search_extensions[FileTypeEnum.Mail]:
            if self.attachment.BinaryData:
                msg_scanner = _MessageScanner(path=self.attachment.Filename)
                msg_scanner.sub_path = os.path.join(
                    os.path.basename(self.filename), self.attachment.Filename)
                msg_matches: list[PAN] = msg_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)

                if len(msg_matches) > 0:
                    match_list.extend(msg_matches)

        return match_list


class _MessageScanner(_ScannerBase):
    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        _, extension = os.path.splitext(self.filename.lower())
        if extension == '.msg':
            return _MsgScanner(path=self.filename).scan(excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
        else:
            return _EmlScanner(path=self.filename).scan(excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)


class _MsgScanner(_ScannerBase):
    msg: Optional[MSMSG] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        match_list: list[PAN] = []

        if self.msg is None:
            self.msg = MSMSG(self.filename)

        if self.msg.Body:
            text_scanner = _InFileScanner()
            text_scanner.text = self.msg.Body
            text_scanner.filename = self.filename
            body_matches: list[PAN] = text_scanner.scan(
                excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
            if len(body_matches) > 0:
                match_list.extend(body_matches)
        if self.msg.attachments:
            for _, att in enumerate(self.msg.attachments):
                att_scanner = _AttachmentScanner(path=self.filename)
                att_scanner.attachment = att
                att_matches: list[PAN] = att_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(att_matches) > 0:
                    match_list.extend(att_matches)
        return match_list


class _EmlScanner(_ScannerBase):
    eml: Optional[Eml] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        match_list: list[PAN] = []

        if self.eml is None:
            self.eml = Eml(self.filename)

        if self.eml.body:
            text_scanner = _InFileScanner()
            text_scanner.text = self.eml.body
            text_scanner.filename = self.filename
            body_matches: list[PAN] = text_scanner.scan(
                excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
            if len(body_matches) > 0:
                match_list.extend(body_matches)
        if self.eml.attachments:
            for _, att in enumerate(self.eml.attachments):
                att_scanner = _AttachmentScanner(path=self.filename)
                att_scanner.attachment = att
                att_matches: list[PAN] = att_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(att_matches) > 0:
                    match_list.extend(att_matches)
        return match_list


class _MboxScanner(_ScannerBase):
    mbox: Optional[Mbox] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        match_list: list[PAN] = []

        if self.mbox is None:
            self.mbox = Mbox(self.filename)

        for mail in self.mbox.mails:
            if mail.body:
                text_scanner = _InFileScanner()
                text_scanner.text = mail.body
                body_matches: list[PAN] = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(body_matches) > 0:
                    match_list.extend(body_matches)
            if mail.attachments:
                for _, att in enumerate(mail.attachments):
                    att_scanner = _AttachmentScanner(path=self.filename)
                    att_scanner.attachment = att
                    att_matches: list[PAN] = att_scanner.scan(
                        excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                    if len(att_matches) > 0:
                        match_list.extend(att_matches)

        return match_list


class _PstScanner(_ScannerBase):
    pst: Optional[PST] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        match_list: list[PAN] = []

        if self.pst is None:
            self.pst = PST(self.filename)

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
                        text_scanner = _InFileScanner()
                        text_scanner.text = message.Body
                        text_scanner.filename = self.filename
                        text_scanner.sub_path = message_path
                        body_matches: list[PAN] = text_scanner.scan(
                            excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                        if len(body_matches) > 0:
                            match_list.extend(body_matches)

                    if message.HasAttachments:
                        for _, subattachment in enumerate(message.subattachments):
                            if subattachment.Filename and panutils.get_ext(subattachment.Filename) in search_extensions[FileTypeEnum.Text] + search_extensions[FileTypeEnum.Zip]:
                                att: Optional[pstAttachment] = message.get_attachment(
                                    subattachment=subattachment)
                                if att:
                                    att_scanner = _AttachmentScanner(
                                        path=self.filename)
                                    att_scanner.attachment = att
                                    att_matches: list[PAN] = att_scanner.scan(
                                        excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                                    if len(att_matches) > 0:
                                        match_list.extend(att_matches)
            self.pst.close()

        return match_list


class _MailArchiveScanner(_ScannerBase):
    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        _, extension = os.path.splitext(self.filename.lower())
        if extension == '.pst':
            return _PstScanner(path=self.filename).scan(excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
        else:
            return _MboxScanner(path=self.filename).scan(excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)


class _ZipScanner(_ScannerBase):

    zip_file: Optional[zipfile.ZipFile] = None

    def scan(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:

        if self.zip_file is None:
            self.zip_file = zipfile.ZipFile(self.filename)

        match_list: list[PAN] = []

        all_extensions: list[str] = search_extensions[FileTypeEnum.Text] + \
            search_extensions[FileTypeEnum.Zip] + \
            search_extensions[FileTypeEnum.Mail]

        files_in_zip: list[str] = [file_in_zip for file_in_zip in self.zip_file.namelist(
        ) if panutils.get_ext(file_in_zip) in all_extensions]

        for file_in_zip in files_in_zip:
            ext: str = panutils.get_ext(file_in_zip)
            # nested zip file
            if ext in search_extensions[FileTypeEnum.Zip]:
                with io.BytesIO(self.zip_file.open(file_in_zip).read()) as memory_zip:
                    nested_zf = zipfile.ZipFile(memory_zip)
                    zip_scanner = _ZipScanner(path=file_in_zip)
                    zip_scanner.zip_file = nested_zf
                    zip_scanner.filename = self.filename
                    zip_scanner.sub_path = os.path.join(
                        os.path.basename(self.sub_path), file_in_zip)
                    zip_matches: list[PAN] = zip_scanner.scan(
                        excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                    if len(zip_matches) > 0:
                        match_list.extend(zip_matches)

            # normal doc
            elif ext in search_extensions[FileTypeEnum.Text]:
                file_text: str = panutils.decode_zip_text(
                    self.zip_file.open(file_in_zip).read())
                text_scanner = _InFileScanner()
                text_scanner.filename = self.filename
                text_scanner.sub_path = os.path.join(
                    self.sub_path, file_in_zip)
                text_scanner.text = file_text
                text_matches: list[PAN] = text_scanner.scan(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                if len(text_matches) > 0:
                    match_list.extend(text_matches)

            else:  # Mail message
                if panutils.get_ext(file_in_zip) in search_extensions[FileTypeEnum.Mail]:
                    memory_msg = io.StringIO()
                    memory_msg.write(panutils.decode_zip_text(
                        self.zip_file.open(file_in_zip).read()))
                    msg: MSMSG = MSMSG(memory_msg.read())
                    if msg.validMSG:
                        msg_scanner = _MsgScanner(path=file_in_zip)
                        msg_scanner.sub_path = os.path.join(nested_zf.filename, panutils.decode_zip_filename(  # type: ignore
                            file_in_zip))

                        msg_matches: list[PAN] = msg_scanner.scan(
                            excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                        if len(msg_matches) > 0:
                            match_list.extend(msg_matches)
                    memory_msg.close()
        return match_list


class Dispatcher:

    scanner_mapping: dict[FileTypeEnum, Type[_ScannerBase]]
    excluded_pans_list: list[str]
    search_extensions: dict[FileTypeEnum, list[str]]

    def __init__(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> None:
        self.excluded_pans_list = excluded_pans_list
        self.search_extensions = search_extensions

        self.scanner_mapping = {
            FileTypeEnum.Text: _BasicScanner,
            FileTypeEnum.Zip: _ZipScanner,
            FileTypeEnum.Mail: _MessageScanner,
            FileTypeEnum.MailArchive: _MailArchiveScanner
        }

    def dispatch(self, file_type: FileTypeEnum, path: str) -> list[PAN]:
        scanner_init: Type[_ScannerBase] = self.scanner_mapping[file_type]
        scanner_instance = scanner_init(path=path)
        return scanner_instance.scan(
            excluded_pans_list=self.excluded_pans_list, search_extensions=self.search_extensions)
