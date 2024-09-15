import os
import tarfile
from gzip import GzipFile
from io import BytesIO
from lzma import LZMAFile
from tarfile import TarFile, TarInfo
from typing import IO, Optional
from zipfile import ZipFile

import panutils
from job import Job


class Archive:
    path: str
    payload: Optional[bytes]

    def __init__(self, path: str, payload: Optional[bytes] = None) -> None:
        self.path = path
        self.payload = payload

    def get_children(self) -> list[Job]:
        raise NotImplementedError()


class ZipArchive(Archive):

    def get_children(self) -> list[Job]:
        children: list[Job] = []

        zip_ref: ZipFile
        if self.payload is not None:
            zip_ref = ZipFile(BytesIO(self.payload), 'r')
        else:
            zip_ref = ZipFile(self.path, 'r')

        for file_info in zip_ref.infolist():
            with zip_ref.open(file_info) as file:
                file.seek(0)
                payload: bytes = file.read()
                x = Job(
                    basename=file_info.filename, dirname=self.path, payload=payload)
                children.append(x)
        zip_ref.close()
        return children


class TarArchive(Archive):

    def get_children(self) -> list[Job]:
        children: list[Job] = []

        tar_ref: TarFile
        if self.payload is not None:
            tar_ref = tarfile.open(
                fileobj=BytesIO(self.payload), mode='r')
        else:
            tar_ref = tarfile.open(self.path, 'r')

        members: list[TarInfo] = tar_ref.getmembers()
        for file_info in [m for m in members if m.isfile()]:
            extracted: Optional[IO[bytes]] = tar_ref.extractfile(file_info)
            if extracted is not None:
                extracted.seek(0)
                payload: bytes = extracted.read()
                x = Job(
                    basename=file_info.path, dirname=self.path, payload=payload)

                children.append(x)
        tar_ref.close()

        return children


class GzipArchive(Archive):

    def get_children(self) -> list[Job]:

        gz_file: GzipFile
        if self.payload is not None:
            gz_file = GzipFile(
                fileobj=BytesIO(self.payload), mode='r')
            gz_file.name = self.path
        else:
            gz_file = GzipFile(filename=self.path, mode='r')

        compressed_filename: str = panutils.get_compressed_filename(
            gz_file)
        gz_file.seek(0)
        payload: bytes = gz_file.read1()
        x = Job(
            basename=compressed_filename, dirname=self.path, payload=payload)
        gz_file.close()
        return [x]


class XzArchive(Archive):

    def get_children(self) -> list[Job]:

        xz_file: LZMAFile

        if self.payload is not None:
            xz_file = LZMAFile(filename=BytesIO(self.payload), mode='r')
        else:
            xz_file = LZMAFile(filename=self.path, mode='r')

        compressed_filename: str = os.path.basename(
            self.path).replace('.xz', '')
        xz_file.seek(0)
        payload: bytes = xz_file.read1()
        x = Job(
            basename=compressed_filename, dirname=self.path, payload=payload)
        xz_file.close()
        return [x]
