import io
import os
from abc import ABC, abstractmethod
from typing import Optional

from formats.eml import Eml
from job import Job, JobQueue
from formats.mbox import Mbox
from formats.msmsg import MSMSG
from PAN import PAN
from PanFinder import PanFinder
from formats.pdf import Pdf
from formats.pst import PST
from formats.pst import Attachment as pstAttachment

''' If file size is 30MB or bigger, read line by line for better memory management '''
BLOCK_SIZE: int = 31_457_280  # 30MB


class ScannerBase(ABC):

    @abstractmethod
    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        raise NotImplementedError()


class PlainTextFileScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:

        matches: list[PAN] = []

        text: str
        if job.payload:

            before = len(job.payload)
            text = job.payload.decode(
                encoding=encoding, errors='backslashreplace')
            after = len(text)
            finder = PanFinder()
            matches.extend(finder.find(text))
        else:
            s: os.stat_result = os.stat(path=job.abspath)
            file_size: int = s.st_size

            if file_size == 0:
                return []

            if 0 < file_size < BLOCK_SIZE:
                with open(file=job.abspath, mode='r', encoding=encoding, errors='backslashreplace') as f:
                    text = f.read()

                finder = PanFinder()
                matches.extend(finder.find(text))
            else:
                with open(file=job.abspath, mode='r', encoding=encoding, errors='backslashreplace') as f:
                    for line in f:
                        finder = PanFinder()
                        matches.extend(finder.find(line))
        return matches


class MsgScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:

        msg: MSMSG
        if job.payload:
            msg = MSMSG(msg_file_path=job.payload)
        else:
            msg = MSMSG(msg_file_path=job.abspath)

        matches: list[PAN] = []

        if msg.validMSG:
            if msg.Body:
                text_scanner = PanFinder()
                body_matches: list[PAN] = text_scanner.find(msg.Body)
                if len(body_matches) > 0:
                    matches.extend(body_matches)
            if msg.attachments:
                for _, att in enumerate(iterable=msg.attachments):
                    job = Job(
                        basename=att.Filename,
                        dirname=job.basename,
                        payload=att.BinaryData
                    )
                    JobQueue().enqueue(job)

        return matches


class EmlScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        eml: Eml

        if job.payload:
            eml = Eml(path=job.abspath,
                      payload=job.payload)
        else:
            eml = Eml(path=job.abspath)

        matches: list[PAN] = []

        if eml.body:
            text_scanner = PanFinder()
            body_matches: list[PAN] = text_scanner.find(eml.body)
            if len(body_matches) > 0:
                matches.extend(body_matches)
        if eml.attachments:
            for _, att in enumerate(iterable=eml.attachments):
                # Create a job for the attachment and add it to the JobQueue
                job = Job(
                    basename=att.Filename,  # Use the attachment filename
                    dirname=job.basename,  # The parent filename
                    payload=att.BinaryData  # Pass the binary content directly
                )
                JobQueue().enqueue(job)

        return matches


class MboxScanner(ScannerBase):

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:
        mbox: Mbox

        if job.payload:
            mbox = Mbox(path=job.basename,
                        payload=job.payload)
        else:
            mbox = Mbox(path=job.abspath)

        matches: list[PAN] = []

        for mail in mbox.mails:
            if mail.body:
                text_scanner = PanFinder()
                body_matches: list[PAN] = text_scanner.find(mail.body)
                if len(body_matches) > 0:
                    matches.extend(body_matches)
            if mail.attachments:
                for _, att in enumerate(iterable=mail.attachments):
                    # Create a job for the attachment and add it to the JobQueue
                    job = Job(
                        basename=att.Filename,  # Use the attachment filename
                        dirname=job.basename,  # The parent filename
                        payload=att.BinaryData  # Pass the binary content directly
                    )
                    JobQueue().enqueue(job)

        return matches


class PstScanner(ScannerBase):
    pst: Optional[PST] = None

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:

        if self.pst is None:
            self.pst = PST(pst_file=job.abspath)

        matches: list[PAN] = []

        if self.pst.header.validPST:
            for folder in self.pst.folder_generator():
                for message in self.pst.message_generator(folder=folder):
                    if message.Subject:
                        message_path: str = os.path.join(
                            folder.path, message.Subject)
                    else:
                        message_path = os.path.join(
                            folder.path, '[NoSubject]')

                    if message.Body:
                        text_scanner = PanFinder(
                        )
                        body_matches: list[PAN] = text_scanner.find(
                            message.Body)
                        if len(body_matches) > 0:
                            matches.extend(body_matches)

                    if message.HasAttachments:
                        for _, subattachment in enumerate(message.subattachments):
                            if subattachment.Filename:
                                att: Optional[pstAttachment] = message.get_attachment(
                                    subattachment=subattachment)
                                if att:
                                    # Create a job for the attachment and add it to the JobQueue
                                    job = Job(
                                        basename=att.Filename,  # Use the attachment filename
                                        dirname=job.basename,  # The parent filename
                                        payload=att.BinaryData  # Pass the binary content directly
                                    )
                                    JobQueue().enqueue(job)
            self.pst.close()

        return matches


class PdfScanner(ScannerBase):
    pdf: Pdf

    def scan(self, job: Job, encoding: str = 'utf8') -> list[PAN]:

        if job.payload:
            self.pdf = Pdf(file=io.BytesIO(initial_bytes=job.payload))
        else:
            self.pdf = Pdf(file=job.abspath)

        finder = PanFinder()
        return finder.find(self.pdf.get_text())
