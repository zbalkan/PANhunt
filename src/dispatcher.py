from typing import Optional, Type

import mappings
from PAN import PAN
from patterns import CardPatterns
from scannable import ScannableFile
from scanner import ScannerBase


class Dispatcher:

    excluded_pans_list: list[str]
    patterns: CardPatterns

    def __init__(self, excluded_pans_list: list[str], patterns: CardPatterns) -> None:

        self.excluded_pans_list = excluded_pans_list
        self.patterns = patterns

    def dispatch(self, scannable: ScannableFile) -> list[ScannableFile]:

        container_type: Optional[Type[mappings.Archive]] = mappings.get_archive_by_file(
            mime_type=scannable.mime_type, extension=scannable.extension)

        if container_type is not None:
            # It is an archive. Enumerate, then call dispatch per file.
            container = container_type(path=scannable.path)
            children: list[ScannableFile] = container.get_children()
            total_results: list[ScannableFile] = []
            for f in children:
                updated_sf: list[ScannableFile] = self.dispatch(f)
                total_results.extend(updated_sf)
            return total_results
        else:
            return [self.__scan(scannable)]

    def __scan(self, scannable: ScannableFile) -> ScannableFile:

        scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
            mime_type=scannable.mime_type, extension=scannable.extension)
        if scanner_init is None:
            scannable.set_error(
                f"No scanner found for file type {scannable.mime_type}")
            return scannable

        scanner_instance = scanner_init(patterns=self.patterns)
        if scannable.value_bytes is not None:
            scanner_instance.from_buffer(buffer=scannable.value_bytes)

        scanner_instance.from_file(path=scannable.path)
        scanner_instance.encoding = scannable.encoding

        try:
            matches: list[PAN] = scanner_instance.scan(
                excluded_pans_list=self.excluded_pans_list)
            scannable.matches = matches
        except Exception as ex:
            scannable.set_error(str(ex))
        finally:
            return scannable
