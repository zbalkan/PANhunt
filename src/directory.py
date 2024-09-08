import os

from container import Container
from scannable import ScannableFile


class Directory(Container):
    def get_children(self) -> list[ScannableFile]:
        searchables: list[ScannableFile] = []
        for root, dirs, files in os.walk(self.path):
            for file in files:
                searchables.append(ScannableFile(
                    filename=file, file_dir=root))

        return searchables
