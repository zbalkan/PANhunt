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
from finding import Finding


class Report:

    __total_files: int
    __start: datetime
    __end: datetime
    __searched: str
    __excluded: str
    pan_count: int
    matched_files: list[Finding]
    interesting_files: list[Finding]

    __command: str
    __timestamp: str
    __elapsed: timedelta

    def __init__(self,
                 files_searched_count: int,
                 matched_files: list[Finding],
                 interesting_files: list[Finding],
                 start: datetime,
                 end: datetime) -> None:
        '''excluded_dirs: list[str]'''
        self.__total_files = files_searched_count
        self.__start = start
        self.__end = end
        self.matched_files = matched_files
        self.interesting_files = interesting_files
        self.__searched = PANHuntConfiguration().search_dir
        self.__excluded = ','.join(PANHuntConfiguration().excluded_directories)
        self.__command = ' '.join(sys.argv)
        self.__timestamp = time.strftime("%H:%M:%S %d/%m/%Y")
        self.__elapsed = self.__end - self.__start
        self.pan_count = len(
            [pan for f in self.matched_files if f.matches for pan in f.matches])

    def create_text_report(self) -> None:

        path: str = PANHuntConfiguration().get_report_path()
        logging.info("Creating TXT report.")
        newline = '\n'
        report: str = f'PAN Hunt Report - {time.strftime("%H:%M:%S %d/%m/%Y")}{newline}{"=" * 100}{newline}'
        report += f'Searched {self.__searched}\nExcluded {self.__excluded}{newline}'
        report += f'Command: {self.__command}{newline}'
        report += f'Uname: {" | ".join(platform.uname())}{newline}'
        report += f'Elapsed time: {self.__elapsed}{newline}'
        report += f'Searched {self.__total_files} files. Found {self.pan_count} possible PANs.{newline}{"=" * 100}{newline}{newline}'

        for file in self.matched_files:
            report += f"FOUND PANs: {file.abspath}" + newline
            for pan in file.matches:
                report += f'\t{pan.get_masked_pan()}' + newline
            report += newline

        if len(self.interesting_files) != 0:
            report += 'Interesting Files to check separately, probably a permission issue:' + newline
            for interesting in sorted(self.interesting_files, key=lambda x: x.basename):
                report += f'{interesting.abspath} ({panutils.size_friendly(interesting.size)}){newline}'
                report += f'Error: {interesting.errors}{newline}'

        basedir: str = os.path.dirname(os.path.abspath(path=path))
        if not exists(basedir):
            os.makedirs(basedir)

        with open(path, encoding='utf-8', mode='w') as f:
            f.write(report)

        logging.info("Created TXT report.")

    def create_json_report(self) -> None:

        path: Optional[str] = PANHuntConfiguration().get_json_path()
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
                item += f"{pan.get_masked_pan()}"
                items.append(item)
            matched_items[file.abspath] = items

        report['pans_found_results'] = matched_items

        if len(self.interesting_files) > 0:
            report['interesting_files'] = {}
            report['interesting_files']['total'] = len(self.interesting_files)

            report['interesting_files']['files'] = []
            for interesting in self.interesting_files:
                report['interesting_files']['files'].append(
                    {'path': interesting.abspath, 'size': interesting.size, 'errors': interesting.errors})

        final_report: str = json.dumps(report, indent=4)

        basedir: str = os.path.dirname(os.path.abspath(path=path))
        if not exists(basedir):
            os.makedirs(basedir)

        with open(path, "w") as f:  # type: ignore
            f.write(final_report)

        logging.info("Created JSON report.")
