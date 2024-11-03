"""Widget for the pokemon blink tab in the main window"""

from math import ceil, floor, log2
from time import perf_counter
from qtpy.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QListWidget,
    QSpinBox,
    QComboBox,
    QLineEdit,
)
from qtpy.QtGui import QRegularExpressionValidator
from qtpy.QtCore import Qt
from qtpy import QtCore
from numba_pokemon_prngs.mersenne_twister import TinyMersenneTwister

from .range_widget import RangeWidget
from .opencl_selector import OpenCLSelector
from .eta_progress_bar import ETAProgressBar
from ..shaders.pokemon_blink import PokemonBlinkFidgetThread


class PokemonBlinkTab(QWidget):
    """QWidget for the pokemon blink tab in the main window"""

    def __init__(self, opencl_selector: OpenCLSelector) -> None:
        super().__init__()
        self.opencl_selector = opencl_selector
        self.setup_widgets()
        self.blinks = []
        self.last_time = 0
        self.data_score = 0
        self.target_score = -1
        self.tracking = False
        self.search_thread = None

    def blink_button_work(self) -> None:
        """Starts blink tracker if not already started, else adds a blink"""
        if not self.tracking:
            self.blinks = []
            self.data_score = 0
            if self.search_type.currentIndex() == 0:
                self.target_score = ceil(
                    32 + log2(len(self.advance_range.get_range())) + 4
                )
            elif self.search_type.currentIndex() == 1:
                self.target_score = ceil(
                    26 + log2(len(self.advance_range.get_range())) + 4
                )
            elif self.search_type.currentIndex() == 2:
                self.target_score = ceil(log2(len(self.advance_range.get_range())) + 4)
            self.search_button.setEnabled(False)
            self.advance_range.setEnabled(False)
            self.blink_widget.clear()
            self.info_progress_bar.setValue(0)
            self.info_progress_bar.setMaximum(self.target_score)

            self.tracking = True
            self.blink_button.setText("Record Blink")
            self.last_time = perf_counter()
            self.blinks.append(-1)
        else:
            new_time = perf_counter()
            gap = new_time - self.last_time
            effective_gap = round(gap * 59.8261) - 250
            self.last_time = new_time
            self.blinks.append(effective_gap)
            self.data_score += log2(240 / (self.leeway_spinbox.value() * 2))
            self.info_progress_bar.setValue(floor(self.data_score))
            self.blink_widget.addItem(f"{gap:.2f}s | {effective_gap+250} frames")
        # overdeterminate by at least 4 bits (arbitrary)
        if self.data_score >= self.target_score:
            self.search_button.setEnabled(True)
            self.advance_range.setEnabled(True)
            self.info_progress_bar.setValue(self.target_score)
            self.tracking = False
            self.blink_button.setText("Start Blinks")

    def display_result(self, result) -> None:
        """Display the result of the search to a label"""
        assert len(result[0]) == 1, f"Expected 1 result, got {result[0]}"
        if self.search_type.currentIndex() == 2:
            self.result_label.setText(
                f"Starting Advance: {result[0][0]}\nResult Advance: {result[0][0] + len(self.blinks)-1+1}"
            )
        else:
            initial_state = TinyMersenneTwister(result[0][0]).state
            self.result_label.setText(
                f"Initial Seed: {result[0][0]:08X}\n"
                f"Initial State: {initial_state[3]:08X} {initial_state[2]:08X} {initial_state[1]:08X} {initial_state[0]:08X}\n"
                + f"Starting Advance: {result[1]}\n"
                + f"Result Advance: {result[1] + len(self.blinks)-1+1}"
            )

    def search_button_work(self) -> None:
        """Starts search thread"""
        platform, device = (
            self.opencl_selector.get_platform(),
            self.opencl_selector.get_device(),
        )
        assert platform is not None and device is not None

        base_seed = (
            int(seed_str, 16) if (seed_str := self.base_seed_input.text()) else 0
        )
        self.search_thread = PokemonBlinkFidgetThread(
            platform,
            device,
            self.blinks[1:],
            self.leeway_spinbox.value(),
            self.advance_range.get_range(),
            0 if self.search_type.currentIndex() == 0 else base_seed,
            0x100 if self.search_type.currentIndex() == 0 else 0x4,
            self.search_type.currentIndex() == 2,
        )
        self.search_thread.results.connect(self.display_result)
        self.search_thread.init_progress_bar.connect(
            self.search_progress_bar.setMaximum
        )
        self.search_thread.progress.connect(self.search_progress_bar.setValue)
        self.search_thread.start()

    def on_search_type_changed(self, index: int) -> None:
        """Enable/disable widgets based on search type"""
        self.base_seed_input_holder.setVisible(index != 0)
        self.base_seed_label.setText("Base Seed:" if index != 2 else "Seed:")
        self.search_button.setText("Find Seed" if index != 2 else "Find Advance")

    def setup_widgets(self) -> None:
        """Construct pokemon blink widgets"""
        self.main_layout = QVBoxLayout(self)
        self.search_type_widget = QWidget()
        self.search_type_layout = QHBoxLayout(self.search_type_widget)
        self.search_type = QComboBox()
        self.search_type.addItems(["Full Search", "Partial Search", "Reidentification"])
        self.search_type.currentIndexChanged.connect(self.on_search_type_changed)
        self.search_type_layout.addWidget(QLabel("Search Type:"))
        self.search_type_layout.addWidget(self.search_type)
        self.advance_range = RangeWidget(0, 200, "Advance Range")
        self.advance_range.min_entry.setValue(0)
        self.advance_range.max_entry.setValue(100)
        self.leeway_widget = QWidget()
        self.leeway_layout = QHBoxLayout(self.leeway_widget)
        self.leeway_spinbox = QSpinBox()
        self.leeway_spinbox.setValue(10)
        self.leeway_layout.addWidget(QLabel("±"))
        self.leeway_layout.addWidget(self.leeway_spinbox)

        self.base_seed_input_holder = QWidget()
        self.base_seed_input_layout = QHBoxLayout(self.base_seed_input_holder)
        self.base_seed_input = QLineEdit()
        self.base_seed_input.setValidator(
            QRegularExpressionValidator(QtCore.QRegularExpression("[0-9a-fA-F]{0,8}"))
        )
        self.base_seed_label = QLabel("Base Seed:")
        self.base_seed_input_layout.addWidget(self.base_seed_label)
        self.base_seed_input_layout.addWidget(self.base_seed_input)
        self.base_seed_input_holder.setVisible(False)

        self.blink_widget = QListWidget()
        self.info_progress_bar = QProgressBar()
        self.blink_button = QPushButton("Start Blinks")
        self.blink_button.clicked.connect(self.blink_button_work)
        self.search_button = QPushButton("Find Seed")
        self.search_button.clicked.connect(self.search_button_work)
        self.search_button.setEnabled(False)
        self.search_progress_bar = ETAProgressBar()
        self.result_label = QLabel("")
        self.result_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.main_layout.addWidget(self.search_type_widget)
        self.main_layout.addWidget(self.advance_range)
        self.main_layout.addWidget(self.leeway_widget)
        self.main_layout.addWidget(self.base_seed_input_holder)
        self.main_layout.addWidget(self.blink_widget)
        self.main_layout.addWidget(self.info_progress_bar)
        self.main_layout.addWidget(self.blink_button)
        self.main_layout.addWidget(self.search_button)
        self.main_layout.addWidget(self.search_progress_bar)
        self.main_layout.addWidget(self.result_label)
