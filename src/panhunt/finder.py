from __future__ import annotations

from re import Pattern

from .config import ScanConfiguration
from .constants import MIN_PAN_LENGTH
from .pan import PAN
from .patterns import CardPatterns


class PanFinder:

    def __init__(self, config: ScanConfiguration) -> None:
        self._config = config
        self._brands: list[tuple[str, Pattern[str]]] = CardPatterns().brands()

    def find(self, text: str) -> list[PAN]:
        matches: list[PAN] = []

        if not self._has_pan_candidate(text):
            return matches

        for brand, regex in self._brands:
            for pan in regex.findall(text):
                if PAN.is_valid_luhn_checksum(pan=pan) and not self._config.is_excluded(pan=pan):
                    matches.append(PAN(brand=brand, pan=pan))

        return matches

    @staticmethod
    def _has_pan_candidate(text: str) -> bool:
        digit_count = 0
        for character in text:
            if character.isdecimal():
                digit_count += 1
                if digit_count >= MIN_PAN_LENGTH:
                    return True
        return False
