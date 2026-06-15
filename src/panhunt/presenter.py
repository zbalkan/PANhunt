import json
import logging
import os
import platform
import sys

import colorama

from . import panutils
from .models import ScanResult
from .report import ReportGenerator


class CliPresenter:
    """Drives all CLI output: writes report files and prints coloured terminal output."""

    def __init__(self) -> None:
        self._report_gen = ReportGenerator()

    def show(self, result: ScanResult) -> None:
        """Save report files and, when not quiet, print results to the terminal."""
        self._save_text(result)

        if result.config.json_dir:
            self._save_json(result)

        if not result.config.quiet:
            self._print(result)

    # ------------------------------------------------------------------
    # File writing
    # ------------------------------------------------------------------

    def _save_text(self, result: ScanResult) -> None:
        path = result.config.get_report_path()
        logging.info("Creating TXT report.")
        _write_file(path, self._report_gen.generate_text(result))
        logging.info("Created TXT report.")

    def _save_json(self, result: ScanResult) -> None:
        path = result.config.get_json_path()
        if path is None:
            return
        logging.info("Creating JSON report.")
        _write_file(path, json.dumps(self._report_gen.generate_json(result), indent=4))
        logging.info("Created JSON report.")

    # ------------------------------------------------------------------
    # Terminal display
    # ------------------------------------------------------------------

    def _print(self, result: ScanResult) -> None:
        newline = '\n'
        sep = '=' * 100
        header = (
            f'PAN Hunt Report - {result.start_time.strftime("%H:%M:%S %d/%m/%Y")}{newline}'
            f'{sep}{newline}'
            f'Searched {result.config.search_dir}{newline}'
            f'Excluded {",".join(result.config.excluded_directories)}{newline}'
            f'Command: {" ".join(sys.argv)}{newline}'
            f'Uname: {" | ".join(platform.uname())}{newline}'
            f'Elapsed time: {result.elapsed}{newline}'
            f'Found {result.pan_count} possible PANs.{newline}'
            f'{sep}{newline}'
        )
        print(colorama.Fore.WHITE + header)

        pan_sep = '\n\t'
        for sf in result.matched_files:
            print(colorama.Fore.RED + panutils.unicode_to_ascii(
                f'FOUND PANs: {sf.abspath} ({panutils.size_friendly(sf.size)})'))
            pan_list = '\t' + ''.join(f'{pan}{pan_sep}' for pan in sf.matches)
            print(colorama.Fore.YELLOW + panutils.unicode_to_ascii(pan_list))

        if result.interesting_files:
            print(colorama.Fore.RED +
                  'Interesting Files to check separately, probably a permission or file size issue:')
            for interesting in result.interesting_files:
                print(colorama.Fore.YELLOW + '\t- ' + panutils.unicode_to_ascii(
                    f'{interesting.abspath} ({panutils.size_friendly(interesting.size)})'))

        print(colorama.Fore.WHITE + f'Report written to {panutils.unicode_to_ascii(result.config.get_report_path())}')


# ------------------------------------------------------------------
# Shared helper
# ------------------------------------------------------------------

def _write_file(path: str, content: str) -> None:
    basedir = os.path.dirname(os.path.abspath(path))
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
