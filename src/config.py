import configparser
import os
import time
from typing import Optional

import panutils


class PANHuntConfiguration:
    # Class-level variable to store the singleton instance
    __instance: Optional['PANHuntConfiguration'] = None

    search_dir: str
    file_path: Optional[str]
    config_file: Optional[str]
    report_file: str
    report_dir: str
    json_file: str
    json_dir: Optional[str]
    excluded_directories: list[str]
    excluded_pans: list[str]
    size_limit: int
    verbose: bool

    def __new__(cls, *args, **kwargs) -> 'PANHuntConfiguration':
        if cls.__instance is None:
            cls.__instance = super(PANHuntConfiguration,
                                   cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'):  # Ensure init is called only once
            if os.name == 'nt':
                self.search_dir = 'C:\\'
                self.excluded_directories = ['C:\\Windows',
                                             'C:\\Program Files', 'C:\\Program Files(x86)']
            else:
                self.search_dir = '/'
                self.excluded_directories = ['/mnt', '/dev', '/proc']
            self.file_path = None
            self.config_file = None
            self.report_file = f'panhunt_{time.strftime("%Y-%m-%d-%H%M%S")}.report'
            self.report_dir = panutils.get_root_dir()
            self.json_file = f'panhunt_{time.strftime("%Y-%m-%d-%H%M%S")}.json'
            self.json_dir = None
            self.excluded_pans = []
            self.size_limit = 1_073_741_824  # 1Gb
            self._initialized = True  # Mark as initialized to prevent re-init

    def with_args(self,
                  search_dir: Optional[str] = None,
                  file_path: Optional[str] = None,
                  report_dir: Optional[str] = None,
                  excluded_directories_string: Optional[str] = None,
                  excluded_pans_string: Optional[str] = None,
                  json_dir: Optional[str] = None,
                  verbose: bool = False,
                  size_limit: Optional[int] = None) -> None:
        """If any parameter is provided, it overwrites the previous value
        """

        self.__update(search_dir=search_dir,
                      file_path=file_path,
                      report_dir=report_dir,
                      json_dir=json_dir,
                      excluded_directories_string=excluded_directories_string,
                      excluded_pans_string=excluded_pans_string,
                      verbose=verbose,
                      size_limit=size_limit)

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
        report_dir: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='outfile')
        json_dir: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='json')
        excluded_pans_string: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file=config_from_file, property='excludepans')
        verbose: bool = PANHuntConfiguration.__check_verbose(
            config_from_file=config_from_file)
        size_limit = PANHuntConfiguration.__try_parse_int(
            config_from_file=config_from_file, property='sizelimit')

        self.__update(search_dir=search_dir,
                      file_path=file_path,
                      report_dir=report_dir,
                      json_dir=json_dir,
                      excluded_directories_string=excluded_directories_string,
                      excluded_pans_string=excluded_pans_string,
                      verbose=verbose,
                      size_limit=size_limit)

    def get_json_path(self) -> Optional[str]:
        if self.json_dir:
            return os.path.join(self.json_dir, self.json_file)
        else:
            return None

    def get_report_path(self) -> str:
        return os.path.join(self.report_dir, self.report_file)

    def is_excluded(self, pan: str) -> bool:
        for excluded_pan in self.excluded_pans:
            if pan == excluded_pan:
                return True
        return False

    @staticmethod
    def __parse_file(config_file) -> dict:
        config: configparser.ConfigParser = configparser.ConfigParser()
        config.read(config_file)
        config_from_file: dict = {}

        for nvp in config.items('DEFAULT'):
            config_from_file[nvp[0]] = nvp[1]
        return config_from_file

    @staticmethod
    def __check_verbose(config_from_file) -> bool:
        is_verbose: bool = False
        if 'verbose' in config_from_file:
            is_verbose = (config_from_file['verbose'].upper() == 'TRUE')
        return is_verbose

    @staticmethod
    def __try_parse(config_from_file: dict, property: str) -> Optional[str]:
        if property in config_from_file:
            return str(config_from_file[property])
        return None

    @staticmethod
    def __try_parse_int(config_from_file: dict, property: str) -> Optional[int]:
        s: Optional[str] = PANHuntConfiguration.__try_parse(
            config_from_file, property)
        if s:
            return int(s)
        return None

    def __update(self,
                 search_dir: Optional[str],
                 file_path: Optional[str],
                 report_dir: Optional[str],
                 json_dir: Optional[str],
                 excluded_directories_string: Optional[str],
                 excluded_pans_string: Optional[str],
                 verbose: bool,
                 size_limit: Optional[int]) -> None:

        if search_dir and search_dir != 'None':
            self.search_dir = os.path.abspath(path=search_dir)

        if file_path and file_path != "None":
            self.file_path = os.path.abspath(path=file_path)

        if report_dir and report_dir != 'None':
            if report_dir == './':
                self.report_dir = panutils.get_root_dir()
            else:
                self.report_dir = os.path.abspath(report_dir)

        if excluded_directories_string and excluded_directories_string != 'None':
            self.excluded_directories = [exc_dir.lower()
                                         for exc_dir in excluded_directories_string.split(',')]

        if excluded_pans_string and excluded_pans_string != excluded_pans_string and len(excluded_pans_string) > 0:
            self.excluded_pans = excluded_pans_string.split(',')

        if json_dir:
            if json_dir == "./":
                self.json_dir = panutils.get_root_dir()
            else:
                self.json_dir = os.path.abspath(json_dir)

        if verbose:
            self.verbose = verbose

        if size_limit:
            self.size_limit = size_limit
