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

    start: datetime
    end: datetime
    searched: str
    excluded: str
    pan_count: int
    matched_files: list[Finding]
    interesting_files: list[Finding]

    command: str
    timestamp: datetime
    elapsed: timedelta

    def __init__(self,
                 matched_files: list[Finding],
                 interesting_files: list[Finding],
                 start: datetime,
                 end: datetime) -> None:
        '''excluded_dirs: list[str]'''
        self.start = start
        self.end = end
        self.matched_files = matched_files
        self.interesting_files = interesting_files
        self.searched = PANHuntConfiguration().search_dir
        self.excluded = ','.join(PANHuntConfiguration().excluded_directories)
        self.command = ' '.join(sys.argv)
        self.timestamp = datetime.now()
        self.elapsed = self.end - self.start
        self.pan_count = len(
            [pan for f in self.matched_files if f.matches for pan in f.matches])

    def create_text_report(self) -> None:

        path: str = PANHuntConfiguration().get_report_path()
        logging.info("Creating TXT report.")
        newline = '\n'
        report: str = f'PAN Hunt Report - {time.strftime("%H:%M:%S %d/%m/%Y")}{newline}{"=" * 100}{newline}'
        report += f'Searched {self.searched}\nExcluded {self.excluded}{newline}'
        report += f'Command: {self.command}{newline}'
        report += f'Uname: {" | ".join(platform.uname())}{newline}'
        report += f'Elapsed time: {self.elapsed}{newline}'
        report += f'Found {self.pan_count} possible PANs.{newline}{"=" * 100}{newline}{newline}'

        for file in self.matched_files:
            report += f"FOUND PANs: {file.abspath}" + newline
            for pan in file.matches:
                report += f'\t{pan}' + newline
            report += newline

        if len(self.interesting_files) > 0:
            report += 'Interesting Files to check separately, probably a permission or file size issue:' + newline
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
        report['timestamp'] = self.timestamp.strftime("%H:%M:%S %d/%m/%Y")
        report['searched'] = self.searched
        report['excluded'] = self.excluded
        report['command'] = self.command
        report['elapsed'] = str(self.elapsed)
        report['pans_found'] = self.pan_count

        matched_items: dict[str, list[str]] = {}
        for file in self.matched_files:

            items: list[str] = []
            for pan in file.matches:
                item: str = ''
                item += str(pan)
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
