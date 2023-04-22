import logging
import os
from datetime import datetime
from typing import Generator, Optional

import pst
from enums import FileTypeEnum
from PAN import PAN
from scanner import Dispatcher


class PANFile:
    """ PANFile: class for a file that can check itself for PANs"""

    filename: str
    dir: str
    path: str
    root: str
    ext: str
    filetype: Optional[FileTypeEnum]
    errors: Optional[list[str]] = None
    matches: list[PAN]
    size: int
    accessed: datetime
    modified: datetime
    created: datetime

    def __init__(self, filename: str, file_dir: str) -> None:
        self.filename = filename
        self.dir = file_dir
        self.path = os.path.join(self.dir, self.filename)
        self.root, self.ext = os.path.splitext(self.filename)
        self.filetype = None
        self.matches = []

    def __cmp__(self, other: 'PANFile') -> bool:

        return self.path.lower() == other.path.lower()

    def set_file_stats(self) -> None:

        try:
            stat: os.stat_result = os.stat(self.path)
            self.size = stat.st_size
            self.accessed = self.dtm_from_ts(stat.st_atime)
            self.modified = self.dtm_from_ts(stat.st_mtime)
            self.created = self.dtm_from_ts(stat.st_ctime)
        except WindowsError as ex:
            self.size = -1
            self.set_error(str(ex))

    def dtm_from_ts(self, ts: float) -> datetime:

        try:
            return datetime.fromtimestamp(ts)
        except ValueError as ex:
            if ts == -753549904:
                # Mac OSX "while copying" thing
                return datetime(1946, 2, 14, 8, 34, 56)
            else:
                self.set_error(str(ex))
                return datetime(1970, 1, 1)

    def set_error(self, error_msg: str) -> None:
        if self.errors is None:
            self.errors = [error_msg]
        else:
            self.errors.append(error_msg)
        logging.error(error_msg)

    def check_regexs(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> list[PAN]:
        """Checks the file for matching regular expressions: if a ZIP then each file in the ZIP (recursively) or the text in a document"""

        if self.filetype:
            try:
                dispatcher = Dispatcher(
                    excluded_pans_list=excluded_pans_list, search_extensions=search_extensions)
                match_list: list[PAN] = dispatcher.dispatch(
                    file_type=self.filetype, path=self.path)
                self.matches.extend(match_list)
            except IOError as ex:
                self.set_error(str(ex))
            except Exception as ex:
                self.set_error(str(ex))

        if len(self.matches) > 0:
            logging.info(
                f'Found {len(self.matches)} possible PANs in {self.path}')
        return self.matches

    def check_pst_regexs(self, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> Generator[tuple[int, int], None, None]:
        """ Searches a pst file for regular expressions in messages and attachments using regular expressions"""
        try:
            pst_file = pst.PST(self.path)
            # if pst_file.header.validPST:

            #     total_messages: int = pst_file.get_total_message_count()
            #     total_attachments: int = pst_file.get_total_attachment_count()
            #     total_items: int = total_messages + total_attachments
            #     items_completed = 0

            #     for folder in pst_file.folder_generator():
            #         for message in pst_file.message_generator(folder):
            #             if message.Subject:
            #                 message_path: str = os.path.join(
            #                     folder.path, message.Subject)
            #             else:
            #                 message_path = os.path.join(
            #                     folder.path, '[NoSubject]')
            #             if message.Body:
            #                 self.check_text_regexs(
            #                     message.Body, message_path, excluded_pans_list)
            #             if message.HasAttachments:
            #                 for subattachment in message.subattachments:
            #                     if subattachment.Filename and panutils.get_ext(subattachment.Filename) in search_extensions[FileTypeEnum.Text] + search_extensions[FileTypeEnum.Zip]:
            #                         attachment: pst.Attachment = message.get_attachment(
            #                             subattachment)  # type: ignore
            #                         # We already checked there is an attachment, this is to suppress type checkers
            #                         self.check_attachment_regexs(attachment=attachment,
            #                                                      sub_path=message_path,
            #                                                      excluded_pans_list=excluded_pans_list,
            #                                                      search_extensions=search_extensions)
            #                     items_completed += 1
            #                     yield items_completed, total_items
            #             items_completed += 1
            #             yield items_completed, total_items

            pst_file.close()

        except IOError as ex:
            self.set_error(str(ex))
        except pst.PANHuntException as ex:
            self.set_error(str(ex))

    # def check_attachment_regexs(self, attachment: pst.Attachment | msmsg.Attachment, sub_path: str, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> None:
    #     """for PST and MSG attachments, check attachment for valid extension and then regexs"""

    #     attachment_ext: str = panutils.get_ext(attachment.Filename)
    #     if attachment_ext in search_extensions[FileTypeEnum.Text]:
    #         if attachment.BinaryData:
    #             self.check_text_regexs(text=attachment.BinaryData.decode('utf-8', errors='backslashreplace'),
    #                                    sub_path=os.path.join(
    #                                        sub_path, attachment.Filename),
    #                                    excluded_pans_list=excluded_pans_list)

    #     if attachment_ext in search_extensions[FileTypeEnum.Zip]:
    #         if attachment.BinaryData:
    #             try:
    #                 memory_zip = io.BytesIO(attachment.BinaryData)
    #                 zip_file = zipfile.ZipFile(memory_zip)
    #                 self.check_zip_regexs(zf=zip_file,
    #                                       sub_path=os.path.join(
    #                                           sub_path, attachment.Filename),
    #                                       excluded_pans_list=excluded_pans_list,
    #                                       search_extensions=search_extensions)
    #                 memory_zip.close()
    #             except RuntimeError as ex:  # RuntimeError: # e.g. zip needs password
    #                 self.set_error(str(ex))

    # def check_msg_regexs(self, msg: msmsg.MSMSG, sub_path: str, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> None:

    #     if msg.Body:
    #         self.check_text_regexs(
    #             text=msg.Body, sub_path=sub_path, excluded_pans_list=excluded_pans_list)
    #     if msg.attachments:
    #         for attachment in msg.attachments:
    #             self.check_attachment_regexs(attachment=attachment,
    #                                          sub_path=sub_path,
    #                                          excluded_pans_list=excluded_pans_list,
    #                                          search_extensions=search_extensions)

    # def check_zip_regexs(self, zf: zipfile.ZipFile, sub_path: str, excluded_pans_list: list[str], search_extensions: dict[FileTypeEnum, list[str]]) -> None:
    #     """Checks a zip file for valid documents that are then checked for regexs"""

    #     all_extensions: list[str] = search_extensions[FileTypeEnum.Text] + \
    #         search_extensions[FileTypeEnum.Zip] + \
    #         search_extensions[FileTypeEnum.Special]

    #     files_in_zip: list[str] = [file_in_zip for file_in_zip in zf.namelist(
    #     ) if panutils.get_ext(file_in_zip) in all_extensions]
    #     for file_in_zip in files_in_zip:
    #         # nested zip file
    #         if panutils.get_ext(file_in_zip) in search_extensions[FileTypeEnum.Zip]:
    #             try:
    #                 with io.BytesIO(zf.open(file_in_zip).read()) as memory_zip:
    #                     nested_zf = zipfile.ZipFile(memory_zip)
    #                     self.check_zip_regexs(zf=nested_zf,
    #                                           sub_path=os.path.join(
    #                                               sub_path, panutils.decode_zip_filename(file_in_zip)),
    #                                           excluded_pans_list=excluded_pans_list,
    #                                           search_extensions=search_extensions)
    #             except RuntimeError as ex:  # RuntimeError: # e.g. zip needs password
    #                 self.set_error(str(ex))
    #         # normal doc
    #         elif panutils.get_ext(file_in_zip) in search_extensions[FileTypeEnum.Text]:
    #             try:
    #                 file_text: str = panutils.decode_zip_text(
    #                     zf.open(file_in_zip).read())
    #                 self.check_text_regexs(text=file_text,
    #                                        sub_path=os.path.join(
    #                                            sub_path, panutils.decode_zip_filename(file_in_zip)),
    #                                        excluded_pans_list=excluded_pans_list)
    #             except RuntimeError as ex:  # RuntimeError: # e.g. zip needs password
    #                 self.set_error(str(ex))
    #         else:  # SPECIAL
    #             try:
    #                 if panutils.get_ext(file_in_zip) == '.msg':
    #                     memory_msg = io.StringIO()
    #                     memory_msg.write(panutils.decode_zip_text(
    #                         zf.open(file_in_zip).read()))
    #                     msg: msmsg.MSMSG = msmsg.MSMSG(memory_msg.read())
    #                     if msg.validMSG:
    #                         self.check_msg_regexs(msg=msg,
    #                                               sub_path=os.path.join(
    #                                                   sub_path, panutils.decode_zip_filename(file_in_zip)),
    #                                               excluded_pans_list=excluded_pans_list,
    #                                               search_extensions=search_extensions)
    #                     memory_msg.close()
    #             except RuntimeError as ex:  # RuntimeError
    #                 self.set_error(str(ex))
