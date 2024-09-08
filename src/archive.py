import gzip
import lzma
import tarfile
import zipfile

import panutils
from container import Container
from scannable import ScannableFile


class Archive(Container):
    ...


class ZipArchive(Archive):

    def get_children(self) -> list[ScannableFile]:
        children: list[ScannableFile] = []
        with zipfile.ZipFile(self.path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                with zip_ref.open(file_info) as file:
                    file_data = file.read()
                    sf = ScannableFile(
                        filename=file_info.filename, file_dir=self.path, value_bytes=file_data)
                    children.append(sf)
        return children


class TarArchive(Archive):

    def get_children(self) -> list[ScannableFile]:
        children: list[ScannableFile] = []

        with tarfile.open(self.path, 'r') as tar_ref:
            for file_info in [m for m in tar_ref.getmembers() if m.isfile()]:
                extracted = tar_ref.extractfile(file_info)
                if extracted is not None:
                    file_data: bytes = extracted.read()
                    sf = ScannableFile(
                        filename=file_info.path, file_dir=self.path, value_bytes=file_data)

                    children.append(sf)
        return children


class GzipArchive(Archive):

    def get_children(self) -> list[ScannableFile]:
        gz_file = gzip.GzipFile(filename=self.path)
        compressed_filename: str = panutils.get_compressed_filename(
            gz_file)
        file_data = gz_file.read1()
        sf = ScannableFile(
            filename=compressed_filename, file_dir=self.path, value_bytes=file_data)
        gz_file.close()
        return [sf]


class XzArchive(Archive):

    def get_children(self) -> list[ScannableFile]:
        xz_file = lzma.LZMAFile(filename=self.path)
        compressed_filename = self.path.replace('.xz', '')
        file_data = xz_file.read1()
        sf = ScannableFile(
            filename=compressed_filename, file_dir=self.path, value_bytes=file_data)
        xz_file.close()
        return [sf]
