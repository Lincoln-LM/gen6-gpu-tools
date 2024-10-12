"""IV Calculator Window"""

import numpy as np
from numba_pokemon_prngs.data import NATURES_EN

from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QLabel,
    QComboBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
)


class IVCalculatorWindow(QDialog):
    """IV Calculator Window"""

    def __init__(self, parent: QWidget, strict: bool) -> None:
        super().__init__(parent)
        self.setWindowTitle("IV Calculator")
        self.setModal(True)
        self.main_layout = QVBoxLayout(self)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        self.confirm_button.setDisabled(True)
        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.calculate)
        self.strict = strict
        self.nature_combo = QComboBox()
        self.nature_combo.addItems([nature.capitalize() for nature in NATURES_EN])
        self.data_entry = QTextEdit()

        self.results_widget = QWidget()
        self.results_layout = QGridLayout(self.results_widget)
        for i, stat in enumerate(("HP", "Atk", "Def", "SpA", "SpD", "Spe")):
            self.results_layout.addWidget(QLabel(stat), i, 0)

        self.main_layout.addWidget(self.nature_combo)
        self.main_layout.addWidget(self.data_entry)
        self.main_layout.addWidget(self.calculate_button)
        self.main_layout.addWidget(self.results_widget)
        self.main_layout.addWidget(self.confirm_button)
        self.iv_ranges: list[range] = [
            range(32),
            range(32),
            range(32),
            range(32),
            range(32),
            range(32),
        ]

    def get_ivs(self) -> tuple[int, int, int, int, int, int]:
        """Function to get the calculated ivs after the window is closed"""
        if not self.strict:
            return self.iv_ranges
        if all(len(iv_range) == 1 for iv_range in self.iv_ranges):
            return tuple(iv_range[0] for iv_range in self.iv_ranges)
        raise Exception("IVs could not be calculated to precise values")

    @staticmethod
    def calc_stat(
        stat_index: int,
        base_stat: np.uint16,
        iv: np.uint8,
        level: np.uint8,
        nature: np.uint8,
    ):
        """Calcuate a stat value"""
        iv_map = (-1, 0, 1, 3, 4, 2)
        stat = np.uint16(
            np.uint16((np.uint16(2) * base_stat + iv) * level) // np.uint16(100)
        )
        nature_boost = nature // np.uint8(5)
        nature_decrease = nature % np.uint8(5)
        if stat_index == 0:
            stat += np.uint16(level) + np.uint16(10)
        else:
            stat += np.uint16(5)
            if nature_boost != nature_decrease:
                if iv_map[stat_index] == nature_boost:
                    stat = np.uint16(stat * np.float32(1.1))
                elif iv_map[stat_index] == nature_decrease:
                    stat = np.uint16(stat * np.float32(0.9))
        return stat

    @staticmethod
    def calc_ivs(
        base_stats: np.array, stats: np.array, level: np.uint8, nature: np.uint8
    ) -> tuple[range, range, range, range, range, range]:
        """Calculate possible ivs"""
        min_ivs = np.ones(6, np.uint8) * 31
        max_ivs = np.zeros(6, np.uint8)
        for i in range(6):
            for iv in range(32):
                stat = IVCalculatorWindow.calc_stat(
                    i, base_stats[i], np.uint8(iv), np.uint8(level), np.uint8(nature)
                )
                if stat == stats[i]:
                    min_ivs[i] = min(iv, min_ivs[i])
                    max_ivs[i] = max(iv, max_ivs[i])
        return tuple(
            range(min_iv, max_iv + 1) for min_iv, max_iv in zip(min_ivs, max_ivs)
        )

    def calculate(self) -> None:
        """Calculate IVs"""
        self.iv_ranges = [
            range(32),
            range(32),
            range(32),
            range(32),
            range(32),
            range(32),
        ]
        nature = np.int8(self.nature_combo.currentIndex())
        rows = [row for row in self.data_entry.toPlainText().split("\n") if row]
        stats = np.array(tuple(map(int, rows[0].split(" "))), np.uint16)
        # aerodactyl
        level = np.uint8(20)
        base_stats = np.array(
            (
                80,
                105,
                65,
                60,
                75,
                130,
            ),
            np.uint16,
        )

        def try_intersect(x, y):
            try:
                return range(max(x[0], y[0]), min(x[-1], y[-1]) + 1)
            except IndexError:
                return range(32, 0)

        self.iv_ranges = [
            try_intersect(x, y)
            for x, y in zip(
                self.iv_ranges,
                IVCalculatorWindow.calc_ivs(base_stats, stats, level, nature),
            )
        ]
        for row in rows[1:]:
            level += 1
            stat_changes = tuple(map(int, row.split(" ")))
            stats += np.array(stat_changes, np.uint16)

            self.iv_ranges = [
                try_intersect(x, y)
                for x, y in zip(
                    self.iv_ranges,
                    IVCalculatorWindow.calc_ivs(base_stats, stats, level, nature),
                )
            ]
        for i, iv_range in enumerate(self.iv_ranges):
            if len(iv_range) == 0:
                self.results_layout.addWidget(QLabel("Invalid"), i, 1)
            else:
                self.results_layout.addWidget(
                    QLabel(
                        f"{iv_range.start}-{iv_range.stop - 1}"
                        if len(iv_range) > 1
                        else f"{iv_range.start}"
                    ),
                    i,
                    1,
                )
        self.confirm_button.setDisabled(
            any(len(iv_range) != 1 for iv_range in self.iv_ranges) and self.strict
        )
