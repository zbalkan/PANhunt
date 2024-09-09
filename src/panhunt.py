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
import sys
from datetime import datetime
from typing import Final, Optional

import colorama

import panutils
from config import PANHuntConfiguration
from hunter import Hunter
from report import Report
from scannable import Scannable

APP_NAME: Final[str] = 'PANhunt'
APP_VERSION: Final[str] = '1.5'


def hunt_pans(configuration: PANHuntConfiguration) -> Report:

    hunter = Hunter(configuration=configuration)
    # Start timer
    start: datetime = datetime.now()

    # Check if it is a single-file scan
    path: Optional[str] = configuration.file_path
    if path:
        logging.info(f"Added file to list: \"{path}\"")

        hunter.add_file(os.path.basename(path), os.path.dirname(path))

    logging.info("Started searching in file(s).")

    # check each file
    hunter.hunt()

    results: list[Scannable] = hunter.get_results()
    logging.info("Finished searching.")

    end: datetime = datetime.now()

    interesting: list[Scannable] = [
        result for result in results if result.errors is not None and len(result.errors) > 0]
    matches: list[Scannable] = [
        result for result in results if result.matches is not None and len(result.matches) > 0]

    return Report(
        configuration=configuration,
        files_searched_count=hunter.count,
        matched_files=matches,
        interesting_files=interesting,
        start=start, end=end)


def display_report(report: Report, configuration: PANHuntConfiguration) -> None:

    pan_sep: str = '\n\t'
    for sf in report.matched_files:
        pan_header: str = f"FOUND PANs: {sf.path} ({panutils.size_friendly(sf.size)})"

        print(colorama.Fore.RED + panutils.unicode_to_ascii(pan_header))
        pan_list: str = '\t'
        for pan in sf.matches:
            if pan.sub_path != '':
                pan_list += f'{pan.sub_path} '
            pan_list += f"{pan.get_masked_pan()}{pan_sep}"

        print(colorama.Fore.YELLOW +
              panutils.unicode_to_ascii(pan_list))

    if len(report.interesting_files) > 0:
        print(colorama.Fore.RED +
              'Interesting Files to check separately, probably a permission issue:')
        for interesting in report.interesting_files:
            print(colorama.Fore.YELLOW + '\t- ' +
                  f'{panutils.unicode_to_ascii(interesting.path)} ({panutils.unicode_to_ascii(panutils.size_friendly(interesting.size))})')

    print(colorama.Fore.WHITE +
          f'Report written to {panutils.unicode_to_ascii(configuration.get_report_path())}')


def check_file_hash(text_file: str) -> None:

    with open(text_file, encoding='utf-8', mode='r') as f:
        text_output: str = f.read()

    hash_pos: int = text_output.rfind(os.linesep)
    hash_in_file: str = text_output[hash_pos + len(os.linesep):]
    hash_check: str = panutils.get_text_hash(text_output[:hash_pos])
    if hash_in_file == hash_check:
        print(colorama.Fore.GREEN + 'Hashes OK')
    else:
        print(colorama.Fore.RED + 'Hashes Not OK')
    print(colorama.Fore.WHITE + hash_in_file + '\n' + hash_check)


def main() -> None:

    logging.basicConfig(filename=os.path.join(panutils.get_root_dir(), f'{APP_NAME}.log'),
                        encoding='utf-8',
                        format='%(asctime)s:%(levelname)s:%(message)s',
                        datefmt="%Y-%m-%dT%H:%M:%S%z",
                        level=logging.DEBUG)

    excepthook = logging.error
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
        '-j', dest='json_dir', help='Report file directory for JSON formatted PAN report')
    arg_parser.add_argument('-u', dest='unmask', action='store_true',
                            default=False, help='unmask PANs in output')
    arg_parser.add_argument(
        '-C', dest='config', help='configuration file to use')
    arg_parser.add_argument(
        '-X', dest='exclude_pan', help='PAN to exclude from search')
    arg_parser.add_argument('-q', dest='quiet', action='store_true',
                            default=False, help='No terminal output')
    arg_parser.add_argument('-v', dest='verbose', action='store_true',
                            default=False, help='Verbose logging')
    arg_parser.add_argument('-c', dest='check_file_hash',
                            help=argparse.SUPPRESS)  # hidden argument

    args: argparse.Namespace = arg_parser.parse_args()

    if args.check_file_hash:
        check_file_hash(args.check_file_hash)
        sys.exit()

    search_dir = str(args.search_dir)
    file_path = str(args.file_path)
    report_dir = str(args.report_dir)
    excluded_directories_string = str(args.exclude_dirs)
    mask_pans: bool = not args.unmask
    excluded_pans_string = str(args.exclude_pan)
    json_dir: Optional[str] = args.json_dir
    config_file: Optional[str] = args.config
    verbose: bool = args.verbose

    # Initiated with default values
    config: PANHuntConfiguration = PANHuntConfiguration()

    # If exists, read the config file
    if config_file:
        config.with_file(
            config_file=config_file)
    else:
        # Else, read the CLI parameters
        config.with_args(search_dir=search_dir,
                         file_path=file_path,
                         report_dir=report_dir,
                         json_dir=json_dir,
                         mask_pans=mask_pans,
                         excluded_directories_string=excluded_directories_string,
                         excluded_pans_string=excluded_pans_string,
                         verbose=verbose)

    report: Report = hunt_pans(configuration=config)

    # report findings
    report.create_text_report()

    if json_dir:
        report.create_json_report()

    display_report(report=report, configuration=config)


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
