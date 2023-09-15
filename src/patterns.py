import re


class CardPatterns:

    __pattern_list: list  # list[tuple[str, re.Pattern[str]]]

    def __init__(self) -> None:
        default_flag: re.RegexFlag = re.MULTILINE | re.UNICODE
        self.__pattern_list = [('Mastercard', re.compile(r'(?:\D|^)(5[1-5][0-9]{2}(?:\ |\-|)[0-9]{4}(?:\ |\-|)[0-9]{4}(?:\ |\-|)[0-9]{4})(?:\D|$)', flags=default_flag)),
                               ('Visa', re.compile(
                                   r'(?:\D|^)(4[0-9]{3}(?:\ |\-|)[0-9]{4}(?:\ |\-|)[0-9]{4}(?:\ |\-|)[0-9]{4})(?:\D|$)', flags=default_flag)),
                               ('AMEX', re.compile(r'(?:\D|^)((?:34|37)[0-9]{2}(?:\ |\-|)[0-9]{6}(?:\ |\-|)[0-9]{5})(?:\D|$)', flags=default_flag))]

    def brands(self) -> list:  # list[tuple[str, re.Pattern[str]]]:
        return self.__pattern_list
