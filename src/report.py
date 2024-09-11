import json
import logging
import os
import platform
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

from genericpath import exists

import panutils
from config import PANHuntConfiguration
from doc import Document


class Report:

    __total_files: int
    __start: datetime
    __end: datetime
    __searched: str
    __excluded: str
    pan_count: int
    matched_files: list[Document]
    interesting_files: list[Document]
    __conf: PANHuntConfiguration

    __command: str
    __timestamp: str
    __elapsed: timedelta

    def __init__(self,
                 configuration: PANHuntConfiguration,
                 files_searched_count: int,
                 matched_files: list[Document],
                 interesting_files: list[Document],
                 start: datetime,
                 end: datetime) -> None:
        '''excluded_dirs: list[str]'''
        self.__total_files = files_searched_count
        self.__start = start
        self.__end = end
        self.__conf = configuration
        self.matched_files = matched_files
        self.interesting_files = interesting_files
        self.__searched = configuration.search_dir
        self.__excluded = ','.join(configuration.excluded_directories)
        self.__command = ' '.join(sys.argv)
        self.__timestamp = time.strftime("%H:%M:%S %d/%m/%Y")
        self.__elapsed = self.__end - self.__start
        self.pan_count = len(
            [pan for f in self.matched_files if f.matches for pan in f.matches])

    def create_text_report(self) -> None:

        path: str = self.__conf.get_report_path()
        logging.info("Creating TXT report.")

        pan_sep: str = '\n\t'
        pan_report: str = f'PAN Hunt Report - {time.strftime("%H:%M:%S %d/%m/%Y")}\n{"=" * 100}\n'
        pan_report += f'Searched {self.__searched}\nExcluded {self.__excluded}\n'
        pan_report += f'Command: {self.__command}\n'
        pan_report += f'Uname: {" | ".join(platform.uname())}\n'
        pan_report += f'Elapsed time: {self.__elapsed}\n'
        pan_report += f'Searched {self.__total_files} files. Found {self.pan_count} possible PANs.\n{"=" * 100}\n\n'

        for file in self.matched_files:
            pan_header: str = f"FOUND PANs: {file.path}"

            pan_report += pan_header + '\n'
            pan_list: str = '\t'

            for pan in file.matches:
                if pan.sub_path != '':
                    pan_list += f'{pan.sub_path} '
                pan_list += f"{pan.get_masked_pan()}{pan_sep}"
            pan_report += pan_list.rstrip(pan_sep) + '\n\n'

        if len(self.interesting_files) != 0:
            pan_report += 'Interesting Files to check separately, probably a permission issue:\n'
        for interesting in sorted(self.interesting_files, key=lambda x: x.filename):
            pan_report += f'{interesting.path} ({panutils.size_friendly(interesting.size)})\n'
            pan_report += f'Error: {interesting.errors}\n'

        pan_report = pan_report.replace('\n', os.linesep)

        basedir: str = os.path.dirname(os.path.abspath(path=path))
        if not exists(basedir):
            os.makedirs(basedir)

        with open(path, encoding='utf-8', mode='w') as f:
            f.write(pan_report)

        self.append_hash(path)

        logging.info("Created TXT report.")

    def create_json_report(self) -> None:

        path: Optional[str] = self.__conf.get_json_path()
        if path is None:
            return

        logging.info("Creating JSON report.")

        report: dict = {}
        report['timestamp'] = self.__timestamp
        report['searched'] = self.__searched
        report['excluded'] = self.__excluded
        report['command'] = self.__command
        report['elapsed'] = str(self.__elapsed)
        report['total_files'] = self.__total_files
        report['pans_found'] = self.pan_count

        matched_items: dict[str, list[str]] = {}
        for file in self.matched_files:

            items: list[str] = []
            for pan in file.matches:
                item: str = ''
                if pan.filename != '':
                    item += f"{pan.filename}\\{pan.sub_path} "
                item += f"{pan.get_masked_pan()}"
                items.append(item)
            matched_items[file.path] = items

        report['pans_found_results'] = matched_items

        if len(self.interesting_files) > 0:
            report['interesting_files'] = {}
            report['interesting_files']['total'] = len(self.interesting_files)

            report['interesting_files']['files'] = []
            for interesting in self.interesting_files:
                report['interesting_files']['files'].append(
                    {'path': interesting.path, 'size': interesting.size, 'errors': interesting.errors})

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
