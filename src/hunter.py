import logging
import re
import time

from config import PANHuntConfiguration
from directory import Directory
from dispatcher import Dispatcher
from job import Job, JobQueue
from patterns import CardPatterns
from scannable import Scannable


class Hunter:

    __all_files: list[Job]
    __conf: PANHuntConfiguration
    __patterns: CardPatterns
    __dispatcher: Dispatcher

    def __init__(self, configuration: PANHuntConfiguration) -> None:
        self.__conf = configuration
        self.__all_files = []
        self.__patterns = CardPatterns()
        self.__dispatcher = Dispatcher(
            excluded_pans_list=self.__conf.excluded_pans, patterns=self.__patterns)

    def add_file(self, filename: str, dir: str) -> None:
        """Create a Job instead of a ScannableFile and add to the list."""
        job = Job(filename=filename, file_dir=dir)
        self.__all_files.append(job)

    def enumerate(self) -> int:
        """Recursively searches a directory for files and adds them as jobs."""

        file_list: list[Job] = []

        logging.info(f"Search base: {self.__conf.search_dir}")

        root = Directory(path=self.__conf.search_dir)
        for file in root.get_children():
            if not self.__is_directory_excluded(file.file_dir):
                # Create a Job instance for each file instead of ScannableFile
                job = Job(filename=file.filename,
                          file_dir=file.file_dir, value_bytes=file.value_bytes)
                file_list.append(job)

        self.__all_files += file_list
        logging.info(f"Total number of jobs (files): {len(self.__all_files)}")
        return len(self.__all_files)

    def hunt(self) -> None:
        """Enqueue all jobs into the job queue for processing by the dispatcher."""

        self.__dispatcher.start()

        for job in self.__all_files:
            JobQueue().enqueue(job)

        # Mark the queue as finished so the dispatcher knows no more jobs are coming
        JobQueue().mark_input_complete()

        while (not JobQueue().is_finished()):
            time.sleep(0.1)

    def get_results(self) -> list[Scannable]:
        return self.__dispatcher.results

    def __is_directory_excluded(self, file_dir: str) -> bool:
        for excluded_dir in self.__conf.excluded_directories:
            escaped_file_dir = re.escape(file_dir)
            escaped_excluded_dir = re.escape(excluded_dir)
            if re.match(f"{escaped_excluded_dir}/.*", escaped_file_dir):
                return True
        return False
