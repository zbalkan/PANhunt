#! /usr/bin/env python3
#
# Copyright (c) 2014, Dionach Ltd. All rights reserved. See LICENSE file.
#
# PANhunt: search directories and sub directories for documents with PANs
# By BB
#
# Contributors: Zafer Balkan, 2023-2026

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Final

import colorama

from . import panutils
from .config import ScanConfiguration
from .presenter import CliPresenter
from .service import PanHuntService

APP_NAME: Final[str] = 'PANhunt'


def _log_uncaught_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        print('\nInterrupted. Exiting cleanly.')
        logging.info('Interrupted by user.')
        return

    logging.critical('Unhandled fatal error', exc_info=(exc_type, exc_value, exc_traceback))


def main() -> None:
    logging.basicConfig(
        filename=os.path.join(panutils.get_root_dir(), f'{APP_NAME}.log'),
        encoding='utf-8',
        format='%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        level=logging.DEBUG)

    sys.excepthook = _log_uncaught_exception
    logging.info('Starting')

    colorama.init()

    arg_parser = argparse.ArgumentParser(
        prog='panhunt',
        description='PANHunt : search directories and sub directories for documents containing PANs.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('target_path', nargs='?',
                            help='file or directory to search')
    arg_parser.add_argument('-x', dest='exclude_dirs', help='directories to exclude from the search (use absolute paths)')
    arg_parser.add_argument('-o', dest='report_dir', help='Report file directory for TXT formatted PAN report', default='./')
    arg_parser.add_argument('-j', dest='json_dir', help='Report file directory for JSON formatted PAN report', default=None)
    arg_parser.add_argument('-C', dest='config', help='configuration file to use')
    arg_parser.add_argument('-X', dest='exclude_pan', help='PAN to exclude from search')
    arg_parser.add_argument('-w', dest='workers', type=int, default=None, help='Number of worker threads (default: 1)')
    arg_parser.add_argument('-q', dest='quiet', action='store_true', default=False, help='No terminal output')

    args = arg_parser.parse_args()

    if args.config:
        config = ScanConfiguration.from_file(config_file=args.config, quiet=args.quiet or None)
    else:
        if args.target_path is None:
            print('No search target specified.')
            print('The default search target is the root directory ("/" for *Nix, "C:\\" for Windows).')
            response = input('Do you want to search the root directory? (y/N): ')
            if response.lower() != 'y':
                sys.exit()

        config = ScanConfiguration.from_args(
            target_path=args.target_path,
            report_dir=args.report_dir,
            json_dir=args.json_dir,
            excluded_directories_string=args.exclude_dirs,
            excluded_pans_string=args.exclude_pan,
            worker_count=args.workers,
            quiet=args.quiet)

    try:
        result = PanHuntService().scan(config)
        CliPresenter().show(result)
    except KeyboardInterrupt:
        raise


if __name__ == '__main__':
    try:
        main()
        logging.info('Exiting')
    except KeyboardInterrupt:
        print('\nInterrupted. Exiting cleanly.')
        logging.info('Interrupted by user.')
        logging.info('Exiting')
        raise SystemExit(130)
    except Exception as ex:
        print('ERROR: ' + str(ex))
        logging.exception('Unhandled fatal error')
        logging.info('Exiting')
        raise SystemExit(1)
