import logging
import os
from typing import Generator, Optional

import panutils
from config import PANHuntConfiguration
from dispatcher import Dispatcher
from PANFile import PANFile
from patterns import CardPatterns


class Hunter:

    __all_files: list  # list[PANFile]
    __conf: PANHuntConfiguration
    __patterns: CardPatterns

    def __init__(self, configuration: PANHuntConfiguration) -> None:
        self.__conf = configuration
        self.__all_files = []
        self.__patterns = CardPatterns()

    def get_files(self) -> tuple:  # tuple[PANFile, ...]:
        return tuple(self.__all_files)

    def add_single_file(self, filename: str, dir: str) -> None:
        file: PANFile = PANFile(filename=filename, file_dir=dir)
        self.__all_files.append(file)

    # def get_scannable_files(self) -> Generator[tuple[int, int, int], None, None]:
    def get_scannable_files(self) -> Generator[tuple, None, None]:
        """Recursively searches a directory for files. search_extensions is a dictionary of extension lists"""

        # list[PANFile]
        doc_files: list = []
        # root_dir_dirs: Optional[list[str]] = None
        root_dir_dirs: Optional[list] = None
        root_items_completed = 0
        docs_found = 0
        root_total_items: int = 0

        logging.info(f"Search base: {self.__conf.search_dir}")

        for root, sub_ds, files in os.walk(top=self.__conf.search_dir):
            # list[str]
            sub_dirs: list = [check_dir for check_dir in sub_ds if os.path.join(
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
                    pan_file: PANFile = PANFile(
                        filename=filename, file_dir=root)
                    doc_files.append(pan_file)
                    if not pan_file.errors:
                        docs_found += 1

                yield docs_found, root_total_items, root_items_completed

        self.__all_files += doc_files
        logging.info(f"Total number of files: {len(self.__all_files)}")

    # def scan_files(self) -> Generator[tuple[int, int], None, None]:

    def scan_files(self) -> Generator[tuple, None, None]:
        """ Searches files in doc_files list for regular expressions"""

        files_completed: int = 0
        matches_found: int = 0
        dispatcher = Dispatcher(
            excluded_pans_list=self.__conf.excluded_pans, patterns=self.__patterns)

        for pan_file in self.__all_files:
            # matches: list[PAN] = pan_file.scan_with(dispatcher=dispatcher)
            matches: list = pan_file.scan_with(
                dispatcher=dispatcher, verbose=self.__conf.verbose)
            matches_found += len(matches)
            files_completed += 1
            yield matches_found, files_completed
