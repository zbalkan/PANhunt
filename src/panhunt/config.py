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
    worker_count: int
    max_scan_depth: int
    max_child_jobs: int
    max_total_expanded_bytes: int
    max_archive_members: int
    max_archive_compression_ratio: int
    max_archive_path_length: int
    archive_spool_threshold: int
    max_attachment_size: int
    max_attachments_per_message: int
    max_total_attachment_bytes: int
    allowed_archive_types: list[str]
    denied_archive_types: list[str]
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
        self.worker_count = 1
        self.max_scan_depth = 25
        self.max_child_jobs = 100_000
        self.max_total_expanded_bytes = self.size_limit
        self.max_archive_members = 10_000
        self.max_archive_compression_ratio = 100
        self.max_archive_path_length = 4096
        self.archive_spool_threshold = 8 * 1024 * 1024
        self.max_attachment_size = self.size_limit
        self.max_attachments_per_message = 1_000
        self.max_total_attachment_bytes = self.size_limit
        self.allowed_archive_types = []
        self.denied_archive_types = []
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
                  worker_count: Optional[int] = None,
                  max_scan_depth: Optional[int] = None,
                  max_child_jobs: Optional[int] = None,
                  max_total_expanded_bytes: Optional[int] = None,
                  max_archive_members: Optional[int] = None,
                  max_archive_compression_ratio: Optional[int] = None,
                  max_archive_path_length: Optional[int] = None,
                  archive_spool_threshold: Optional[int] = None,
                  max_attachment_size: Optional[int] = None,
                  max_attachments_per_message: Optional[int] = None,
                  max_total_attachment_bytes: Optional[int] = None,
                  allowed_archive_types_string: Optional[str] = None,
                  denied_archive_types_string: Optional[str] = None,
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
            worker_count=worker_count,
            max_scan_depth=max_scan_depth,
            max_child_jobs=max_child_jobs,
            max_total_expanded_bytes=max_total_expanded_bytes,
            max_archive_members=max_archive_members,
            max_archive_compression_ratio=max_archive_compression_ratio,
            max_archive_path_length=max_archive_path_length,
            archive_spool_threshold=archive_spool_threshold,
            max_attachment_size=max_attachment_size,
            max_attachments_per_message=max_attachments_per_message,
            max_total_attachment_bytes=max_total_attachment_bytes,
            allowed_archive_types_string=allowed_archive_types_string,
            denied_archive_types_string=denied_archive_types_string,
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
            worker_count=cls._try_parse_int(raw, 'workers'),
            max_scan_depth=cls._try_parse_int(raw, 'maxscandepth'),
            max_child_jobs=cls._try_parse_int(raw, 'maxchildjobs'),
            max_total_expanded_bytes=cls._try_parse_int(raw, 'maxtotalexpandedbytes'),
            max_archive_members=cls._try_parse_int(raw, 'maxarchivemembers'),
            max_archive_compression_ratio=cls._try_parse_int(raw, 'maxarchivecompressionratio'),
            max_archive_path_length=cls._try_parse_int(raw, 'maxarchivepathlength'),
            archive_spool_threshold=cls._try_parse_int(raw, 'archivespoolthreshold'),
            max_attachment_size=cls._try_parse_int(raw, 'maxattachmentsize'),
            max_attachments_per_message=cls._try_parse_int(raw, 'maxattachmentspermessage'),
            max_total_attachment_bytes=cls._try_parse_int(raw, 'maxtotalattachmentbytes'),
            allowed_archive_types_string=cls._try_parse(raw, 'allowedarchivetypes'),
            denied_archive_types_string=cls._try_parse(raw, 'deniedarchivetypes'),
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
                worker_count: Optional[int] = None,
                max_scan_depth: Optional[int] = None,
                max_child_jobs: Optional[int] = None,
                max_total_expanded_bytes: Optional[int] = None,
                max_archive_members: Optional[int] = None,
                max_archive_compression_ratio: Optional[int] = None,
                max_archive_path_length: Optional[int] = None,
                archive_spool_threshold: Optional[int] = None,
                max_attachment_size: Optional[int] = None,
                max_attachments_per_message: Optional[int] = None,
                max_total_attachment_bytes: Optional[int] = None,
                allowed_archive_types_string: Optional[str] = None,
                denied_archive_types_string: Optional[str] = None,
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
            self.max_total_expanded_bytes = size_limit
            self.max_attachment_size = size_limit
            self.max_total_attachment_bytes = size_limit

        if worker_count is not None:
            if worker_count < 1:
                raise ValueError("worker_count must be a positive integer")
            self.worker_count = worker_count

        if max_scan_depth is not None:
            if max_scan_depth < 0:
                raise ValueError("max_scan_depth must be a non-negative integer")
            self.max_scan_depth = max_scan_depth

        if max_child_jobs is not None:
            if max_child_jobs < 1:
                raise ValueError("max_child_jobs must be a positive integer")
            self.max_child_jobs = max_child_jobs

        if max_total_expanded_bytes is not None:
            if max_total_expanded_bytes < 0:
                raise ValueError("max_total_expanded_bytes must be a non-negative integer")
            self.max_total_expanded_bytes = max_total_expanded_bytes

        if max_archive_members is not None:
            if max_archive_members < 1:
                raise ValueError("max_archive_members must be a positive integer")
            self.max_archive_members = max_archive_members

        if max_archive_compression_ratio is not None:
            if max_archive_compression_ratio < 1:
                raise ValueError("max_archive_compression_ratio must be a positive integer")
            self.max_archive_compression_ratio = max_archive_compression_ratio

        if max_archive_path_length is not None:
            if max_archive_path_length < 1:
                raise ValueError("max_archive_path_length must be a positive integer")
            self.max_archive_path_length = max_archive_path_length

        if archive_spool_threshold is not None:
            if archive_spool_threshold < 0:
                raise ValueError("archive_spool_threshold must be a non-negative integer")
            self.archive_spool_threshold = archive_spool_threshold

        if max_attachment_size is not None:
            if max_attachment_size < 0:
                raise ValueError("max_attachment_size must be a non-negative integer")
            self.max_attachment_size = max_attachment_size

        if max_attachments_per_message is not None:
            if max_attachments_per_message < 1:
                raise ValueError("max_attachments_per_message must be a positive integer")
            self.max_attachments_per_message = max_attachments_per_message

        if max_total_attachment_bytes is not None:
            if max_total_attachment_bytes < 0:
                raise ValueError("max_total_attachment_bytes must be a non-negative integer")
            self.max_total_attachment_bytes = max_total_attachment_bytes

        if allowed_archive_types_string and allowed_archive_types_string != 'None':
            self.allowed_archive_types = [t.strip().lower() for t in allowed_archive_types_string.split(',') if t.strip()]

        if denied_archive_types_string and denied_archive_types_string != 'None':
            self.denied_archive_types = [t.strip().lower() for t in denied_archive_types_string.split(',') if t.strip()]

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
