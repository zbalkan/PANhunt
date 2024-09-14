import logging
import os
import re
import time

from config import PANHuntConfiguration
from directory import Directory
from dispatcher import Dispatcher
from finding import Finding
from job import Job, JobQueue


class Hunter:

    __dispatcher: Dispatcher
    count: int = 0

    def __init__(self) -> None:
        self.__dispatcher = Dispatcher()

    def hunt(self) -> None:
        """Enqueue all jobs into the job queue for processing by the dispatcher."""

        self.__dispatcher.start()

        logging.info(f"Search base: {PANHuntConfiguration().search_dir}")

        if PANHuntConfiguration().file_path is not None:
            # To silence the type checker
            p = str(PANHuntConfiguration().file_path)
            basename: str = os.path.basename(p)
            dir: str = os.path.dirname(p)
            if not self.__is_directory_excluded(dir):
                JobQueue().enqueue(Job(basename, file_dir=dir))
        else:
            root = Directory(path=PANHuntConfiguration().search_dir)
            for file in root.get_children():
                if not self.__is_directory_excluded(file.file_dir):
                    # Create a Job instance for each file instead of ScannableFile
                    job = Job(filename=file.filename,
                              file_dir=file.file_dir, payload=file.payload)
                    JobQueue().enqueue(job)
                    self.count += 1

        # Mark the queue as finished so the dispatcher knows no more jobs are coming
        JobQueue().mark_input_complete()

        while (not JobQueue().is_finished()):
            time.sleep(0.1)

        logging.info(f"Total number of jobs (files): {self.count}")

    def get_results(self) -> list[Finding]:
        return self.__dispatcher.results

    def __is_directory_excluded(self, file_dir: str) -> bool:
        for excluded_dir in PANHuntConfiguration().excluded_directories:
            escaped_file_dir = re.escape(file_dir)
            escaped_excluded_dir = re.escape(excluded_dir)
            if os.name == 'nt':
                if re.match(f"{escaped_excluded_dir}\\.*", escaped_file_dir):
                    return True
            else:
                if re.match(f"{escaped_excluded_dir}/.*", escaped_file_dir):
                    return True
        return False
