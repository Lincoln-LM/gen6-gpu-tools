"""Main script for {}"""

import sys
import qdarkstyle
from core.window.main_window import MainWindow
from qtpy.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    window.show()
    window.setFocus()

    sys.exit(app.exec())
