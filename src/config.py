import configparser
import os
import time
from typing import Optional

import panutils
from enums import FileCategoryEnum


class PANHuntConfiguration:
    search_dir: str
    file_path: Optional[str]
    config_file: Optional[str]
    report_file: str
    report_dir: str
    json_file: str
    json_dir: Optional[str]
    mask_pans: bool
    # excluded_directories: list[str]
    excluded_directories: list
    # search_extensions: dict[FileCategoryEnum, list[str]]
    search_extensions: dict
    # excluded_pans: list[str]
    excluded_pans: list

    def __init__(self) -> None:
        if os.name == 'nt':
            self.search_dir = 'C:\\'
        else:
            self.search_dir = '/'
        self.file_path = None
        self.config_file = None
        self.report_file = f'panhunt_{time.strftime("%Y-%m-%d-%H%M%S")}.report'
        self.report_dir = panutils.get_root_dir()
        self.json_file = f'panhunt_{time.strftime("%Y-%m-%d-%H%M%S")}.json'
        self.json_dir = None
        self.mask_pans = False
        self.excluded_directories = ['C:\\Windows',
                                     'C:\\Program Files', 'C:\\Program Files(x86)', '/mnt', '/dev', '/proc']
        self.search_extensions = {
            FileCategoryEnum.Text: ['.doc', '.xls', '.ppt', '.xml', '.txt', '.csv', '.log', '.rtf', '.tmp', '.bak', '.rtf', '.csv', '.htm', '.html', '.js', '.css', '.md', '.json'],
            FileCategoryEnum.Zip: ['.docx', '.xlsx', '.pptx', '.zip'],
            FileCategoryEnum.Mail: ['.msg'],
            FileCategoryEnum.MailArchive: ['.pst'],
            FileCategoryEnum.Other: ['.ost', '.accdb', '.mdb'],
            FileCategoryEnum.Pdf: ['.pdf']
        }
        self.excluded_pans = []

    def with_args(self,
                  search_dir: Optional[str] = None,
                  file_path: Optional[str] = None,
                  report_dir: Optional[str] = None,
                  mask_pans: bool = False,
                  excluded_directories_string: Optional[str] = None,
                  text_extensions_string: Optional[str] = None,
                  zip_extensions_string: Optional[str] = None,
                  mail_message_extensions_string: Optional[str] = None,
                  mail_archive_extensions_string: Optional[str] = None,
                  other_extensions_string: Optional[str] = None,
                  excluded_pans_string: Optional[str] = None,
                  json_dir: Optional[str] = None) -> None:
        """If any parameter is provided, it overwrites the previous value
        """

        self.__update(search_dir=search_dir,
                      file_path=file_path,
                      report_dir=report_dir,
                      json_dir=json_dir,
                      mask_pans=mask_pans,
                      excluded_directories_string=excluded_directories_string,
                      text_extensions_string=text_extensions_string,
                      zip_extensions_string=zip_extensions_string,
                      mail_message_extensions_string=mail_message_extensions_string,
                      mail_archive_extensions_string=mail_archive_extensions_string,
                      other_extensions_string=other_extensions_string,
                      excluded_pans_string=excluded_pans_string)

    def with_file(self, config_file: str) -> None:
        """If a config file provided and it has specific values, they overwrite the previous values

        Args:
            config_file (Optional[str]): Path to config file in INI format
        """

        if not os.path.isfile(config_file):
            raise ValueError("Invalid configuration file.")

        config_from_file: dict = self.__parse_file(config_file)

        search_dir: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='search')
        file_path: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='file')
        excluded_directories_string: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='exclude')
        text_extensions_string: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='textfiles')
        zip_extensions_string: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='zipfiles')
        mail_message_extensions_string: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='mailmessagefiles')
        mail_archive_extensions_string: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='mailarchivefiles')
        other_extensions_string: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='otherfiles')
        report_dir: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='outfile')
        json_dir: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='json')
        mask_pans: Optional[bool] = PANHuntConfiguration.__check_masked(
            config_from_file)
        excluded_pans_string: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='excludepans')

        self.__update(search_dir=search_dir,
                      file_path=file_path,
                      report_dir=report_dir,
                      json_dir=json_dir,
                      mask_pans=mask_pans,
                      excluded_directories_string=excluded_directories_string,
                      text_extensions_string=text_extensions_string,
                      zip_extensions_string=zip_extensions_string,
                      mail_message_extensions_string=mail_message_extensions_string,
                      mail_archive_extensions_string=mail_archive_extensions_string,
                      other_extensions_string=other_extensions_string,
                      excluded_pans_string=excluded_pans_string)

    def get_json_path(self) -> Optional[str]:
        if self.json_dir:
            return os.path.join(self.json_dir, self.json_file)
        else:
            return None

    def get_report_path(self) -> str:
        return os.path.join(self.report_dir, self.report_file)

    # def get_filetype_per_extension(self) -> dict[str, FileCategoryEnum]:
    def get_filetype_per_extension(self) -> dict:
        # extension_types: dict[str, FileCategoryEnum] = {}
        extension_types: dict = {}
        for ext_type, ext_list in self.search_extensions.items():
            for ext in ext_list:
                extension_types[ext] = ext_type
        return extension_types

    # def get_accepted_exts(self) -> list[str]:
    def get_accepted_exts(self) -> list:
        return [ext for ext_list in list(self.search_extensions.values()) for ext in ext_list]

    @staticmethod
    def __parse_file(config_file) -> dict:
        config: configparser.ConfigParser = configparser.ConfigParser()
        config.read(config_file)
        config_from_file: dict = {}

        for nvp in config.items('DEFAULT'):
            config_from_file[nvp[0]] = nvp[1]
        return config_from_file

    @staticmethod
    def __check_masked(config_from_file) -> Optional[bool]:
        mask_pans: Optional[bool] = None
        if 'unmask' in config_from_file:
            mask_pans = not (config_from_file['unmask'].upper() == 'TRUE')
        return mask_pans

    @staticmethod
    def __get_search_pdf(config_from_file) -> Optional[bool]:
        mask_pans: Optional[bool] = None
        if 'pdf' in config_from_file:
            mask_pans = (config_from_file['pdf'].upper() == 'TRUE')
        return mask_pans

    @staticmethod
    def __try_parse(config_from_file: dict, property: str) -> Optional[str]:
        if property in config_from_file:
            return str(config_from_file[property])
        return None

    def __update(self,
                 search_dir: Optional[str],
                 file_path: Optional[str],
                 report_dir: Optional[str],
                 json_dir: Optional[str],
                 mask_pans: Optional[bool],
                 excluded_directories_string: Optional[str],
                 text_extensions_string: Optional[str],
                 zip_extensions_string: Optional[str],
                 mail_message_extensions_string: Optional[str],
                 mail_archive_extensions_string: Optional[str],
                 other_extensions_string: Optional[str],
                 excluded_pans_string: Optional[str]) -> None:

        if search_dir and search_dir != 'None':
            self.search_dir = os.path.abspath(search_dir)

        if file_path and file_path != "None":
            self.file_path = os.path.abspath(file_path)

        if report_dir and report_dir != 'None':
            if report_dir == './':
                self.report_dir = panutils.get_root_dir()
            else:
                self.report_dir = os.path.abspath(report_dir)

        if mask_pans:
            self.mask_pans = mask_pans

        if excluded_directories_string and excluded_directories_string != 'None':
            self.excluded_directories = [os.path.abspath(exc_dir.lower())
                                         for exc_dir in excluded_directories_string.split(',')]
        if text_extensions_string and text_extensions_string != 'None':
            self.search_extensions[FileCategoryEnum.Text] = text_extensions_string.split(
                ',')
        if zip_extensions_string and zip_extensions_string != 'None':
            self.search_extensions[FileCategoryEnum.Zip] = zip_extensions_string.split(
                ',')
        if mail_message_extensions_string and mail_message_extensions_string != 'None':
            self.search_extensions[FileCategoryEnum.Mail] = mail_message_extensions_string.split(
                ',')
        if mail_archive_extensions_string and mail_archive_extensions_string != 'None':
            self.search_extensions[FileCategoryEnum.MailArchive] = mail_archive_extensions_string.split(
                ',')
        if other_extensions_string and other_extensions_string != 'None':
            self.search_extensions[FileCategoryEnum.Other] = other_extensions_string.split(
                ',')

        if excluded_pans_string and excluded_pans_string != excluded_pans_string and len(excluded_pans_string) > 0:
            self.excluded_pans = excluded_pans_string.split(',')

        if json_dir:
            if json_dir != "./":
                self.json_dir = panutils.get_root_dir()
            else:
                self.json_dir = os.path.abspath(json_dir)
