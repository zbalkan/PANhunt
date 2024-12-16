#! /usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright (c) 2014, Dionach Ltd. All rights reserved. See LICENSE file.
#
# PANhunt: search directories and sub directories for documents with PANs
# By BB
#
# Contributors: Zafer Balkan, 2023


import argparse
import logging
import os
import platform
import sys
from datetime import datetime
from typing import Final, Optional

import colorama

import panutils
from config import PANHuntConfiguration
from hunter import Hunter
from report import Report

APP_NAME: Final[str] = 'PANhunt'
APP_VERSION: Final[str] = '1.6'


def hunt_pans() -> Report:

    hunter = Hunter()
    # Start timer
    start: datetime = datetime.now()

    logging.info("Started searching in file(s).")

    # Start the hunt
    findings, failures = hunter.hunt()
    logging.info("Finished searching.")

    end: datetime = datetime.now()

    return Report(
        matched_files=findings,
        interesting_files=failures,
        start=start, end=end)


def display_report(report: Report) -> None:

    newline = '\n'
    header: str = f'PAN Hunt Report - {report.timestamp.strftime("%H:%M:%S %d/%m/%Y")}{newline}'
    header = f'{"=" * 100}{newline}'
    header += f'Searched {report.searched}{newline}'
    header += f'Excluded {report.excluded}{newline}'
    header += f'Command: {report.command}{newline}'
    header += f'Uname: {" | ".join(platform.uname())}{newline}'
    header += f'Elapsed time: {report.elapsed}{newline}'
    header += f'Found {report.pan_count} possible PANs.{newline}'
    header += f'{"=" * 100}{newline}{newline}'
    print(colorama.Fore.WHITE + header)

    pan_sep: str = '\n\t'
    for sf in report.matched_files:
        pan_header: str = f"FOUND PANs: {sf.abspath} ({panutils.size_friendly(sf.size)})"

        print(colorama.Fore.RED + panutils.unicode_to_ascii(pan_header))
        pan_list: str = '\t'
        for pan in sf.matches:
            pan_list += f"{pan}{pan_sep}"

        print(colorama.Fore.YELLOW + panutils.unicode_to_ascii(pan_list))

    if len(report.interesting_files) > 0:
        print(colorama.Fore.RED + 'Interesting Files to check separately, probably a permission or file size issue:')
        for interesting in report.interesting_files:
            print(colorama.Fore.YELLOW + '\t- ' + f'{panutils.unicode_to_ascii(interesting.abspath)} ({panutils.unicode_to_ascii(panutils.size_friendly(interesting.size))})')

    print(colorama.Fore.WHITE + f'Report written to {panutils.unicode_to_ascii(PANHuntConfiguration().get_report_path())}')


def main() -> None:

    logging.basicConfig(filename=os.path.join(panutils.get_root_dir(), f'{APP_NAME}.log'),
                        encoding='utf-8',
                        format='%(asctime)s:%(levelname)s:%(message)s',
                        datefmt="%Y-%m-%dT%H:%M:%S%z",
                        level=logging.DEBUG)

    sys.excepthook = logging.error
    logging.info('Starting')

    colorama.init()

    # Command Line Arguments
    arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog='panhunt', description=f'PAN Hunt v{APP_VERSION}: search directories and sub directories for documents containing PANs.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument(
        '-s', dest='search_dir', help='base directory to search in')
    arg_parser.add_argument(
        '-f', dest='file_path', help='File path for single file scan')
    arg_parser.add_argument('-x', dest='exclude_dirs',
                            help='directories to exclude from the search (use absolute paths)')
    arg_parser.add_argument(
        '-o', dest='report_dir', help='Report file directory for TXT formatted PAN report', default='./')
    arg_parser.add_argument(
        '-j', dest='json_dir', help='Report file directory for JSON formatted PAN report', default=None)
    arg_parser.add_argument(
        '-C', dest='config', help='configuration file to use')
    arg_parser.add_argument(
        '-X', dest='exclude_pan', help='PAN to exclude from search')
    arg_parser.add_argument('-q', dest='quiet', action='store_true',
                            default=False, help='No terminal output')

    args: argparse.Namespace = arg_parser.parse_args()

    config_file: Optional[str] = args.config

    # We need these as flags
    json_dir: Optional[str]
    quiet: bool

    # If exists, read the config file
    if config_file:
        PANHuntConfiguration().with_file(
            config_file=config_file)

        json_dir = PANHuntConfiguration().json_dir
        quiet = PANHuntConfiguration().quiet
    else:
        # Else, read the CLI parameters
        # Ask the user if they want to scan the root directory if no search directory or file path is provided
        if args.search_dir is None and args.file_path is None:
            print('No search directory or single file path specified.')
            print(
                'The default search target is the root directory ("/" for *Nix, "C:\\" for Windows).')
            response = input(
                'Do you want to search the root directory? (y/N): ')
            if response.lower() != 'y':
                sys.exit()

        search_dir = str(args.search_dir)
        file_path = str(args.file_path)
        report_dir = str(args.report_dir)
        excluded_directories_string = str(args.exclude_dirs)
        excluded_pans_string = str(args.exclude_pan)
        json_dir = str(args.json_dir)
        quiet = bool(args.quiet)

        PANHuntConfiguration().with_args(search_dir=search_dir,
                                         file_path=file_path,
                                         report_dir=report_dir,
                                         json_dir=json_dir,
                                         excluded_directories_string=excluded_directories_string,
                                         excluded_pans_string=excluded_pans_string)

    report: Report = hunt_pans()

    # report findings
    report.create_text_report()

    if json_dir:
        report.create_json_report()

    if not quiet:
        display_report(report=report)


if __name__ == "__main__":
    try:
        main()
        logging.info('Exiting')
    except KeyboardInterrupt:
        print('Cancelled by user.')
        logging.error("Cancelled by user.")
        logging.info('Exiting')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as ex:
        print('ERROR: ' + str(ex))
        logging.info('Exiting')
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)
