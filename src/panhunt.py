#! /usr/bin/env python3
#
# Copyright (c) 2014, Dionach Ltd. All rights reserved. See LICENSE file.
#
# PANhunt: search directories and sub directories for documents with PANs
# By BB
#
# Contributors: Zafer Balkan, 2023-2026


import argparse
import logging
import os
import sys
from typing import Final

import colorama

import panutils
from config import ScanConfiguration
from presenter import CliPresenter
from service import PanHuntService

APP_NAME: Final[str] = 'PANhunt'


def main() -> None:
    logging.basicConfig(
        filename=os.path.join(panutils.get_root_dir(), f'{APP_NAME}.log'),
        encoding='utf-8',
        format='%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        level=logging.DEBUG)

    sys.excepthook = logging.error
    logging.info('Starting')

    colorama.init()

    arg_parser = argparse.ArgumentParser(
        prog='panhunt',
        description='PANHunt : search directories and sub directories for documents containing PANs.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('-s', dest='search_dir', help='base directory to search in')
    arg_parser.add_argument('-f', dest='file_path', help='File path for single file scan')
    arg_parser.add_argument('-x', dest='exclude_dirs', help='directories to exclude from the search (use absolute paths)')
    arg_parser.add_argument('-o', dest='report_dir', help='Report file directory for TXT formatted PAN report', default='./')
    arg_parser.add_argument('-j', dest='json_dir', help='Report file directory for JSON formatted PAN report', default=None)
    arg_parser.add_argument('-C', dest='config', help='configuration file to use')
    arg_parser.add_argument('-X', dest='exclude_pan', help='PAN to exclude from search')
    arg_parser.add_argument('-q', dest='quiet', action='store_true', default=False, help='No terminal output')

    args = arg_parser.parse_args()

    if args.config:
        config = ScanConfiguration.from_file(config_file=args.config, quiet=args.quiet or None)
    else:
        if args.search_dir is None and args.file_path is None:
            print('No search directory or single file path specified.')
            print('The default search target is the root directory ("/" for *Nix, "C:\\" for Windows).')
            response = input('Do you want to search the root directory? (y/N): ')
            if response.lower() != 'y':
                sys.exit()

        config = ScanConfiguration.from_args(
            search_dir=args.search_dir,
            file_path=args.file_path,
            report_dir=args.report_dir,
            json_dir=args.json_dir,
            excluded_directories_string=args.exclude_dirs,
            excluded_pans_string=args.exclude_pan,
            quiet=args.quiet)

    result = PanHuntService().scan(config)
    CliPresenter().show(result)


if __name__ == '__main__':
    try:
        main()
        logging.info('Exiting')
    except KeyboardInterrupt:
        print('Cancelled by user.')
        logging.error('Cancelled by user.')
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
