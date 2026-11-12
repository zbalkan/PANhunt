from __future__ import annotations

from re import Pattern

from .config import ScanConfiguration
from .pan import PAN
from .patterns import CardPatterns


class PanFinder:
    """Discover valid candidates and resolve brand-pattern overlaps by location."""

    def __init__(self, config: ScanConfiguration) -> None:
        self._config = config
        self._brands: list[tuple[str, Pattern[str]]] = CardPatterns().brands()

    def find_with_offsets(self, text: str) -> list[tuple[int, int, PAN]]:
        candidates: list[tuple[int, int, int, str, str]] = []
        for priority, (brand, regex) in enumerate(self._brands):
            for match in regex.finditer(text):
                pan = match.group(1)
                if brand == 'Maestro' and sum(ch in '0123456789' for ch in pan) < self._config.maestro_min_length:
                    continue
                if PAN.is_valid_luhn_checksum(pan) and not self._config.is_excluded(pan):
                    candidates.append((match.start(1), match.end(1), priority, brand, pan))

        # Prefer the earliest starting and longest valid interval. Brand priority
        # breaks equal-length ties reproducibly rather than reporting duplicates.
        candidates.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
        resolved: list[tuple[int, int, PAN]] = []
        previous_end = -1
        for start, end, _, brand, pan in candidates:
            if start < previous_end:
                continue
            resolved.append((start, end, PAN(brand=brand, pan=pan, start=start, end=end)))
            previous_end = end
        return resolved

    def find(self, text: str) -> list[PAN]:
        return [pan for _, _, pan in self.find_with_offsets(text)]
