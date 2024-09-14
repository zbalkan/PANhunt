import os

from job import Job


class Directory:

    path: str

    def __init__(self, path: str) -> None:
        self.path = path

    def get_children(self) -> list[Job]:
        jobs: list[Job] = []
        for root, dirs, files in os.walk(self.path):
            for file in files:
                # file = os.path.join(root, file)
                jobs.append(Job(
                    filename=file, file_dir=root))

        return jobs
