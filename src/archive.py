from gzip import GzipFile
from io import BytesIO
from lzma import LZMAFile
from tarfile import TarFile, open
from typing import Optional
from zipfile import ZipFile

import panutils
from job import Job


class Archive:
    path: str
    value_bytes: Optional[bytes]

    def __init__(self, path: str, value_bytes: Optional[bytes] = None) -> None:
        self.path = path
        self.value_bytes = value_bytes

    def get_children(self) -> list[Job]:
        raise NotImplementedError()


class ZipArchive(Archive):

    def get_children(self) -> list[Job]:
        children: list[Job] = []

        zip_ref: ZipFile
        if self.value_bytes is not None:
            zip_ref = ZipFile(BytesIO(self.value_bytes), 'r')
        else:
            zip_ref = ZipFile(self.path, 'r')

        for file_info in zip_ref.infolist():
            with zip_ref.open(file_info) as file:
                file.seek(0)
                file_data: bytes = file.read()
                x = Job(
                    filename=file_info.filename, file_dir=self.path, value_bytes=file_data)
                children.append(x)
        zip_ref.close()
        return children


class TarArchive(Archive):

    def get_children(self) -> list[Job]:
        children: list[Job] = []

        tar_ref: TarFile
        if self.value_bytes is not None:
            tar_ref = open(
                fileobj=BytesIO(self.value_bytes), mode='r')
        else:
            tar_ref = open(self.path, 'r')
        for file_info in [m for m in tar_ref.getmembers() if m.isfile()]:
            extracted = tar_ref.extractfile(file_info)
            if extracted is not None:
                extracted.seek(0)
                file_data: bytes = extracted.read()
                x = Job(
                    filename=file_info.path, file_dir=self.path, value_bytes=file_data)

                children.append(x)
        tar_ref.close()
        return children


class GzipArchive(Archive):

    def get_children(self) -> list[Job]:

        gz_file: GzipFile
        if self.value_bytes is not None:
            gz_file = GzipFile(
                fileobj=BytesIO(self.value_bytes), mode='r')
        else:
            gz_file = GzipFile(filename=self.path, mode='r')

        compressed_filename: str = panutils.get_compressed_filename(
            gz_file)
        gz_file.seek(0)
        file_data: bytes = gz_file.read1()
        x = Job(
            filename=compressed_filename, file_dir=self.path, value_bytes=file_data)
        gz_file.close()
        return [x]


class XzArchive(Archive):

    def get_children(self) -> list[Job]:

        xz_file: LZMAFile

        if self.value_bytes is not None:
            xz_file = LZMAFile(filename=BytesIO(self.value_bytes), mode='r')
        else:
            xz_file = LZMAFile(filename=self.path, mode='r')

        compressed_filename: str = self.path.replace('.xz', '')
        xz_file.seek(0)
        file_data: bytes = xz_file.read1()
        x = Job(
            filename=compressed_filename, file_dir=self.path, value_bytes=file_data)
        xz_file.close()
        return [x]
