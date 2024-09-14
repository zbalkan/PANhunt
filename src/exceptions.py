import logging


class PANHuntException(BaseException):
    def __init__(self, message: str) -> None:
        logging.error(message)
