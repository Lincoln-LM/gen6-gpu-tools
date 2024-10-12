"""QWidget window for the main program"""

from qtpy.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTabWidget,
)

from .opencl_selector import OpenCLSelector
from .soaring_fidget import SoaringFidgetTab
from .unique_hash import UniqueHashTab
from .iv_search import IVSearchTab


class MainWindow(QWidget):
    """QWidget window for the main program"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gen 6 GPU Tools")
        self.setup_widgets()

        self.show()

    def setup_widgets(self) -> None:
        """Construct main window widgets"""
        self.main_layout = QVBoxLayout(self)
        self.opencl_selector = OpenCLSelector()
        self.tab_widget = QTabWidget()

        self.tab_widget.addTab(IVSearchTab(self.opencl_selector), "IV Search")
        self.tab_widget.addTab(SoaringFidgetTab(self.opencl_selector), "Soaring Fidget")
        self.tab_widget.addTab(UniqueHashTab(self.opencl_selector), "Unique Hash")

        self.main_layout.addWidget(self.opencl_selector)
        self.main_layout.addWidget(self.tab_widget)
