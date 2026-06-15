import json
import logging
import os
import platform
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

import panutils
from config import ScanConfiguration
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
                 end: datetime,
                 config: ScanConfiguration) -> None:
        self.start = start
        self.end = end
        self.matched_files = matched_files
        self.interesting_files = interesting_files
        self.searched = config.search_dir
        self.excluded = ','.join(config.excluded_directories)
        self.command = ' '.join(sys.argv)
        self.timestamp = datetime.now()
        self.elapsed = self.end - self.start
        self.pan_count = len([pan for f in self.matched_files if f.matches for pan in f.matches])
        self._config = config

    @property
    def report_path(self) -> str:
        return self._config.get_report_path()

    def create_text_report(self) -> None:
        path: str = self._config.get_report_path()
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
        if not os.path.exists(basedir):
            os.makedirs(basedir)

        with open(path, encoding='utf-8', mode='w') as f:
            f.write(report)

        logging.info("Created TXT report.")

    def create_json_report(self) -> None:
        path: Optional[str] = self._config.get_json_path()
        if path is None:
            return

        logging.info("Creating JSON report.")

        report: dict = {
            'timestamp': self.timestamp.strftime("%H:%M:%S %d/%m/%Y"),
            'searched': self.searched,
            'excluded': self.excluded,
            'command': self.command,
            'elapsed': str(self.elapsed),
            'pans_found': self.pan_count,
        }

        matched_items: dict[str, list[str]] = {}
        for file in self.matched_files:
            matched_items[file.abspath] = [str(pan) for pan in file.matches]
        report['pans_found_results'] = matched_items

        if len(self.interesting_files) > 0:
            report['interesting_files'] = {
                'total': len(self.interesting_files),
                'files': [
                    {'path': f.abspath, 'size': f.size, 'errors': f.errors}
                    for f in self.interesting_files
                ]
            }

        basedir: str = os.path.dirname(os.path.abspath(path=path))
        if not os.path.exists(basedir):
            os.makedirs(basedir)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(report, indent=4))

        logging.info("Created JSON report.")
