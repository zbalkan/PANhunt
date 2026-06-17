from __future__ import annotations

from re import Pattern

from .config import ScanConfiguration
from .pan import PAN
from .patterns import CardPatterns


class PanFinder:

    def __init__(self, config: ScanConfiguration) -> None:
        self._config = config
        self._brands: list[tuple[str, Pattern[str]]] = CardPatterns().brands()

    def find(self, text: str) -> list[PAN]:
        matches: list[PAN] = []

        for brand, regex in self._brands:
            for pan in regex.findall(text):
                if PAN.is_valid_luhn_checksum(pan=pan) and not self._config.is_excluded(pan=pan):
                    matches.append(PAN(brand=brand, pan=pan))

        return matches

