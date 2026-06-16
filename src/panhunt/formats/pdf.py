from io import BytesIO
from typing import Union

from pdfminer.high_level import extract_text


class Pdf:

    __file: Union[str, BytesIO]

    def __init__(self, file: Union[str, BytesIO]) -> None:
        self.__file = file

    def get_text(self) -> str:
        if isinstance(self.__file, str):
            with open(self.__file, "rb") as in_file:
                return extract_text(in_file)

        self.__file.seek(0)
        return extract_text(self.__file)
