import re
from typing import Optional


class CardPatterns:

    # Class-level variable to store the singleton instance
    __instance: Optional['CardPatterns'] = None

    __pattern_list: list[tuple[str, re.Pattern[str]]]

    def __new__(cls, *args, **kwargs) -> "CardPatterns":
        if cls.__instance is None:
            cls.__instance = super(CardPatterns, cls).__new__(
                cls, *args, **kwargs)
        return cls.__instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'):  # Ensures __init__ runs only once
            default_flag: re.RegexFlag = re.MULTILINE | re.UNICODE
            self.__pattern_list = [
                ('Mastercard', re.compile(
                    r'(?:\D|^)(5[1-5][0-9]{2}(?:\ |\-|)[0-9]{4}(?:\ |\-|)[0-9]{4}(?:\ |\-|)[0-9]{4})(?:\D|$)', flags=default_flag)),
                ('Visa', re.compile(
                    r'(?:\D|^)(4[0-9]{3}(?:\ |\-|)[0-9]{4}(?:\ |\-|)[0-9]{4}(?:\ |\-|)[0-9]{4})(?:\D|$)', flags=default_flag)),
                ('AMEX', re.compile(
                    r'(?:\D|^)((?:34|37)[0-9]{2}(?:\ |\-|)[0-9]{6}(?:\ |\-|)[0-9]{5})(?:\D|$)', flags=default_flag))
            ]
            self._initialized = True  # Mark as initialized

    def brands(self) -> list[tuple[str, re.Pattern[str]]]:
        return self.__pattern_list
