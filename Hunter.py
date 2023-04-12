import logging
import os
from datetime import datetime
from typing import Final, Generator, Optional

import panutils
from config import PANHuntConfigSingleton
from PAN import PAN
from PANFile import PANFile
from pbar import DocProgressbar, PstProgressbar
from stats import Stats

TEXT_FILE_SIZE_LIMIT: Final[int] = 1073741824  # 1Gb


class Hunter:

    __all_files__: list[PANFile]

    def __init__(self) -> None:
        self.__all_files__ = []

    def hunt_pans(self) -> Stats:

        # Start timer
        start: datetime = datetime.now()

        logging.debug("Started searching directories.")

        # find all files to check
        with DocProgressbar('Doc') as pbar:
            for docs_found, root_total_items, root_items_completed in self.get_scannable_files():
                pbar.update(items_found=docs_found,
                            items_total=root_total_items, items_completed=root_items_completed)

        logging.debug("Finished searching directories.")

        logging.debug("Started searching in files.")

        # check each non-PST file
        with DocProgressbar(hunt_type='PAN') as pbar:
            doc_pans_found: int = 0
            nonpst_files: list[PANFile] = [pan_file for pan_file in self.__all_files__ if not pan_file.errors and pan_file.filetype in (
                'TEXT', 'ZIP', 'SPECIAL')]
            for doc_pans_found, files_completed in self.scan_files():
                pbar.update(items_found=doc_pans_found,
                            items_total=len(nonpst_files), items_completed=files_completed)

        logging.debug("Finished searching in non-PST files.")

        # check each pst message and attachment

        pst_files: list[PANFile] = self.filter_pst_files()
        total_psts: int = len(pst_files)
        pst_pans_found: int = 0

        for pst_file in pst_files:

            with PstProgressbar('PAN', pst_file.filename) as pbar:
                for completed, total_items in pst_file.check_pst_regexs(
                        excluded_pans_list=PANHuntConfigSingleton.instance().excluded_pans,
                        search_extensions=PANHuntConfigSingleton.instance().search_extensions):
                    pst_pans_found += len(pst_file.matches)
                    pbar.update(items_found=len(pst_file.matches),
                                items_total=total_items, items_completed=completed)

        logging.debug("Finished searching in PST files.")

        total_files_searched: int = len(nonpst_files) + total_psts
        pans_found: int = doc_pans_found + pst_pans_found

        logging.debug("Finished searching.")

        # Finish timer
        end: datetime = datetime.now()

        # return total_files_searched, pans_found, all_files
        return Stats(files_total=total_files_searched,
                     pans_found=pans_found, all_files=self.__all_files__, start=start, end=end)

    def get_scannable_files(self) -> Generator[tuple[int, int, int], None, None]:
        """Recursively searches a directory for files. search_extensions is a dictionary of extension lists"""

        all_extensions: list[str] = [ext for ext_list in list(
            PANHuntConfigSingleton.instance().search_extensions.values()) for ext in ext_list]

        extension_types: dict[str, str] = {}
        for ext_type, ext_list in PANHuntConfigSingleton.instance().search_extensions.items():
            for ext in ext_list:
                extension_types[ext] = ext_type

        doc_files: list[PANFile] = []
        root_dir_dirs: Optional[list[str]] = None
        root_items_completed = 0
        docs_found = 0
        root_total_items: int = 0

        for root, sub_ds, files in os.walk(PANHuntConfigSingleton.instance().search_dir):
            sub_dirs: list[str] = [check_dir for check_dir in sub_ds if os.path.join(
                root, check_dir)
                .lower() not in PANHuntConfigSingleton.instance().excluded_directories]
            if not root_dir_dirs:
                root_dir_dirs = [os.path.join(root, sub_dir)
                                 for sub_dir in sub_dirs]
                root_total_items = len(root_dir_dirs) + len(files)
            if root in root_dir_dirs:
                root_items_completed += 1

                yield docs_found, root_total_items, root_items_completed

            for filename in files:
                if root == PANHuntConfigSingleton.instance().search_dir:
                    root_items_completed += 1
                pan_file = PANFile(filename, root)
                if pan_file.ext.lower() in all_extensions:
                    pan_file.set_file_stats()
                    pan_file.filetype = extension_types[pan_file.ext.lower(
                    )]
                    if pan_file.filetype in ('TEXT', 'SPECIAL') and pan_file.size > TEXT_FILE_SIZE_LIMIT:
                        pan_file.filetype = 'OTHER'
                        pan_file.set_error(
                            f'File size {panutils.size_friendly(pan_file.size)} over limit of {panutils.size_friendly(TEXT_FILE_SIZE_LIMIT)} for checking')
                    doc_files.append(pan_file)
                    if not pan_file.errors:
                        docs_found += 1

                    yield docs_found, root_total_items, root_items_completed

        self.__all_files__ += doc_files

    def scan_files(self) -> Generator[tuple[int, int], None, None]:
        """ Searches files in doc_files list for regular expressions"""

        files_completed: int = 0
        matches_found: int = 0

        for pan_file in self.filter_nonpst_files():
            matches: list[PAN] = pan_file.check_regexs(excluded_pans_list=PANHuntConfigSingleton.instance().excluded_pans,
                                                       search_extensions=PANHuntConfigSingleton.instance().search_extensions)
            matches_found += len(matches)
            files_completed += 1
            yield matches_found, files_completed

    def filter_nonpst_files(self) -> list[PANFile]:
        return [pan_file for pan_file in self.__all_files__ if not pan_file.errors and pan_file.filetype in (
            'TEXT', 'ZIP', 'SPECIAL')]

    def filter_pst_files(self) -> list[PANFile]:
        return [
            pan_file for pan_file in self.__all_files__ if not pan_file.errors and pan_file.filetype == 'MAIL']
