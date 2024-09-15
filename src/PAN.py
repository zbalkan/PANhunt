import gc
import re


class PAN:
    """PAN: A class for recording PANs and their brand"""

    brand: str

    __pan: str
    __masked: str

    def __init__(self, brand: str, pan: str) -> None:

        self.brand = brand
        self.__masked = self.__mask_pan(pan)

        # Clear the PAN from memory ASAP
        del pan
        gc.collect()

    def __mask_pan(self, pan: str) -> str:
        """The first six and last four digits are the maximum number of digits that may be displayed"""
        standardized = pan.replace(' ', '').replace('-', '')
        masked: str = standardized[0:6] + \
            re.sub(r'\d', '*', standardized[6:-4]) + standardized[-4:]
        return masked

    def get_masked_pan(self) -> str:
        return f'{self.brand}:{self.__masked}'

    @staticmethod
    def is_valid_luhn_checksum(pan: str) -> bool:
        """ from wikipedia: https://en.wikipedia.org/wiki/Luhn_algorithm"""

        safe_pan: str = re.sub(r'[^\d]', '', pan)

        def digits_of(n) -> list[int]:
            return [int(d) for d in str(n)]

        digits: list[int] = digits_of(safe_pan)
        odd_digits: list[int] = digits[-1::-2]
        even_digits: list[int] = digits[-2::-2]
        checksum: int = 0
        checksum += sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))

        return checksum % 10 == 0
