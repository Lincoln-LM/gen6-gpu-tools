"""Widget for the soaring fidget tab in the main window"""

from math import ceil, floor, log2
from time import perf_counter
from qtpy.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QListWidget,
)
from qtpy.QtCore import Qt

from .range_widget import RangeWidget
from .opencl_selector import OpenCLSelector
from .eta_progress_bar import ETAProgressBar
from ..shaders.soaring_fidget import SearchSoaringFidgetThread


class SoaringFidgetTab(QWidget):
    """QWidget for the soaring fidget tab in the main window"""

    def __init__(self, opencl_selector: OpenCLSelector) -> None:
        super().__init__()
        self.opencl_selector = opencl_selector
        self.setup_widgets()
        self.fidget_gaps = []
        self.last_time = 0
        self.data_score = 0
        self.target_score = -1
        self.tracking = False
        self.search_thread = None

    def fidget_button_work(self) -> None:
        """Starts fidget tracker if not already started, else adds a fidget"""
        if not self.tracking:
            self.fidget_gaps = []
            self.data_score = 0
            self.target_score = ceil(32 + log2(len(self.advance_range.get_range())) + 4)
            self.search_button.setEnabled(False)
            self.advance_range.setEnabled(False)
            self.fidget_gaps_widget.clear()
            self.info_progress_bar.setValue(0)
            self.info_progress_bar.setMaximum(self.target_score)

            self.tracking = True
            self.fidget_button.setText("Record Fidget")
            self.last_time = perf_counter()
            self.fidget_gaps.append(-1)
        else:
            new_time = perf_counter()
            gap = new_time - self.last_time
            effective_gap = round(gap / 3) - 2
            self.last_time = new_time
            self.fidget_gaps.append(effective_gap)
            self.data_score += log2(3 ** (effective_gap + 1)) - effective_gap
            self.info_progress_bar.setValue(floor(self.data_score))
            self.fidget_gaps_widget.addItem(f"{gap:.2f}s | {effective_gap+1}adv")
        # overdeterminate by at least 4 bits (arbitrary)
        if self.data_score >= self.target_score:
            self.search_button.setEnabled(True)
            self.advance_range.setEnabled(True)
            self.info_progress_bar.setValue(self.target_score)
            self.tracking = False
            self.fidget_button.setText("Start Fidgets")

    def display_result(self, result) -> None:
        """Display the result of the search to a label"""
        self.result_label.setText(f"Result: {result[0]:08X}")

    def search_button_work(self) -> None:
        """Starts search thread"""
        platform, device = (
            self.opencl_selector.get_platform(),
            self.opencl_selector.get_device(),
        )
        assert platform is not None and device is not None

        self.search_thread = SearchSoaringFidgetThread(
            platform, device, self.fidget_gaps[1:], self.advance_range.get_range()
        )
        self.search_thread.results.connect(self.display_result)
        self.search_thread.init_progress_bar.connect(
            self.search_progress_bar.setMaximum
        )
        self.search_thread.progress.connect(self.search_progress_bar.setValue)
        self.search_thread.start()

    def setup_widgets(self) -> None:
        """Construct soaring fidget widgets"""
        self.main_layout = QVBoxLayout(self)
        self.advance_range = RangeWidget(0, 200, "Advance Range")
        self.advance_range.min_entry.setValue(40)
        self.advance_range.max_entry.setValue(100)
        self.fidget_gaps_widget = QListWidget()
        self.info_progress_bar = QProgressBar()
        self.fidget_button = QPushButton("Start Fidgets")
        self.fidget_button.clicked.connect(self.fidget_button_work)
        self.search_button = QPushButton("Find Seed")
        self.search_button.clicked.connect(self.search_button_work)
        self.search_button.setEnabled(False)
        self.search_progress_bar = ETAProgressBar()
        self.result_label = QLabel("Result:")
        self.result_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.main_layout.addWidget(self.advance_range)
        self.main_layout.addWidget(self.fidget_gaps_widget)
        self.main_layout.addWidget(self.info_progress_bar)
        self.main_layout.addWidget(self.fidget_button)
        self.main_layout.addWidget(self.search_button)
        self.main_layout.addWidget(self.search_progress_bar)
        self.main_layout.addWidget(self.result_label)
