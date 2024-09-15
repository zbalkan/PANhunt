import gc
from re import Pattern

from config import PANHuntConfiguration
from PAN import PAN
from patterns import CardPatterns


class PanFinder():

    def find(self, text: str) -> list[PAN]:
        matches: list[PAN] = []
        brands: list[tuple[str, Pattern[str]]] = CardPatterns().brands()
        config = PANHuntConfiguration()

        for brand, regex in brands:
            for pan in regex.findall(text):
                if PAN.is_valid_luhn_checksum(pan=pan) and not config.is_excluded(pan=pan):
                    matches.append(PAN(brand=brand, pan=pan))
                    # Clear the PAN from memory ASAP
                    del pan
                    gc.collect()
                    break

        return matches
