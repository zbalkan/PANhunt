from io import BufferedReader, BytesIO
from typing import Optional, Union

from pdfminer.high_level import extract_text


class Pdf:

    __file: Optional[Union[str, BytesIO]] = None

    def __init__(self, file: Union[str, BytesIO]) -> None:
        self.__file = file

    def get_text(self) -> str:
        in_file: Optional[Union[BufferedReader, BytesIO]] = None
        if isinstance(self.__file, str):
            in_file = open(self.__file, "rb")
        elif isinstance(self.__file, BytesIO):
            in_file = self.__file

        if in_file is None:
            return ''

        return extract_text(in_file)
