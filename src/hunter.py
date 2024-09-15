import logging
import os
import re
import time

from config import PANHuntConfiguration
from dispatcher import Dispatcher
from finding import Finding
from job import Job, JobQueue


class Hunter:

    __dispatcher: Dispatcher
    count: int = 0

    def __init__(self) -> None:
        self.__dispatcher = Dispatcher()

    def hunt(self) -> tuple[list[Finding], list[Finding]]:
        """Enqueue all jobs into the job queue for processing by the dispatcher."""

        self.__dispatcher.start()

        logging.info(f"Search base: {PANHuntConfiguration().search_dir}")

        if PANHuntConfiguration().file_path is not None:
            # To silence the type checker
            p = str(PANHuntConfiguration().file_path)
            basename: str = os.path.basename(p)
            dir: str = os.path.dirname(p)
            if not self.__is_directory_excluded(dir):
                JobQueue().enqueue(Job(basename, dirname=dir))
        else:
            for root, _, files in os.walk(PANHuntConfiguration().search_dir):
                for file in files:
                    job = Job(
                        basename=file, dirname=root, payload=None)
                    JobQueue().enqueue(job)
                    self.count += 1

        # Mark the queue as finished so the dispatcher knows no more jobs are coming
        JobQueue().mark_input_complete()

        while (not JobQueue().is_finished()):
            time.sleep(0.1)

        logging.info(f"Total number of jobs (files): {self.count}")
        return self.__dispatcher.findings, self.__dispatcher.failures

    def __is_directory_excluded(self, dirname: str) -> bool:
        for excluded_dir in PANHuntConfiguration().excluded_directories:
            escaped_dirname = re.escape(dirname)
            escaped_excluded_dir = re.escape(excluded_dir)
            if os.name == 'nt':
                if re.match(f"{escaped_excluded_dir}\\.*", escaped_dirname):
                    return True
            else:
                if re.match(f"{escaped_excluded_dir}/.*", escaped_dirname):
                    return True
        return False
