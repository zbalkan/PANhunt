import os
import tarfile
from gzip import GzipFile
from io import BytesIO, IOBase
from lzma import LZMAFile
from tarfile import TarFile, TarInfo
from typing import IO, Optional, Union
from zipfile import ZipFile, ZipInfo

from . import panutils
from .exceptions import PANHuntException
from .job import Job
from .limitedio import LimitedReader, spool_limited
from .scancontext import ScanContext


class Archive:
    path: str
    payload: Optional[Union[bytes, IOBase]]
    size_limit: int
    context: Optional[ScanContext]

    def __init__(
            self,
            path: str,
            payload: Optional[Union[bytes, IOBase]] = None,
            size_limit: int = 1_073_741_824,
            context: Optional[ScanContext] = None,
            max_members: int = 10_000,
            compression_ratio_limit: int = 100,
            max_path_length: int = 4096,
            spool_threshold: int = 8 * 1024 * 1024) -> None:
        self.path = path
        self.payload = payload
        self.size_limit = size_limit
        self.context = context
        self.max_members = max_members
        self.compression_ratio_limit = compression_ratio_limit
        self.max_path_length = max_path_length
        self.spool_threshold = spool_threshold

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        raise NotImplementedError()

    def _limit_error(self, detail: str) -> PANHuntException:
        return PANHuntException(
            f'Archive expansion limit exceeded for "{self.path}": {detail} '
            f'(limit {panutils.size_friendly(size=self.size_limit)})'
        )

    def _validate_path_length(self, member_path: str) -> Optional[PANHuntException]:
        logical_path = f'{self.context.logical_path if self.context else self.path}!/{member_path}'
        if len(member_path) > self.max_path_length or len(logical_path) > self.max_path_length:
            return PANHuntException(
                f'Archive path length limit exceeded for "{logical_path}": '
                f'{max(len(member_path), len(logical_path))} over {self.max_path_length}'
            )
        return None

    def _child_context(self, basename: str, payload_size: int = 0) -> Optional[ScanContext]:
        return self.context.child(basename=basename, payload_size=payload_size) if self.context else None

    def _spool_child(self, stream: IO[bytes], basename: str) -> tuple[IO[bytes], int, Optional[ScanContext]]:
        payload, size = spool_limited(stream, self.size_limit, spool_threshold=self.spool_threshold)
        try:
            context = self._child_context(basename, size)
            return payload, size, context
        except Exception:
            payload.close()
            raise

    @staticmethod
    def _close_children(children: list[Job]) -> None:
        for child in children:
            if isinstance(child.payload, IOBase):
                child.payload.close()


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
        path_error = self._validate_path_length(file_info.filename)
        if path_error:
            return path_error
        if (file_info.compress_size > 0
                and file_info.file_size / file_info.compress_size > self.compression_ratio_limit):
            return self._limit_error(
                f'member "{file_info.filename}" compression ratio exceeds {self.compression_ratio_limit}:1'
            )
        return None

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        children: list[Job] = []
        total_size = 0
        try:
            if isinstance(self.payload, bytes):
                zip_source = BytesIO(self.payload)
            elif self.payload is not None:
                self.payload.seek(0)
                zip_source = self.payload
            else:
                zip_source = self.path
            with ZipFile(zip_source, 'r') as zip_ref:
                infos = zip_ref.infolist()
                if len(infos) > self.max_members:
                    return [], self._limit_error(f'ZIP member count exceeds {self.max_members}')

                for file_info in infos:
                    if file_info.is_dir():
                        continue
                    limit_error = self._validate_member(file_info, total_size)
                    if limit_error:
                        self._close_children(children)
                        return [], limit_error
                    with zip_ref.open(file_info) as file:
                        payload, payload_size, child_context = self._spool_child(file, file_info.filename)
                    total_size += payload_size
                    children.append(Job(
                        basename=file_info.filename,
                        dirname=self.path,
                        payload=payload,
                        context=child_context))
        except PANHuntException as ex:
            self._close_children(children)
            return [], ex
        except Exception as ex:
            self._close_children(children)
            return [], PANHuntException(f'{type(ex).__name__}: {ex}')

        return children, None


class TarArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:
        children: list[Job] = []
        total_size = 0

        try:
            if isinstance(self.payload, bytes):
                tar_ref: TarFile = tarfile.open(fileobj=BytesIO(self.payload), mode='r')
            elif self.payload is not None:
                self.payload.seek(0)
                tar_ref = tarfile.open(fileobj=self.payload, mode='r')
            else:
                tar_ref = tarfile.open(self.path, 'r')

            with tar_ref:
                members: list[TarInfo] = tar_ref.getmembers()
                if len(members) > self.max_members:
                    return [], self._limit_error(f'TAR member count exceeds {self.max_members}')

                for file_info in [m for m in members if m.isfile()]:
                    path_error = self._validate_path_length(file_info.path)
                    if path_error:
                        self._close_children(children)
                        return [], path_error
                    if file_info.size > self.size_limit:
                        self._close_children(children)
                        return [], self._limit_error(
                            f'member "{file_info.path}" declares {panutils.size_friendly(size=file_info.size)}'
                        )
                    if total_size + file_info.size > self.size_limit:
                        self._close_children(children)
                        return [], self._limit_error('total uncompressed TAR size exceeds limit')

                    extracted: Optional[IO[bytes]] = tar_ref.extractfile(file_info)
                    if extracted is not None:
                        payload, payload_size, child_context = self._spool_child(extracted, file_info.path)
                        total_size += payload_size
                        children.append(Job(
                            basename=file_info.path,
                            dirname=self.path,
                            payload=payload,
                            context=child_context))

        except PANHuntException as ex:
            self._close_children(children)
            return [], ex
        except Exception as ex:
            self._close_children(children)
            return [], PANHuntException(f'{type(ex).__name__}: {ex}')

        return children, None


class GzipArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:

        try:
            gz_file: GzipFile

            if isinstance(self.payload, bytes):
                gz_file = GzipFile(fileobj=BytesIO(self.payload), mode='r')
                gz_file.name = self.path
            elif self.payload is not None:
                self.payload.seek(0)
                gz_file = GzipFile(fileobj=self.payload, mode='r')
                gz_file.name = self.path
            else:
                gz_file = GzipFile(filename=self.path, mode='r')

            compressed_filename: str = panutils.get_compressed_filename(
                gz_file)
            gz_file.seek(0)

            path_error = self._validate_path_length(compressed_filename)
            if path_error:
                gz_file.close()
                return [], path_error
            child_context = self._child_context(compressed_filename)
            job = Job(
                basename=compressed_filename,
                dirname=self.path,
                payload=LimitedReader(gz_file, self.size_limit, self.path, child_context),
                context=child_context
            )
            return [job], None
        except Exception as ex:
            return [], PANHuntException(f'{type(ex).__name__}: {ex}')


class XzArchive(Archive):

    def get_children(self) -> tuple[list[Job], Optional[PANHuntException]]:

        try:
            xz_file: LZMAFile

            if isinstance(self.payload, bytes):
                xz_file = LZMAFile(filename=BytesIO(self.payload), mode='r')
            elif self.payload is not None:
                self.payload.seek(0)
                xz_file = LZMAFile(filename=self.payload, mode='r')
            else:
                xz_file = LZMAFile(filename=self.path, mode='r')

            compressed_filename: str = os.path.basename(
                self.path).replace('.xz', '')
            xz_file.seek(0)

            path_error = self._validate_path_length(compressed_filename)
            if path_error:
                xz_file.close()
                return [], path_error
            child_context = self._child_context(compressed_filename)
            job = Job(
                basename=compressed_filename,
                dirname=self.path,
                payload=LimitedReader(xz_file, self.size_limit, self.path, child_context),
                context=child_context
            )
            return [job], None
        except Exception as ex:
            return [], PANHuntException(f'{type(ex).__name__}: {ex}')
