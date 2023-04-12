import datetime
import json
import logging
import os
import platform
import sys
import time
from dataclasses import dataclass
from typing import Final, Generator, Optional

import panutils
from config import PANHuntConfigSingleton
from PAN import PAN
from PANFile import PANFile
from pbar import FileProgressbar, MainProgressbar

TEXT_FILE_SIZE_LIMIT: Final[int] = 1073741824  # 1Gb

# TODO: Move progressbar related stuff to CLI


@dataclass
class Stats:
    files_total: int
    pans_found: int
    all_files: list[PANFile]


class Hunter:

    stats: Stats

    pbar: MainProgressbar
    start: datetime.datetime
    end: datetime.datetime

    def hunt_pans(self) -> None:

        # Start timer
        self.start = datetime.datetime.now()

        logging.debug("Started searching directories.")

        # find all files to check
        all_files: list[PANFile] = self.find_all_files_in_search_directory()

        logging.debug("Finished searching directories.")

        logging.debug("Started searching in files.")

        # Create the bar
        hunt_type = 'PAN'
        self.pbar.create(hunt_type=hunt_type)

        # check each non-PST file
        doc_pans_found: int = 0
        nonpst_files: list[PANFile] = [pan_file for pan_file in all_files if not pan_file.errors and pan_file.filetype in (
            'TEXT', 'ZIP', 'SPECIAL')]
        for doc_pans_found, files_completed in self.find_all_regexs_in_files(nonpst_files):
            self.pbar.update(hunt_type=hunt_type, items_found=doc_pans_found,
                             items_total=len(nonpst_files), items_completed=files_completed)

        self.pbar.finish()
        logging.debug("Finished searching in on-PST files.")

        # check each pst message and attachment
        total_psts, pst_pans_found = self.find_all_regexs_in_psts(
            [pan_file for pan_file in all_files if not pan_file.errors and pan_file.filetype == 'MAIL'], 'PAN')
        logging.debug("Finished searching in PST files.")

        total_files_searched: int = len(nonpst_files) + total_psts
        pans_found: int = doc_pans_found + pst_pans_found

        logging.debug("Finished searching.")

        # Finish timer
        self.end = datetime.datetime.now()

        # return total_files_searched, pans_found, all_files
        self.stats = Stats(files_total=total_files_searched,
                           pans_found=pans_found, all_files=all_files)

    def create_report(self) -> None:

        if self.stats is None:
            return

        logging.debug("Creating TXT report.")

        pan_sep: str = '\n\t'
        pan_report: str = 'PAN Hunt Report - %s\n%s\n' % (
            time.strftime("%H:%M:%S %d/%m/%Y"), '=' * 100)
        pan_report += 'Searched %s\nExcluded %s\n' % (
            PANHuntConfigSingleton.instance().search_dir, ','.join(PANHuntConfigSingleton.instance().excluded_directories))
        pan_report += 'Command: %s\n' % (' '.join(sys.argv))
        pan_report += 'Uname: %s\n' % (' | '.join(platform.uname()))
        pan_report += f'Elapsed time: {self.end - self.start}\n'
        pan_report += 'Searched %s files. Found %s possible PANs.\n%s\n\n' % (
            self.stats.files_total, self.stats.pans_found, '=' * 100)

        for pan_file in sorted([pan_file for pan_file in self.stats.all_files if pan_file.matches], key=lambda x: x.filename):
            pan_header: str = f"FOUND PANs: {pan_file.path} ({panutils.size_friendly(pan_file.size)} {pan_file.modified.strftime('%d/%m/%Y')})"

            pan_report += pan_header + '\n'
            pan_list: str = '\t' + \
                pan_sep.join([pan.get_masked_pan()
                              for pan in pan_file.matches])
            pan_report += pan_list + '\n\n'

        interesting_files = [
            pan_file for pan_file in self.stats.all_files if pan_file.filetype == 'OTHER']
        if len(interesting_files) != 0:
            pan_report += 'Interesting Files to check separately:\n'
        for pan_file in sorted(interesting_files, key=lambda x: x.filename):
            pan_report += '%s (%s %s)\n' % (pan_file.path,
                                            panutils.size_friendly(pan_file.size), pan_file.modified.strftime('%d/%m/%Y'))

        pan_report = pan_report.replace('\n', os.linesep)

        with open(PANHuntConfigSingleton.instance().output_file, encoding='utf-8', mode='w') as f:
            f.write(pan_report)

        self.append_hash(PANHuntConfigSingleton.instance().output_file)

        logging.debug("Created TXT report.")

    def create_json_report(self) -> None:

        if PANHuntConfigSingleton.instance().json_path is None:
            return

        logging.debug("Creating JSON report.")

        report: dict = {}
        report['timestamp'] = time.strftime("%H:%M:%S %d/%m/%Y")
        report['searched'] = PANHuntConfigSingleton.instance().search_dir
        report['excluded'] = ','.join(
            PANHuntConfigSingleton.instance().excluded_directories)
        report['command'] = ' '.join(sys.argv)
        report['elapsed'] = str(self.end - self.start)
        report['total_files'] = self.stats.files_total
        report['pans_found'] = self.stats.pans_found
        report['pans_found_results'] = []
        for pan_file in sorted([pan_file for pan_file in self.stats.all_files if pan_file.matches], key=lambda x: x.filename):
            report['pans_found_results'].append(
                (pan_file.filename, [pan.get_masked_pan() for pan in pan_file.matches]))

        interesting_files: list[PANFile] = sorted([
            pan_file for pan_file in self.stats.all_files if pan_file.filetype == 'OTHER'], key=lambda x: x.filename)
        if len(interesting_files) != 0:
            report['interesting_files']['total'] = len(interesting_files)

            report['interesting_files']['files'] = [
                f.filename for f in interesting_files]

        initial_report: str = json.dumps(report, sort_keys=True)
        digest: str = panutils.get_text_hash(initial_report)
        report['hash'] = digest
        final_report: str = json.dumps(report)
        with open(PANHuntConfigSingleton.instance().json_path, "w") as f:  # type: ignore
            f.write(final_report)

        logging.debug("Created JSON report.")

    def find_all_files_in_search_directory(self) -> list[PANFile]:
        """Recursively searches a directory for files. search_extensions is a dictionary of extension lists"""

        all_extensions: list[str] = [ext for ext_list in list(
            PANHuntConfigSingleton.instance().search_extensions.values()) for ext in ext_list]

        extension_types: dict[str, str] = {}
        for ext_type, ext_list in PANHuntConfigSingleton.instance().search_extensions.items():
            for ext in ext_list:
                extension_types[ext] = ext_type

        self.pbar = MainProgressbar()
        self.pbar.create('Doc')

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
                self.pbar.update(
                    hunt_type='Doc',
                    items_found=docs_found,
                    items_total=root_total_items,
                    items_completed=root_items_completed)

            for filename in files:
                if root == PANHuntConfigSingleton.instance().search_dir:
                    root_items_completed += 1
                pan_file = PANFile(filename, root)
                if pan_file.ext.lower() in all_extensions:
                    pan_file.set_file_stats()
                    pan_file.filetype = extension_types[pan_file.ext.lower()]
                    if pan_file.filetype in ('TEXT', 'SPECIAL') and pan_file.size > TEXT_FILE_SIZE_LIMIT:
                        pan_file.filetype = 'OTHER'
                        pan_file.set_error(
                            f'File size {panutils.size_friendly(pan_file.size)} over limit of {panutils.size_friendly(TEXT_FILE_SIZE_LIMIT)} for checking')
                    doc_files.append(pan_file)
                    if not pan_file.errors:
                        docs_found += 1
                    self.pbar.update(
                        hunt_type='Doc',
                        items_found=docs_found,
                        items_total=root_total_items,
                        items_completed=root_items_completed)

        self.pbar.finish()

        return doc_files

    def find_all_regexs_in_files(self, text_or_zip_files: list[PANFile]) -> Generator[tuple[int, int], None, None]:
        """ Searches files in doc_files list for regular expressions"""

        files_completed: int = 0
        matches_found: int = 0

        for pan_file in text_or_zip_files:
            matches: list[PAN] = pan_file.check_regexs(excluded_pans_list=PANHuntConfigSingleton.instance().excluded_pans,
                                                       search_extensions=PANHuntConfigSingleton.instance().search_extensions)
            matches_found += len(matches)
            files_completed += 1
            yield matches_found, files_completed

    def find_all_regexs_in_psts(self, pst_files: list[PANFile], hunt_type: str) -> tuple[int, int]:
        """ Searches psts in pst_files list for regular expressions in messages and attachments"""

        total_psts: int = len(pst_files)
        psts_completed = 0
        matches_found = 0

        for file in pst_files:

            with FileProgressbar(hunt_type, file.filename) as sub_pbar:
                for completed, total_items in file.check_pst_regexs(
                        excluded_pans_list=PANHuntConfigSingleton.instance().excluded_pans,
                        search_extensions=PANHuntConfigSingleton.instance().search_extensions):

                    sub_pbar.update(items_found=len(file.matches),
                                    items_total=total_items, items_completed=completed)
                matches_found += len(file.matches)
                psts_completed += 1
        return total_psts, matches_found

    def append_hash(self, text_file: str) -> None:

        with open(text_file, encoding='utf-8', mode='r') as f:
            text: str = f.read()

        hash_check: str = panutils.get_text_hash(text)

        text += os.linesep + hash_check

        with open(text_file, encoding='utf-8', mode='w') as f:
            f.write(text)
