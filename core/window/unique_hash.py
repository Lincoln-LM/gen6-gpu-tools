"""Widget for the unique hash tab in the main window"""

import struct
from qtpy.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QCheckBox,
)
from qtpy.QtCore import Qt
from Crypto.Cipher import AES

from .opencl_selector import OpenCLSelector
from .eta_progress_bar import ETAProgressBar
from ..shaders.unique_hash import SearchUniqueHashThread


class UniqueHashTab(QWidget):
    """QWidget for the soaring fidget tab in the main window"""

    def __init__(self, opencl_selector: OpenCLSelector) -> None:
        super().__init__()
        self.opencl_selector = opencl_selector
        self.setup_widgets()
        self.search_thread = None
        self.hash_0 = None

    def display_result(self, result) -> None:
        """Display the result of the search to a label"""
        self.result_label.setText(f"Result: {result:08X}")

    def select_bin_work(self) -> None:
        """Open file selector for input.bin"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select input.bin", "", "bin files (*.bin)"
        )
        if filename:
            with open(filename, "rb") as f:
                enc = f.read()
            key = (0x59FC817E6446EA6190347B20E9BDCE52).to_bytes(16, "big")
            assert len(enc) == 0x70
            nonce = enc[:8] + b"\x00" * 4
            cipher = AES.new(key, AES.MODE_CCM, nonce)
            dec = cipher.decrypt(enc[8:0x60])
            nonce = nonce[:8]
            final = dec[:12] + nonce + dec[12:]
            # GenHashConsoleUnique(0)
            self.hash_0 = struct.unpack("<II", final[4 : 4 + 8])
            self.search_button.setEnabled(True)
            self.search_progress_bar.reset()

    def search_button_work(self) -> None:
        """Starts search thread"""
        platform, device = (
            self.opencl_selector.get_platform(),
            self.opencl_selector.get_device(),
        )
        assert platform is not None and device is not None

        self.search_thread = SearchUniqueHashThread(
            platform, device, self.new_3ds_checkbox.isChecked(), *self.hash_0
        )
        self.search_thread.results.connect(self.display_result)
        self.search_thread.init_progress_bar.connect(
            self.search_progress_bar.setMaximum
        )
        self.search_thread.progress.connect(self.search_progress_bar.setValue)
        self.search_thread.start()

    def setup_widgets(self) -> None:
        """Construct unique hash widgets"""
        self.main_layout = QVBoxLayout(self)
        self.select_bin = QPushButton("Select input.bin")
        self.select_bin.clicked.connect(self.select_bin_work)
        self.new_3ds_checkbox = QCheckBox("New 3DS")
        self.search_button = QPushButton("Find Hash")
        self.search_button.setEnabled(False)
        self.search_button.clicked.connect(self.search_button_work)
        self.search_progress_bar = ETAProgressBar()
        self.result_label = QLabel("Result:")
        self.result_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.main_layout.addWidget(self.select_bin)
        self.main_layout.addWidget(self.new_3ds_checkbox)
        self.main_layout.addWidget(self.search_button)
        self.main_layout.addWidget(self.search_progress_bar)
        self.main_layout.addWidget(self.result_label)
