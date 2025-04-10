"""Progress bar with a time estimation"""

import time
from qtpy.QtWidgets import QProgressBar


class ETAProgressBar(QProgressBar):
    """Progress bar with a time estimation"""

    def __init__(self, parent=None) -> None:
        self.start_time: float = None
        super().__init__(parent)

    def setValue(self, value: int) -> None:
        QProgressBar.setValue(self, value)
        if value == 0:
            value = 1
        if self.start_time is None:
            self.start_time = time.time()
        elapsed_time = time.time() - self.start_time
        eta = (self.maximum() - value) * elapsed_time / value
        eta_minutes, eta_seconds = divmod(eta, 60)
        eta_hours, eta_minutes = divmod(eta_minutes, 60)
        eta_str = (
            (f"{eta_hours:02.00f}:" if eta_hours > 0 else "")
            + (f"{eta_minutes:02.00f}:" if eta_minutes > 0 else "")
            + f"{eta_seconds:05.02f}"
            + ("s" if eta_hours == 0 and eta_minutes == 0 else "")
        )
        self.setFormat(f"{value/self.maximum()*100:.00f}% Estimated time: {eta_str}")

    def setMaximum(self, maximum: int) -> None:
        QProgressBar.setMaximum(self, maximum)
        self.start_time = None
