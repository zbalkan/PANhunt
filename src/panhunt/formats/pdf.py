from io import BytesIO
from typing import Optional, Union

from pdfminer.high_level import extract_text

from ..exceptions import PANHuntException
from ..parser_isolation import SubprocessParserRunner


def _extract_pdf_text(pdfFile: Union[str, bytes], max_pages: int, max_text_bytes: int) -> str:
    text: str
    if isinstance(pdfFile, bytes) or isinstance(pdfFile, bytearray):
        text = extract_text(BytesIO(pdfFile), maxpages=max_pages)
    else:
        text = extract_text(pdfFile, maxpages=max_pages)  # type: ignore

    if max_text_bytes >= 0 and len(text.encode('utf-8', errors='ignore')) > max_text_bytes:
        raise PANHuntException(f'PDF extracted text exceeds configured limit of {max_text_bytes} bytes')
    return text


class Pdf:

    __file: Union[str, BytesIO]
    __runner: Optional[SubprocessParserRunner]
    __max_pages: int
    __max_text_bytes: int

    def __init__(
            self,
            file: Union[str, BytesIO],
            runner: Optional[SubprocessParserRunner] = None,
            max_pages: int = 100,
            max_text_bytes: int = 10 * 1024 * 1024) -> None:
        self.__file = file
        self.__runner = runner
        self.__max_pages = max_pages
        self.__max_text_bytes = max_text_bytes

    def get_text(self) -> str:
        parser_input: Union[str, bytes]
        if isinstance(self.__file, str):
            parser_input = self.__file
        else:
            self.__file.seek(0)
            parser_input = bytes(self.__file.read())

        if self.__runner is not None:
            return self.__runner.run(_extract_pdf_text, parser_input, self.__max_pages, self.__max_text_bytes)
        return _extract_pdf_text(parser_input, self.__max_pages, self.__max_text_bytes)
