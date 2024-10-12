"""Widget for the iv search tab in the main window"""

from qtpy.QtWidgets import (
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QCheckBox,
    QLabel,
    QLineEdit,
    QDialog,
)
from qtpy.QtGui import QRegularExpressionValidator
from qtpy import QtCore

from .range_widget import RangeWidget
from .opencl_selector import OpenCLSelector
from .eta_progress_bar import ETAProgressBar
from .iv_calc_window import IVCalculatorWindow
from ..shaders.iv_search import SearchIVThread


class IVSearchTab(QWidget):
    """QWidget for the iv search tab in the main window"""

    def __init__(self, opencl_selector: OpenCLSelector) -> None:
        super().__init__()
        self.opencl_selector = opencl_selector
        self.setup_widgets()
        self.search_thread = None

    def display_result(self, result) -> None:
        """Display the result of the search to a list"""
        self.result_list.addItem(f"{result:08X}")

    def search_button_work(self) -> None:
        """Starts search thread"""
        platform, device = (
            self.opencl_selector.get_platform(),
            self.opencl_selector.get_device(),
        )
        assert platform is not None and device is not None
        full_search = self.full_search.isChecked()
        base_seed = (
            int(seed_str, 16) if (seed_str := self.base_seed_input.text()) else 0
        )
        if self.search_thread is not None:
            self.search_button.setText("Start Search")

            self.search_thread.requestInterruption()
            self.search_thread.wait()
            self.search_thread = None
        else:
            self.result_list.clear()
            self.search_button.setText("Stop Search")

            self.search_thread = SearchIVThread(
                platform,
                device,
                [widget.value() for widget in self.iv_widgets_1],
                (
                    [widget.value() for widget in self.iv_widgets_2]
                    if full_search
                    else None
                ),
                (
                    [widget.value() for widget in self.iv_max_widgets_1]
                    if not full_search
                    else None
                ),
                self.advance_range_1.get_range(),
                self.advance_range_2.get_range() if full_search else None,
                0 if full_search else base_seed,
                0x100 if full_search else 0x4,
            )
            self.search_thread.results.connect(self.display_result)
            self.search_thread.init_progress_bar.connect(
                self.search_progress_bar.setMaximum
            )
            self.search_thread.progress.connect(self.search_progress_bar.setValue)
            self.search_thread.finished.connect(
                lambda: self.search_button.setText("Start Search")
            )
            self.search_thread.start()

    def full_search_changed(self) -> None:
        """Enable/disable full search"""
        value = self.full_search.isChecked()
        self.advance_range_2.setVisible(value)
        self.iv_2.setVisible(value)
        self.iv_calc_button_2.setVisible(value)
        self.base_seed_input_holder.setVisible(not value)
        self.iv_max_1.setVisible(not value)

    def setup_widgets(self) -> None:
        """Construct soaring fidget widgets"""
        self.main_layout = QVBoxLayout(self)
        self.full_search = QCheckBox("Full Search")
        self.full_search.setChecked(True)
        self.full_search.stateChanged.connect(self.full_search_changed)

        def iv_calc_1_work() -> None:
            full_search = self.full_search.isChecked()
            iv_calc_window = IVCalculatorWindow(self, full_search)
            if iv_calc_window.exec_() == QDialog.Accepted:
                iv_info = iv_calc_window.get_ivs()
                if full_search:
                    for i, iv in enumerate(iv_info):
                        self.iv_widgets_1[i].setValue(iv.start)
                else:
                    for i, iv_range in enumerate(iv_info):
                        self.iv_widgets_1[i].setValue(iv_range.start)
                        self.iv_max_widgets_1[i].setValue(iv_range.stop - 1)

        def iv_calc_2_work() -> None:
            iv_calc_window = IVCalculatorWindow(self, True)
            if iv_calc_window.exec_() == QDialog.Accepted:
                iv_info = iv_calc_window.get_ivs()
                for i, iv in enumerate(iv_info):
                    self.iv_widgets_2[i].setValue(iv.start)

        self.advance_range_1 = RangeWidget(0, 624 * 4, "Pokemon 1 Advance Range")
        self.advance_range_1.min_entry.setValue(600)
        self.advance_range_1.max_entry.setValue(800)
        self.iv_1 = QWidget()
        self.iv_layout_1 = QHBoxLayout(self.iv_1)
        self.iv_widgets_1 = [QSpinBox(minimum=0, maximum=31) for _ in range(6)]
        for iv_widget in self.iv_widgets_1:
            self.iv_layout_1.addWidget(iv_widget)
        self.iv_max_1 = QWidget()
        self.iv_max_layout_1 = QHBoxLayout(self.iv_max_1)
        self.iv_max_widgets_1 = [QSpinBox(minimum=0, maximum=31) for _ in range(6)]
        for iv_widget in self.iv_max_widgets_1:
            iv_widget.setValue(31)
            self.iv_max_layout_1.addWidget(iv_widget)
        self.iv_max_1.setVisible(False)
        self.iv_calc_button_1 = QPushButton("Calculate IVs")
        self.iv_calc_button_1.clicked.connect(iv_calc_1_work)

        self.advance_range_2 = RangeWidget(0, 624 * 4, "Pokemon 2 Advance Range")
        self.advance_range_2.min_entry.setValue(1500)
        self.advance_range_2.max_entry.setValue(1700)
        self.iv_2 = QWidget()
        self.iv_layout_2 = QHBoxLayout(self.iv_2)
        self.iv_widgets_2 = [QSpinBox(minimum=0, maximum=31) for _ in range(6)]
        for iv_widget in self.iv_widgets_2:
            self.iv_layout_2.addWidget(iv_widget)
        self.iv_calc_button_2 = QPushButton("Calculate IVs")
        self.iv_calc_button_2.clicked.connect(iv_calc_2_work)

        self.base_seed_input_holder = QWidget()
        self.base_seed_input_layout = QHBoxLayout(self.base_seed_input_holder)
        self.base_seed_input = QLineEdit()
        self.base_seed_input.setValidator(
            QRegularExpressionValidator(QtCore.QRegularExpression("[0-9a-fA-F]{0,8}"))
        )
        self.base_seed_input_layout.addWidget(QLabel("Base Seed:"))
        self.base_seed_input_layout.addWidget(self.base_seed_input)
        self.base_seed_input_holder.setVisible(False)

        self.search_button = QPushButton("Find Seed")
        self.search_button.clicked.connect(self.search_button_work)
        self.search_progress_bar = ETAProgressBar()
        self.result_list = QListWidget()

        self.main_layout.addWidget(self.full_search)
        self.main_layout.addWidget(self.advance_range_1)
        self.main_layout.addWidget(self.iv_1)
        self.main_layout.addWidget(self.iv_max_1)
        self.main_layout.addWidget(self.iv_calc_button_1)
        self.main_layout.addWidget(self.advance_range_2)
        self.main_layout.addWidget(self.iv_2)
        self.main_layout.addWidget(self.iv_calc_button_2)
        self.main_layout.addWidget(self.base_seed_input_holder)
        self.main_layout.addWidget(self.search_button)
        self.main_layout.addWidget(self.search_progress_bar)
        self.main_layout.addWidget(self.result_list)
