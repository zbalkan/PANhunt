from typing import Optional, Type

import mappings
from enums import FileCategoryEnum
from PAN import PAN
from patterns import CardPatterns
from scanner import ScannerBase


class Dispatcher:

    excluded_pans_list: list[str]
    search_extensions: dict[FileCategoryEnum, list[str]]
    patterns: CardPatterns

    def __init__(self, excluded_pans_list: list[str], search_extensions: dict[FileCategoryEnum, list[str]], patterns: CardPatterns) -> None:
        self.excluded_pans_list = excluded_pans_list
        self.search_extensions = search_extensions
        self.patterns = patterns

    def dispatch(self, mime_type: str, extension: str, path: str) -> list[PAN]:
        scanner_init: Optional[Type[ScannerBase]] = mappings.get_scanner_by_file(
            mime_type=mime_type, extension=extension)
        if scanner_init is None:
            return []

        scanner_instance = scanner_init(patterns=self.patterns)
        scanner_instance.from_file(path=path)

        return scanner_instance.scan(
            excluded_pans_list=self.excluded_pans_list, search_extensions=self.search_extensions)
