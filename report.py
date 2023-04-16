import json
import logging
import os
import platform
import sys
import time

import panutils
from config import PANHuntConfigSingleton
from PANFile import PANFile
from stats import Stats


class Report:

    stats: Stats

    def __init__(self, stats: Stats) -> None:
        self.stats = stats

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
        pan_report += f'Elapsed time: {self.stats.end - self.stats.start}\n'
        pan_report += 'Searched %s files. Found %s possible PANs.\n%s\n\n' % (
            self.stats.files_total, self.stats.pans_found, '=' * 100)

        for pan_file in sorted([pan_file for pan_file in self.stats.all_files if pan_file.matches], key=lambda x: x.filename):
            pan_header: str = f"FOUND PANs: {pan_file.path} ({panutils.size_friendly(pan_file.size)} {pan_file.modified.strftime('%d/%m/%Y')})"

            pan_report += pan_header + '\n'
            pan_list: str = '\t' + \
                pan_sep.join([pan.get_masked_pan()
                              for pan in pan_file.matches])
            pan_report += pan_list + '\n\n'

        interesting_files: list[PANFile] = [
            pan_file for pan_file in self.stats.all_files if pan_file.filetype == 'OTHER']
        if len(interesting_files) != 0:
            pan_report += 'Interesting Files to check separately:\n'
        for pan_file in sorted(interesting_files, key=lambda x: x.filename):
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
        report['timestamp'] = time.strftime("%H:%M:%S %d/%m/%Y")
        report['searched'] = PANHuntConfigSingleton.instance().search_dir
        report['excluded'] = ','.join(
            PANHuntConfigSingleton.instance().excluded_directories)
        report['command'] = ' '.join(sys.argv)
        report['elapsed'] = str(self.stats.end - self.stats.start)
        report['total_files'] = self.stats.files_total
        report['pans_found'] = self.stats.pans_found
        report['pans_found_results'] = []

        match_dict = {}
        for pan_file in sorted([pan_file for pan_file in self.stats.all_files if pan_file.matches], key=lambda x: x.path):
            match_dict[pan_file.path] = [pan.get_masked_pan()
                                         for pan in pan_file.matches]

        report['pans_found_results'].append(match_dict)

        interesting_files: list[PANFile] = sorted([
            pan_file for pan_file in self.stats.all_files if pan_file.filetype == 'OTHER'], key=lambda x: x.path)
        if len(interesting_files) != 0:
            report['interesting_files']['total'] = len(interesting_files)

            report['interesting_files']['files'] = [
                f.path for f in interesting_files]

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
