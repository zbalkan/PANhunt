import os
import tarfile
from gzip import GzipFile
from io import BytesIO
from lzma import LZMAFile
from tarfile import TarFile, TarInfo
from typing import IO, Optional
from zipfile import ZipFile

import panutils
from config import PANHuntConfiguration
from exceptions import PANHuntException
from job import Job


class Archive:
    path: str
    payload: Optional[bytes]

    def __init__(self, path: str, payload: Optional[bytes] = None) -> None:
        self.path = path
        self.payload = payload

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        raise NotImplementedError()


class ZipArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        children: list[Job] = []
        try:
            zip_ref: ZipFile
            if self.payload is not None:
                zip_ref = ZipFile(BytesIO(self.payload), 'r')
            else:
                zip_ref = ZipFile(self.path, 'r')

            for file_info in zip_ref.infolist():
                with zip_ref.open(file_info) as file:
                    file.seek(0)
                    payload: bytes = file.read()
                    job = Job(
                        basename=file_info.filename, dirname=self.path, payload=payload)
                    children.append(job)
            zip_ref.close()
        except Exception as ex:
            return [], PANHuntException(str(ex))

        return children, None



class TarArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        children: list[Job] = []

        try:
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
                    job = Job(
                        basename=file_info.path, dirname=self.path, payload=payload)

                    children.append(job)
            tar_ref.close()

        except Exception as ex:
            return [], PANHuntException(str(ex))

        return children, None


class GzipArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:

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

        size = 0
        reached_eof = False
        payload: bytes = b''
        while size < PANHuntConfiguration().size_limit:
            b = gz_file.read1()
            if b == b'':
                reached_eof = True
                break
            payload += gz_file.read1()
            size += len(payload)

        gz_file.close()

        if not reached_eof:
            return [], PANHuntException(
                f'File size limit ({PANHuntConfiguration().size_limit}) reached during decompressing. Skipping file.')
        else:
            job = Job(
                basename=compressed_filename, dirname=self.path, payload=payload)
            return [job], None


class XzArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:

        xz_file: LZMAFile

        if self.payload is not None:
            xz_file = LZMAFile(filename=BytesIO(self.payload), mode='r')
        else:
            xz_file = LZMAFile(filename=self.path, mode='r')

        compressed_filename: str = os.path.basename(
            self.path).replace('.xz', '')
        xz_file.seek(0)

        size = 0
        reached_eof = False
        payload: bytes = b''
        while size < PANHuntConfiguration().size_limit:
            b = xz_file.read1()
            if b == b'':
                reached_eof = True
                break
            payload += xz_file.read1()
            size += len(payload)

        xz_file.close()

        if not reached_eof:
            return [], PANHuntException(
                f'File size limit ({PANHuntConfiguration().size_limit}) reached during decompressing. Skipping file.')
        else:
            job = Job(
                basename=compressed_filename, dirname=self.path, payload=payload)
            xz_file.close()
            return [job], None
