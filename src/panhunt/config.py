import configparser
import os
import time
from typing import Optional

from . import panutils


class ScanConfiguration:
    """Configuration for a single scan session. Created once and injected into all components."""

    search_dir: str
    file_path: Optional[str]
    report_dir: str
    json_dir: Optional[str]
    excluded_directories: list[str]
    excluded_pans: list[str]
    size_limit: int
    quiet: bool
    report_file: str
    json_file: str

    def __init__(self) -> None:
        if os.name == 'nt':
            self.search_dir = 'C:\\'
            self.excluded_directories = ['c:\\windows', 'c:\\program files', 'c:\\program files(x86)']
        else:
            self.search_dir = '/'
            self.excluded_directories = ['/mnt', '/dev', '/proc']

        self.file_path = None
        self.report_dir = panutils.get_root_dir()
        self.json_dir = None
        self.excluded_pans = []
        self.size_limit = 1_073_741_824  # 1GB
        self.quiet = False
        self.report_file = f'panhunt_{time.strftime("%Y-%m-%d-%H%M%S")}.report'
        self.json_file = f'panhunt_{time.strftime("%Y-%m-%d-%H%M%S")}.json'

    def get_report_path(self) -> str:
        return os.path.join(self.report_dir, self.report_file)

    def get_json_path(self) -> Optional[str]:
        if self.json_dir:
            return os.path.join(self.json_dir, self.json_file)
        return None

    def is_excluded(self, pan: str) -> bool:
        return pan in self.excluded_pans

    @classmethod
    def from_args(cls,
                  search_dir: Optional[str] = None,
                  file_path: Optional[str] = None,
                  report_dir: Optional[str] = None,
                  json_dir: Optional[str] = None,
                  excluded_directories_string: Optional[str] = None,
                  excluded_pans_string: Optional[str] = None,
                  size_limit: Optional[int] = None,
                  quiet: Optional[bool] = None) -> 'ScanConfiguration':

        config = cls()
        config._update(
            search_dir=search_dir,
            file_path=file_path,
            report_dir=report_dir,
            json_dir=json_dir,
            excluded_directories_string=excluded_directories_string,
            excluded_pans_string=excluded_pans_string,
            size_limit=size_limit,
            quiet=quiet
        )
        return config

    @classmethod
    def from_file(cls, config_file: str, quiet: Optional[bool] = None) -> 'ScanConfiguration':
        if not os.path.isfile(config_file):
            raise ValueError("Invalid configuration file.")

        raw = cls._parse_file(config_file)

        return cls.from_args(
            search_dir=cls._try_parse(raw, 'search'),
            file_path=cls._try_parse(raw, 'file'),
            report_dir=cls._try_parse(raw, 'outfile'),
            json_dir=cls._try_parse(raw, 'json'),
            excluded_directories_string=cls._try_parse(raw, 'exclude'),
            excluded_pans_string=cls._try_parse(raw, 'excludepans'),
            size_limit=cls._try_parse_int(raw, 'sizelimit'),
            quiet=quiet if quiet is not None else cls._try_parse_bool(raw, 'quiet'),
        )

    def _update(self,
                search_dir: Optional[str],
                file_path: Optional[str],
                report_dir: Optional[str],
                json_dir: Optional[str],
                excluded_directories_string: Optional[str],
                excluded_pans_string: Optional[str],
                size_limit: Optional[int],
                quiet: Optional[bool] = None) -> None:

        if search_dir and search_dir != 'None':
            self.search_dir = os.path.abspath(path=search_dir)

        if file_path and file_path != 'None':
            self.file_path = os.path.abspath(path=file_path)

        if report_dir and report_dir != 'None':
            self.report_dir = panutils.get_root_dir() if report_dir == './' else os.path.abspath(report_dir)

        if json_dir:
            self.json_dir = panutils.get_root_dir() if json_dir == './' else os.path.abspath(json_dir)

        if excluded_directories_string and excluded_directories_string != 'None':
            self.excluded_directories = [d.lower() for d in excluded_directories_string.split(',')]

        if excluded_pans_string and excluded_pans_string != 'None':
            self.excluded_pans = excluded_pans_string.split(',')

        if size_limit is not None:
            self.size_limit = size_limit

        if quiet is not None:
            self.quiet = quiet

    @staticmethod
    def _parse_file(config_file: str) -> dict:
        config = configparser.ConfigParser()
        config.read(config_file)
        result: dict = {}
        for nvp in config.items('DEFAULT'):
            result[nvp[0]] = nvp[1]
        return result

    @staticmethod
    def _try_parse(raw: dict, key: str) -> Optional[str]:
        return str(raw[key]) if key in raw else None

    @staticmethod
    def _try_parse_int(raw: dict, key: str) -> Optional[int]:
        s = ScanConfiguration._try_parse(raw, key)
        return int(s) if s else None

    @staticmethod
    def _try_parse_bool(raw: dict, key: str) -> Optional[bool]:
        s = ScanConfiguration._try_parse(raw, key)
        return s.lower() == 'true' if s else None
