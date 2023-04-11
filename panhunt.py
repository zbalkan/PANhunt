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
from typing import Final, Optional

import colorama

from config import PANHuntConfigSingleton
from Hunter import Hunter

APP_VERSION: Final[str] = '1.3'


def main() -> None:
    application_path: str = '.'
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    logging.basicConfig(filename=os.path.join(application_path, 'PANhunt.log'),
                        encoding='utf-8',
                        format='%(asctime)s %(message)s',
                        level=logging.DEBUG)

    excepthook = logging.error
    logging.info('Starting')

    colorama.init()

    # Command Line Arguments
    arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog='panhunt', description='PAN Hunt v%s: search directories and sub directories for documents containing PANs.' % APP_VERSION, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument(
        '-s', dest='search', help='base directory to search in')
    arg_parser.add_argument('-x', dest='exclude',
                            help='directories to exclude from the search')
    arg_parser.add_argument(
        '-t', dest='text_files', help='text file extensions to search')
    arg_parser.add_argument(
        '-z', dest='zip_files', help='zip file extensions to search')
    arg_parser.add_argument('-e', dest='special_files',
                            help='special file extensions to search')
    arg_parser.add_argument(
        '-m', dest='mail_files', help='email file extensions to search')
    arg_parser.add_argument(
        '-l', dest='other_files', help='other file extensions to list')
    arg_parser.add_argument(
        '-o', dest='outfile', help='output file name for PAN report')
    arg_parser.add_argument('-u', dest='unmask', action='store_true',
                            default=False, help='unmask PANs in output')
    arg_parser.add_argument(
        '-C', dest='config', help='configuration file to use')
    arg_parser.add_argument(
        '-X', dest='exclude_pan', help='PAN to exclude from search')
    arg_parser.add_argument(
        '-j', dest='json_path', help='Create JSON formatted report')

    arg_parser.add_argument('-c', dest='check_file_hash',
                            help=argparse.SUPPRESS)  # hidden argument

    args: argparse.Namespace = arg_parser.parse_args()

    hunter = Hunter()
    if args.check_file_hash:
        hunter.check_file_hash(args.check_file_hash)
        sys.exit()

    search_dir = str(args.search)
    output_file = str(args.outfile)
    excluded_directories_string = str(args.exclude)
    text_extensions_string = str(args.text_files)
    zip_extensions_string = str(args.zip_files)
    special_extensions_string = str(args.special_files)
    mail_extensions_string = str(args.mail_files)
    other_extensions_string = str(args.other_files)
    mask_pans: bool = not args.unmask
    excluded_pans_string = str(args.exclude_pan)
    json_path: Optional[str] = args.json_path
    config_file: Optional[str] = args.config

    # The singleton is initiated at the first call with the hardcoded default values.
    # If exists, read the config file
    if config_file:
        PANHuntConfigSingleton.instance().from_file(
            config_file=config_file)

    # Finally, read the CLI parameters as they override the default and config file values
    PANHuntConfigSingleton.instance().from_args(search_dir=search_dir,
                                                output_file=output_file,
                                                mask_pans=mask_pans,
                                                excluded_directories_string=excluded_directories_string,
                                                text_extensions_string=text_extensions_string,
                                                zip_extensions_string=zip_extensions_string,
                                                special_extensions_string=special_extensions_string,
                                                mail_extensions_string=mail_extensions_string,
                                                other_extensions_string=other_extensions_string,
                                                excluded_pans_string=excluded_pans_string,
                                                json_path=json_path)

    total_files_searched, pans_found, all_files = hunter.hunt_pans()

    # report findings
    hunter.create_report(all_files,
                         total_files_searched, pans_found)

    if json_path:
        hunter.create_json_report(all_files, total_files_searched, pans_found)


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
