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
                    r'(?<![A-Za-z0-9_])((?:5[1-5]\d{2}|222[1-9]|22[3-9]\d|2[3-6]\d{2}|27[01]\d|2720)[ -]?\d{4}[ -]?\d{4}[ -]?\d{4})(?!(?:[ -]?\d)|[A-Za-z0-9_])',
                    flags=default_flag)),
                ('Visa', re.compile(
                    r'(?<![A-Za-z0-9_])(4\d{3}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4})(?!(?:[ -]?\d)|[A-Za-z0-9_])',
                    flags=default_flag)),
                ('AMEX', re.compile(
                    r'(?<![A-Za-z0-9_])(3[47]\d{13}|3[47]\d{2}-\d{6}-\d{5}|3[47]\d{2} \d{6} \d{5})(?!(?:[ -]?\d)|[A-Za-z0-9_])',
                    flags=default_flag)),
                ('DinersClub', re.compile(
                    r'(?:\D|^)((?:30[0-5][0-9]|3095|36[0-9]{2}|3[89][0-9]{2})(?:[ \-]?[0-9]){10})(?:\D|$)',
                    flags=default_flag)),
                ('Discover', re.compile(
                    r'(?:\D|^)(6011(?:[ \-]?[0-9]{4}){3}|65[0-9]{2}(?:[ \-]?[0-9]{4}){3}|64[4-9][0-9](?:[ \-]?[0-9]{4}){3}|622(?:12[6-9]|1[3-9][0-9]|[2-8][0-9]{2}|9[01][0-9]|92[0-5])[0-9]{10})(?:\D|$)',
                    flags=default_flag)),
                ('JCB', re.compile(
                    r'\b((?:(?:2131|1800)(?:[ -]?\d){11})|(?:35(?:2[89]|[3-8]\d)(?:[ -]?\d){12}))\b(?![ -]?\d)',
                    flags=default_flag)),
                ('Maestro', re.compile(
                    r'\b((?:5[0678]\d{2}|6013|6[237]\d{2})(?:[ -]?\d){12,15})\b(?![ -]?\d)',
                    flags=default_flag)),
                ('UnionPay', re.compile(
                    r"(?<!\d)(622(?:[ -]?\d){13,16}|(?:621977|60(?:1428|2969|3265|3367|3601|3694|3708))(?:[ -]?\d){10})(?![ -]?\d)",
                    flags=default_flag))
            ]
            self._initialized = True  # Mark as initialized

    def brands(self) -> list[tuple[str, re.Pattern[str]]]:
        return self.__pattern_list
