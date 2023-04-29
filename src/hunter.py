import os
from typing import Final, Generator, Optional

import panutils
from config import PANHuntConfiguration
from enums import FileTypeEnum
from PAN import PAN
from PANFile import PANFile
from scanner import Dispatcher

TEXT_FILE_SIZE_LIMIT: Final[int] = 1073741824  # 1Gb


class Hunter:

    __all_files: list[PANFile]
    __conf: PANHuntConfiguration

    def __init__(self, configuration: PANHuntConfiguration) -> None:
        self.__conf = configuration
        self.__all_files = []

    def get_files(self) -> tuple[PANFile, ...]:
        return tuple(self.__all_files)

    def add_single_file(self, filename: str, dir: str) -> None:
        file: PANFile = self.__try_init_PANfile(filename=filename, dir=dir)
        self.__all_files.append(file)

    def get_scannable_files(self) -> Generator[tuple[int, int, int], None, None]:
        """Recursively searches a directory for files. search_extensions is a dictionary of extension lists"""

        doc_files: list[PANFile] = []
        root_dir_dirs: Optional[list[str]] = None
        root_items_completed = 0
        docs_found = 0
        root_total_items: int = 0

        for root, sub_ds, files in os.walk(self.__conf.search_dir):
            sub_dirs: list[str] = [check_dir for check_dir in sub_ds if os.path.join(
                root, check_dir)
                .lower() not in self.__conf.excluded_directories]
            if not root_dir_dirs:
                root_dir_dirs = [os.path.join(root, sub_dir)
                                 for sub_dir in sub_dirs]
                root_total_items = len(root_dir_dirs) + len(files)
            if root in root_dir_dirs:
                root_items_completed += 1

                yield docs_found, root_total_items, root_items_completed

            for filename in files:
                if root == self.__conf.search_dir:
                    root_items_completed += 1
                pan_file: PANFile = self.__try_init_PANfile(
                    filename=filename, dir=root)
                doc_files.append(pan_file)
                if not pan_file.errors:
                    docs_found += 1

                yield docs_found, root_total_items, root_items_completed

        self.__all_files += doc_files

    def scan_files(self) -> Generator[tuple[int, int], None, None]:
        """ Searches files in doc_files list for regular expressions"""

        files_completed: int = 0
        matches_found: int = 0

        for pan_file in self.__all_files:
            dispatcher = Dispatcher(
                excluded_pans_list=self.__conf.excluded_pans, search_extensions=self.__conf.search_extensions)
            matches: list[PAN] = pan_file.scan_with(dispatcher=dispatcher)
            matches_found += len(matches)
            files_completed += 1
            yield matches_found, files_completed

    def __try_init_PANfile(self, filename: str, dir: str) -> PANFile:
        pan_file = PANFile(filename=filename, file_dir=dir)
        if pan_file.ext.lower() in self.__conf.get_accepted_exts():
            pan_file.set_file_stats()
            pan_file.filetype = self.__conf.get_filetype_per_extension()[pan_file.ext.lower(
            )]
            if pan_file.filetype in (FileTypeEnum.Text, FileTypeEnum.Mail) and pan_file.size > TEXT_FILE_SIZE_LIMIT:
                pan_file.filetype = FileTypeEnum.Other
                pan_file.set_error(
                    f'File size {panutils.size_friendly(pan_file.size)} over limit of {panutils.size_friendly(TEXT_FILE_SIZE_LIMIT)} for checking for file \"{filename}\"')

        return pan_file
