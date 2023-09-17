import json
import logging
import os
import platform
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Sequence

from genericpath import exists

import panutils
from enums import ScanStatusEnum
from PANFile import PANFile


class Report:

    total_files: int
    start: datetime
    end: datetime
    searched: str
    excluded: str
    pans_found: int
    matched_files: list  # list[PANFile]
    interesting_files: list  # list[PANFile]

    __command: str
    __timestamp: str
    __elapsed: timedelta

    def __init__(self,
                 search_dir: str,
                 excluded_dirs: list,
                 pans_found: int,
                 all_files: Sequence[PANFile],
                 start: datetime,
                 end: datetime) -> None:
        '''excluded_dirs: list[str]'''
        self.total_files = len(all_files)
        self.start = start
        self.end = end
        self.searched = search_dir
        self.excluded = ','.join(excluded_dirs)
        self.pans_found = pans_found
        self.__command = ' '.join(sys.argv)
        self.__timestamp = time.strftime("%H:%M:%S %d/%m/%Y")
        self.__elapsed = self.end - self.start
        self.matched_files = sorted(
            [pan_file for pan_file in all_files if pan_file.matches], key=lambda x: x.filename)
        self.interesting_files = sorted([
            pan_file for pan_file in all_files if pan_file.file_category == ScanStatusEnum.NotScanned], key=lambda x: x.path)

    def create_text_report(self, path: str) -> None:

        logging.info("Creating TXT report.")

        pan_sep: str = '\n\t'
        pan_report: str = f'PAN Hunt Report - {time.strftime("%H:%M:%S %d/%m/%Y")}\n{"=" * 100}\n'
        pan_report += f'Searched {self.searched}\nExcluded {self.excluded}\n'
        pan_report += f'Command: {self.__command}\n'
        pan_report += f'Uname: {" | ".join(platform.uname())}\n'
        pan_report += f'Elapsed time: {self.__elapsed}\n'
        pan_report += f'Searched {self.total_files} files. Found {self.pans_found} possible PANs.\n{"=" * 100}\n\n'

        for pan_file in sorted(self.matched_files, key=lambda x: x.path):
            pan_header: str = f"FOUND PANs: {pan_file.path} ({panutils.size_friendly(pan_file.size)} {pan_file.modified.strftime('%d/%m/%Y')})"

            pan_report += pan_header + '\n'
            pan_list: str = '\t'
            for pan in pan_file.matches:
                if pan.sub_path != '':
                    pan_list += f'{pan.sub_path} '
                pan_list += f"{pan.get_masked_pan()}{pan_sep}"
            pan_report += pan_list.rstrip(pan_sep) + '\n\n'

        if len(self.interesting_files) != 0:
            pan_report += 'Interesting Files to check separately, proably permission issue:\n'
        for pan_file in sorted(self.interesting_files, key=lambda x: x.filename):
            pan_report += f'{pan_file.path} ({panutils.size_friendly(pan_file.size)} {pan_file.modified.strftime("%d/%m/%Y")})\n'

        pan_report = pan_report.replace('\n', os.linesep)

        basedir: str = os.path.dirname(os.path.abspath(path=path))
        if not exists(basedir):
            os.makedirs(basedir)

        with open(path, encoding='utf-8', mode='w') as f:
            f.write(pan_report)

        self.append_hash(path)

        logging.info("Created TXT report.")

    def create_json_report(self, path: Optional[str]) -> None:

        if path is None:
            return

        logging.info("Creating JSON report.")

        report: dict = {}
        report['timestamp'] = self.__timestamp
        report['searched'] = self.searched
        report['excluded'] = self.excluded
        report['command'] = self.__command
        report['elapsed'] = str(self.__elapsed)
        report['total_files'] = self.total_files
        report['pans_found'] = self.pans_found

        # dict[str, list[str]]
        matched_items: dict = {}
        for pan_file in self.matched_files:

            # list[str]
            items: list = []
            for pan in pan_file.matches:
                item: str = ''
                if pan.filename != '':
                    item += f"{pan.filename}\\{pan.sub_path} "
                item += f"{pan.get_masked_pan()}"
                items.append(item)
            matched_items[pan_file.path] = items

        report['pans_found_results'] = matched_items

        if len(self.interesting_files) != 0:
            report['interesting_files']['total'] = len(self.interesting_files)

            report['interesting_files']['files'] = [
                f.path for f in self.interesting_files]

        initial_report: str = json.dumps(report, sort_keys=True)
        digest: str = panutils.get_text_hash(initial_report)
        report['hash'] = digest
        final_report: str = json.dumps(report, indent=4)

        basedir: str = os.path.dirname(os.path.abspath(path=path))
        if not exists(basedir):
            os.makedirs(basedir)

        with open(path, "w") as f:  # type: ignore
            f.write(final_report)

        logging.info("Created JSON report.")

    def append_hash(self, text_file: str) -> None:

        with open(text_file, encoding='utf-8', mode='r') as f:
            text: str = f.read()

        hash_check: str = panutils.get_text_hash(text)

        text += os.linesep + hash_check

        with open(text_file, encoding='utf-8', mode='w') as f:
            f.write(text)
