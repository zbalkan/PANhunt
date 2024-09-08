from scannable import ScannableFile


class Container:
    def __init__(self, path: str) -> None:
        self.path = path

    def get_children(self) -> list[ScannableFile]:
        raise NotImplementedError()
