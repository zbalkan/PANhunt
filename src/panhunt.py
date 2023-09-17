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
from typing import Optional

import colorama

import panutils
from config import PANHuntConfiguration
from hunter import Hunter
from pbar import DocProgressbar
from report import Report

APP_NAME: str = 'PANhunt'
APP_VERSION: str = '1.4'


def hunt_pans(quiet: bool, configuration: PANHuntConfiguration) -> Report:

    hunter = Hunter(configuration=configuration)
    # Start timer
    start: datetime = datetime.now()

    # Check if it is a single-file scan
    path: Optional[str] = configuration.file_path
    if path:
        logging.info(f"Added file to list: \"{path}\"")

        hunter.add_single_file(os.path.basename(path), os.path.dirname(path))

    else:
        logging.info("Started searching directories.")

        # find all files to check
        if quiet:
            # Wait until generator finishes
            for _ in hunter.get_scannable_files():
                ...
        else:
            with DocProgressbar('Doc') as pbar:
                for docs_found, root_total_items, root_items_completed in hunter.get_scannable_files():
                    pbar.update(items_found=docs_found,
                                items_total=root_total_items, items_completed=root_items_completed)

        logging.info("Finished searching directories.")

    logging.info("Started searching in file(s).")

    # check each file
    pans_found: int = 0

    if quiet:
        for pans_found, files_completed in hunter.scan_files():
            ...
    else:
        with DocProgressbar(hunt_type='PAN') as pbar:
            for pans_found, files_completed in hunter.scan_files():
                pbar.update(items_found=pans_found,
                            items_total=len(hunter.get_files()), items_completed=files_completed)

    logging.info("Finished searching in files.")

    logging.info("Finished searching.")

    # Stop timer
    end: datetime = datetime.now()

    return Report(search_dir=configuration.search_dir, excluded_dirs=configuration.excluded_directories, pans_found=pans_found, all_files=hunter.get_files(), start=start, end=end)


def print_report(report: Report, configuration: PANHuntConfiguration) -> None:

    logging.info("Creating TXT report.")
    pan_sep: str = '\n\t'
    for pan_file in report.matched_files:
        pan_header: str = f"FOUND PANs: {pan_file.path} ({panutils.size_friendly(pan_file.size)} {pan_file.modified.strftime('%d/%m/%Y')})"

        print(colorama.Fore.RED + panutils.unicode_to_ascii(pan_header))
        pan_list: str = '\t'
        for pan in pan_file.matches:
            if pan.sub_path != '':
                pan_list += f'{pan.sub_path} '
            pan_list += f"{pan.get_masked_pan()}{pan_sep}"

        print(colorama.Fore.YELLOW +
              panutils.unicode_to_ascii(pan_list))

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

    # logging.basicConfig(filename=os.path.join(panutils.get_root_dir(), 'PANhunt.log'),
    #                     encoding='utf-8',
    #                     format='%(asctime)s:%(levelname)s:%(message)s',
    #                     datefmt="%Y-%m-%dT%H:%M:%S%z",
    #                     level=logging.INFO)

    logging.basicConfig(filename=os.path.join(panutils.get_root_dir(), f'{APP_NAME}.log'),
                        format='%(asctime)s:%(levelname)s:%(message)s',
                        datefmt="%Y-%m-%dT%H:%M:%S%z",
                        level=logging.INFO)

    excepthook = logging.error
    logging.info('Starting')

    colorama.init()

    # Command Line Arguments
    arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog='panhunt', description=f'PAN Hunt v{APP_VERSION}: search directories and sub directories for documents containing PANs.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument(
        '-s', dest='search_dir', help='base directory to search in', default='/')
    arg_parser.add_argument(
        '-f', dest='file_path', help='File path for single file scan')
    arg_parser.add_argument('-x', dest='exclude_dirs',
                            help='directories to exclude from the search (use absolute paths)', default='C:\\Windows,C:\\Program Files,C:\\Program Files (x86),/mnt,/dev,/proc')
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
    quiet: bool = args.quiet
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

    report: Report = hunt_pans(quiet=quiet, configuration=config)

    # report findings
    report.create_text_report(path=config.get_report_path())

    if json_dir:
        report.create_json_report(path=config.get_json_path())

    if not quiet:
        print_report(report=report, configuration=config)


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
