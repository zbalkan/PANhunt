import json
import logging
import os
import platform
import sys
import time
from datetime import datetime, timedelta

import panutils
from config import PANHuntConfigSingleton
from enums import FileTypeEnum
from PANFile import PANFile


class Report:

    total_files: int
    start: datetime
    end: datetime
    searched: str
    excluded: str
    pans_found: int
    matched_files: list[PANFile]
    interesting_files: list[PANFile]

    __command: str
    __timestamp: str
    __elapsed: timedelta

    def __init__(self,
                 pans_found:int,
                 all_files: list[PANFile],
                 start: datetime,
                 end: datetime) -> None:
        self.total_files = len(all_files)
        self.start = start
        self.end = end
        self.searched = PANHuntConfigSingleton.instance().search_dir
        self.excluded = ','.join(PANHuntConfigSingleton.instance().excluded_directories)
        self.pans_found = pans_found
        self.__command = ' '.join(sys.argv)
        self.__timestamp = time.strftime("%H:%M:%S %d/%m/%Y")
        self.__elapsed = self.end - self.start
        self.matched_files = sorted([pan_file for pan_file in all_files if pan_file.matches], key=lambda x: x.filename)
        self.interesting_files = sorted([
            pan_file for pan_file in all_files if pan_file.filetype == FileTypeEnum.Other], key=lambda x: x.path)


    def create_text_report(self) -> None:

        logging.debug("Creating TXT report.")

        pan_sep: str = '\n\t'
        pan_report: str = 'PAN Hunt Report - %s\n%s\n' % (
            time.strftime("%H:%M:%S %d/%m/%Y"), '=' * 100)
        pan_report += 'Searched %s\nExcluded %s\n' % (
            PANHuntConfigSingleton.instance().search_dir, ','.join(PANHuntConfigSingleton.instance().excluded_directories))
        pan_report += 'Command: %s\n' % (' '.join(sys.argv))
        pan_report += 'Uname: %s\n' % (' | '.join(platform.uname()))
        pan_report += f'Elapsed time: {self.__elapsed}\n'
        pan_report += 'Searched %s files. Found %s possible PANs.\n%s\n\n' % (
            self.total_files, self.pans_found, '=' * 100)

        for pan_file in self.matched_files:
            pan_header: str = f"FOUND PANs: {pan_file.path} ({panutils.size_friendly(pan_file.size)} {pan_file.modified.strftime('%d/%m/%Y')})"

            pan_report += pan_header + '\n'
            pan_list: str = '\t'
            for pan in pan_file.matches:
                if pan.sub_path != '':
                    pan_list += f'{pan.sub_path} '
                pan_list += f"{pan.get_masked_pan()}{pan_sep}"
            pan_report += pan_list.rstrip(pan_sep) + '\n\n'


        if len(self.interesting_files) != 0:
            pan_report += 'Interesting Files to check separately:\n'
        for pan_file in sorted(self.interesting_files, key=lambda x: x.filename):
            pan_report += '%s (%s %s)\n' % (pan_file.path,
                                            panutils.size_friendly(pan_file.size), pan_file.modified.strftime('%d/%m/%Y'))

        pan_report = pan_report.replace('\n', os.linesep)

        with open(PANHuntConfigSingleton.instance().get_report_path(), encoding='utf-8', mode='w') as f:
            f.write(pan_report)

        self.append_hash(PANHuntConfigSingleton.instance().get_report_path())

        logging.debug("Created TXT report.")

    def create_json_report(self) -> None:

        if PANHuntConfigSingleton.instance().get_json_path() is None:
            return

        logging.debug("Creating JSON report.")

        report: dict = {}
        report['timestamp'] = self.__timestamp
        report['searched'] = self.searched
        report['excluded'] = self.excluded
        report['command'] = self.__command
        report['elapsed'] = str(self.__elapsed)
        report['total_files'] = self.total_files
        report['pans_found'] = self.pans_found

        matched_items:dict[str,list[str]]= {}
        for pan_file in self.matched_files:
            items: list[str] = []
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
        with open(PANHuntConfigSingleton.instance().get_json_path(), "w") as f:  # type: ignore
            f.write(final_report)

        logging.debug("Created JSON report.")

    def append_hash(self, text_file: str) -> None:

        with open(text_file, encoding='utf-8', mode='r') as f:
            text: str = f.read()

        hash_check: str = panutils.get_text_hash(text)

        text += os.linesep + hash_check

        with open(text_file, encoding='utf-8', mode='w') as f:
            f.write(text)
