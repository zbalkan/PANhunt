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

import panutils
from config import PANHuntConfigSingleton
from hunter import Hunter
from PANFile import PANFile
from report import Report
from stats import Stats

APP_VERSION: Final[str] = '1.3'


def print_report(all_files: list[PANFile]) -> None:

    logging.debug("Creating TXT report.")
    pan_sep: str = '\n\t'
    for pan_file in sorted([pan_file for pan_file in all_files if pan_file.matches], key=lambda x: x.filename):
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
          f'Report written to {panutils.unicode_to_ascii(PANHuntConfigSingleton.instance().get_report_path())}')


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

    logging.basicConfig(filename=os.path.join(panutils.get_root_dir(), 'PANhunt.log'),
                        encoding='utf-8',
                        format='%(asctime)s %(message)s',
                        level=logging.DEBUG)

    excepthook = logging.error
    logging.info('Starting')

    colorama.init()

    # Command Line Arguments
    arg_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog='panhunt', description=f'PAN Hunt v{APP_VERSION}: search directories and sub directories for documents containing PANs.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument(
        '-s', dest='search', help='base directory to search in', default='/')
    arg_parser.add_argument('-x', dest='exclude',
                            help='directories to exclude from the search')
    arg_parser.add_argument(
        '-t', dest='text_files', help='text file extensions to search', default='.doc,.xls,.ppt,.xml,.txt,.csv,.log,.rtf,.tmp,.bak,.rtf,.csv,.htm,.html,.js,.css,.md,.json')
    arg_parser.add_argument(
        '-z', dest='zip_files', help='zip file extensions to search', default='.docx,.xlsx,.pptx,.zip')
    arg_parser.add_argument('-e', dest='special_files',
                            help='special file extensions to search', default='.msg')
    arg_parser.add_argument(
        '-m', dest='mail_files', help='email file extensions to search', default='.pst')
    arg_parser.add_argument(
        '-l', dest='other_files', help='other file extensions to list', default='.ost,.accdb,.mdb')
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
    arg_parser.add_argument('-c', dest='check_file_hash',
                            help=argparse.SUPPRESS)  # hidden argument

    args: argparse.Namespace = arg_parser.parse_args()

    if args.check_file_hash:
        check_file_hash(args.check_file_hash)
        sys.exit()

    search_dir = str(args.search)
    report_dir = str(args.report_dir)
    excluded_directories_string = str(args.exclude)
    text_extensions_string = str(args.text_files)
    zip_extensions_string = str(args.zip_files)
    special_extensions_string = str(args.special_files)
    mail_extensions_string = str(args.mail_files)
    other_extensions_string = str(args.other_files)
    mask_pans: bool = not args.unmask
    excluded_pans_string = str(args.exclude_pan)
    json_dir: Optional[str] = args.json_dir
    config_file: Optional[str] = args.config
    quiet: bool = args.quiet

    # The singleton is initiated at the first call with the hardcoded default values.
    # If exists, read the config file
    if config_file:
        PANHuntConfigSingleton.instance().from_file(
            config_file=config_file)

    # Finally, read the CLI parameters as they override the default and config file values
    PANHuntConfigSingleton.instance().from_args(search_dir=search_dir,
                                                report_dir=report_dir,
                                                json_dir=json_dir,
                                                mask_pans=mask_pans,
                                                excluded_directories_string=excluded_directories_string,
                                                text_extensions_string=text_extensions_string,
                                                zip_extensions_string=zip_extensions_string,
                                                special_extensions_string=special_extensions_string,
                                                mail_extensions_string=mail_extensions_string,
                                                other_extensions_string=other_extensions_string,
                                                excluded_pans_string=excluded_pans_string)

    hunter = Hunter()
    stats: Stats = hunter.hunt_pans(quiet=quiet)

    # report findings
    report = Report(stats=stats)
    report.create_report()
    if json_dir:
        report.create_json_report()

    if not quiet:
        print_report(all_files=stats.all_files)


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
