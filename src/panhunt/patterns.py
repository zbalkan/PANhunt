from __future__ import annotations

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
                    r'(?:\D|^)((?:5[1-5][0-9]{2}|2(?:2[2-9][0-9]|[3-6][0-9]{2}|7[01][0-9]|720))(?:[ \-]?)[0-9]{4}(?:[ \-]?)[0-9]{4}(?:[ \-]?)[0-9]{4})(?:\D|$)',
                    flags=default_flag)),
                ('Visa', re.compile(
                    r'(?:\D|^)(4[0-9]{12}|4[0-9]{3}(?:[ \-]?[0-9]{4}){3}|4[0-9]{3}(?:[ \-]?[0-9]{4}){3}[ \-]?[0-9]{3})(?:\D|$)',
                    flags=default_flag)),
                ('AMEX', re.compile(
                    r'(?:\D|^)((?:3[47][0-9]{2})(?:[ \-]?)[0-9]{6}(?:[ \-]?)[0-9]{5})(?:\D|$)',
                    flags=default_flag)),
                ('DinersClub', re.compile(
                    r'(?:\D|^)((?:30[0-5][0-9]|3095|36[0-9]{2}|3[89][0-9]{2})(?:[ \-]?[0-9]){10})(?:\D|$)',
                    flags=default_flag)),
                ('Discover', re.compile(
                    r'(?:\D|^)(6011(?:[ \-]?[0-9]{4}){3}|65[0-9]{2}(?:[ \-]?[0-9]{4}){3}|64[4-9][0-9](?:[ \-]?[0-9]{4}){3}|622(?:12[6-9]|1[3-9][0-9]|[2-8][0-9]{2}|9[01][0-9]|92[0-5])[0-9]{10})(?:\D|$)',
                    flags=default_flag)),
                ('JCB', re.compile(
                    r'(?:\D|^)((?:2131|1800)(?:[ \-]?[0-9]){11}|35(?:2[89]|[3-8][0-9])(?:[ \-]?[0-9]){12,15})(?:\D|$)',
                    flags=default_flag)),
                ('Maestro', re.compile(
                    r'(?:\D|^)((?:5[0678]\d\d|6304|67\d\d)(?:[ \-]?\d){8,15})(?:\D|$)',
                    flags=default_flag)),
                ('UnionPay', re.compile(
                    r'(?:\D|^)(62(?:[ \-]?[0-9]){14,17})(?=\D|$)',
                    flags=default_flag))
            ]
            self._initialized = True  # Mark as initialized

    def brands(self) -> list[tuple[str, re.Pattern[str]]]:
        return self.__pattern_list
