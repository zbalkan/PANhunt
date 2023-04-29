import io
from typing import Optional

from pdfminer.high_level import extract_text


class Pdf:

    filename:str

    __binary_data: Optional[bytes] = None

    def __init__(self, filename:str = '', value_bytes:Optional[bytes] = None) -> None:
        self.filename=filename
        if value_bytes:
            self.__binary_data = value_bytes

    def get_text(self) ->str:
        if self.__binary_data:
            byte_stream = io.BytesIO(self.__binary_data)
            return extract_text(byte_stream)

        return extract_text(pdf_file=self.filename)
