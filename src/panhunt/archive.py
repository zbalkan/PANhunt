import os
import tarfile
from gzip import GzipFile
from io import BytesIO
from lzma import LZMAFile
from tarfile import TarFile, TarInfo
from typing import IO, Optional
from zipfile import ZipFile, ZipInfo

from . import panutils
from .exceptions import PANHuntException
from .job import Job
from .limitedio import LimitedReader, read_limited
from .scancontext import ScanContext


class Archive:
    path: str
    payload: Optional[bytes]
    size_limit: int
    context: Optional[ScanContext]

    def __init__(
            self,
            path: str,
            payload: Optional[bytes] = None,
            size_limit: int = 1_073_741_824,
            context: Optional[ScanContext] = None) -> None:
        self.path = path
        self.payload = payload
        self.size_limit = size_limit
        self.context = context

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        raise NotImplementedError()

    def _limit_error(self, detail: str) -> PANHuntException:
        return PANHuntException(
            f'Archive expansion limit exceeded for "{self.path}": {detail} '
            f'(limit {panutils.size_friendly(size=self.size_limit)})'
        )

    def _child_context(self, basename: str, payload_size: int = 0) -> Optional[ScanContext]:
        return self.context.child(basename=basename, payload_size=payload_size) if self.context else None


class ZipArchive(Archive):

    def _validate_member(self, file_info: ZipInfo, total_size: int) -> Optional[PANHuntException]:
        if file_info.is_dir():
            return None
        if file_info.file_size > self.size_limit:
            return self._limit_error(
                f'member "{file_info.filename}" declares {panutils.size_friendly(size=file_info.file_size)}'
            )
        if total_size + file_info.file_size > self.size_limit:
            return self._limit_error('total uncompressed ZIP size exceeds limit')
        if file_info.compress_size > 0 and file_info.file_size / file_info.compress_size > 100:
            return self._limit_error(f'member "{file_info.filename}" compression ratio exceeds 100:1')
        return None

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        children: list[Job] = []
        total_size = 0
        try:
            zip_source = BytesIO(self.payload) if self.payload is not None else self.path
            with ZipFile(zip_source, 'r') as zip_ref:
                infos = zip_ref.infolist()
                if len(infos) > 10_000:
                    return [], self._limit_error('ZIP member count exceeds 10000')

                for file_info in infos:
                    if file_info.is_dir():
                        continue
                    limit_error = self._validate_member(file_info, total_size)
                    if limit_error:
                        return [], limit_error
                    with zip_ref.open(file_info) as file:
                        payload = read_limited(file, self.size_limit)
                    total_size += len(payload)
                    children.append(Job(
                        basename=file_info.filename,
                        dirname=self.path,
                        payload=payload,
                        context=self._child_context(file_info.filename, len(payload))))
        except PANHuntException as ex:
            return [], ex
        except Exception as ex:
            return [], PANHuntException(f'{type(ex).__name__}: {ex}')

        return children, None


class TarArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        children: list[Job] = []
        total_size = 0

        try:
            if self.payload is not None:
                tar_ref: TarFile = tarfile.open(fileobj=BytesIO(self.payload), mode='r')
            else:
                tar_ref = tarfile.open(self.path, 'r')

            with tar_ref:
                members: list[TarInfo] = tar_ref.getmembers()
                if len(members) > 10_000:
                    return [], self._limit_error('TAR member count exceeds 10000')

                for file_info in [m for m in members if m.isfile()]:
                    if file_info.size > self.size_limit:
                        return [], self._limit_error(
                            f'member "{file_info.path}" declares {panutils.size_friendly(size=file_info.size)}'
                        )
                    if total_size + file_info.size > self.size_limit:
                        return [], self._limit_error('total uncompressed TAR size exceeds limit')

                    extracted: Optional[IO[bytes]] = tar_ref.extractfile(file_info)
                    if extracted is not None:
                        payload = read_limited(extracted, self.size_limit)
                        total_size += len(payload)
                        children.append(Job(
                            basename=file_info.path,
                            dirname=self.path,
                            payload=payload,
                            context=self._child_context(file_info.path, len(payload))))

        except PANHuntException as ex:
            return [], ex
        except Exception as ex:
            return [], PANHuntException(f'{type(ex).__name__}: {ex}')

        return children, None


class GzipArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:

        try:
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

            job = Job(
                basename=compressed_filename,
                dirname=self.path,
                payload=LimitedReader(gz_file, self.size_limit, self.path),
                context=self._child_context(compressed_filename)
            )
            return [job], None
        except Exception as ex:
            return [], PANHuntException(f'{type(ex).__name__}: {ex}')


class XzArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:

        try:
            xz_file: LZMAFile

            if self.payload is not None:
                xz_file = LZMAFile(filename=BytesIO(self.payload), mode='r')
            else:
                xz_file = LZMAFile(filename=self.path, mode='r')

            compressed_filename: str = os.path.basename(
                self.path).replace('.xz', '')
            xz_file.seek(0)

            job = Job(
                basename=compressed_filename,
                dirname=self.path,
                payload=LimitedReader(xz_file, self.size_limit, self.path),
                context=self._child_context(compressed_filename)
            )
            return [job], None
        except Exception as ex:
            return [], PANHuntException(f'{type(ex).__name__}: {ex}')
