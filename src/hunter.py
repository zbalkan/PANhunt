import logging

from config import PANHuntConfiguration
from directory import Directory
from dispatcher import Dispatcher
from patterns import CardPatterns
from scannable import ScannableFile


class Hunter:

    __all_files: list[ScannableFile]
    __matched_files: list[ScannableFile]
    __interesting_files: list[ScannableFile]
    __conf: PANHuntConfiguration
    __patterns: CardPatterns

    def __init__(self, configuration: PANHuntConfiguration) -> None:
        self.__conf = configuration
        self.__all_files = []
        self.__matched_files = []
        self.__interesting_files = []
        self.__patterns = CardPatterns()

    def add_file(self, filename: str, dir: str) -> None:
        file: ScannableFile = ScannableFile(filename=filename, file_dir=dir)
        self.__all_files.append(file)

    def enumerate(self) -> int:
        """Recursively searches a directory for files. search_extensions is a dictionary of extension lists"""

        file_list: list[ScannableFile] = []

        logging.info(f"Search base: {self.__conf.search_dir}")

        root = Directory(path=self.__conf.search_dir)
        for file in root.get_children():
            if file.dir not in self.__conf.excluded_directories:
                file_list.append(file)
        self.__all_files += file_list
        logging.info(f"Total number of files: {len(self.__all_files)}")
        return len(self.__all_files)

    def get_interesting_files(self) -> list[ScannableFile]:
        return self.__interesting_files

    def hunt(self) -> list[ScannableFile]:
        """ Searches files in doc_files list for regular expressions"""

        dispatcher = Dispatcher(
            excluded_pans_list=self.__conf.excluded_pans, patterns=self.__patterns)

        for sf in self.__all_files:
            sf_list: list[ScannableFile] = dispatcher.dispatch(sf)

            for f in sf_list:
                if len(f.matches) > 0:
                    self.__matched_files.append(f)
                else:
                    if f.errors is not None and len(f.errors) > 0:
                        self.__interesting_files.append(f)

        return self.__matched_files
