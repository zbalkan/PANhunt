import progressbar

import panutils


class DocProgressbar:
    """ This progress bar is used for document and non-pst file search.

        We do not care about single files due to high number.
    """

    pbar: progressbar.ProgressBar
    hunt_type: str

    def __init__(self, hunt_type: str) -> None:
        self.hunt_type = hunt_type
        self.__create__()

    def __enter__(self) -> 'DocProgressbar':
        self.__create__()
        return self

    def __create__(self) -> None:
        pbar_widgets: list = ['%s Hunt: ' % self.hunt_type, progressbar.Percentage(), ' ', progressbar.Bar(
            marker=progressbar.RotatingMarker()), ' ', progressbar.ETA(), progressbar.FormatLabel(' %ss:0' % self.hunt_type)]
        self.pbar = progressbar.ProgressBar(widgets=pbar_widgets).start()

    def update(self, items_found: int, items_total: int, items_completed: int) -> None:
        self.pbar.widgets[6] = progressbar.FormatLabel(
            ' %ss:%s' % (self.hunt_type, items_found))
        self.pbar.update(items_completed * 100.0 / items_total)

    def finish(self) -> None:
        self.pbar.finish()

    def __del__(self) -> None:
        self.finish()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.finish()


class PstProgressbar:
    """ This progress bar is used for PST file search as scanning big PST files can be time consuming and number of them are low.

        User might need feedback during a long-running task.
    """

    pbar: progressbar.ProgressBar
    filename: str
    hunt_type: str

    def __init__(self, hunt_type: str, filename: str) -> None:
        self.hunt_type = hunt_type
        self.filename = filename
        self.__create__()

    def __enter__(self) -> 'PstProgressbar':
        self.__create__()
        return self

    def __create__(self) -> None:
        pbar_widgets: list = ['%s Hunt %s: ' % (self.hunt_type, panutils.unicode_to_ascii(self.filename)), progressbar.Percentage(), ' ', progressbar.Bar(
            marker=progressbar.RotatingMarker()), ' ', progressbar.ETA(), progressbar.FormatLabel(' %ss:0' % self.hunt_type)]
        self.pbar = progressbar.ProgressBar(
            widgets=pbar_widgets).start()

    def update(self, items_found: int, items_total: int, items_completed: int) -> None:
        self.pbar.widgets[6] = progressbar.FormatLabel(
            ' %ss:%s' % (self.hunt_type, items_found))
        self.pbar.update(items_completed * 100.0 / items_total)

    def finish(self) -> None:
        self.pbar.finish()

    def __del__(self) -> None:
        self.finish()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.finish()
