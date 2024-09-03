import logging
import os
from typing import Generator, Optional

from PAN import PAN
import panutils
from config import PANHuntConfiguration
from dispatcher import Dispatcher
from PANFile import PANFile
from patterns import CardPatterns


class Hunter:

    __all_files: list[PANFile]
    __conf: PANHuntConfiguration
    __patterns: CardPatterns

    def __init__(self, configuration: PANHuntConfiguration) -> None:
        self.__conf = configuration
        self.__all_files = []
        self.__patterns = CardPatterns()

    def get_files(self) -> tuple[PANFile, ...]:
        return tuple(self.__all_files)

    def add_single_file(self, filename: str, dir: str) -> None:
        file: PANFile = PANFile(filename=filename, file_dir=dir)
        self.__all_files.append(file)

    def get_scannable_files(self) -> Generator[tuple[int, int, int], None, None]:
        """Recursively searches a directory for files. search_extensions is a dictionary of extension lists"""

        doc_files: list[PANFile] = []
        total_items: list[str] = []

        logging.info(f"Search base: {self.__conf.search_dir}")

        # Precompute total items
        for root, dirs, files in os.walk(self.__conf.search_dir):
            dirs[:] = [d for d in dirs if os.path.join(
                root, d).lower() not in self.__conf.excluded_directories]
            total_items.extend([os.path.join(root, d) for d in dirs])
            total_items.extend([os.path.join(root, f) for f in files])

        root_total_items = len(total_items)
        root_items_completed = 0
        docs_found = 0

        for root, dirs, files in os.walk(self.__conf.search_dir):
            dirs[:] = [d for d in dirs if os.path.join(
                root, d).lower() not in self.__conf.excluded_directories]

            for directory in dirs:
                root_items_completed += 1
                yield docs_found, root_total_items, root_items_completed

            for filename in files:
                root_items_completed += 1
                pan_file = PANFile(filename=filename, file_dir=root)
                if not pan_file.errors:
                    doc_files.append(pan_file)
                    docs_found += 1
                yield docs_found, root_total_items, root_items_completed

        self.__all_files += doc_files
        logging.info(f"Total number of files: {len(self.__all_files)}")

    def scan_files(self) -> Generator[tuple[int, int], None, None]:
        """ Searches files in doc_files list for regular expressions"""

        files_completed: int = 0
        matches_found: int = 0
        dispatcher = Dispatcher(
            excluded_pans_list=self.__conf.excluded_pans, patterns=self.__patterns)

        for pan_file in self.__all_files:
            matches: list[PAN] = pan_file.scan_with(
                dispatcher=dispatcher, verbose=self.__conf.verbose)
            matches_found += len(matches)
            files_completed += 1
            yield matches_found, files_completed
