"""OpenCL platform/device selector widget"""

from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QWidget,
)
import pyopencl as cl


class OpenCLSelector(QWidget):
    """QWidget for selecting OpenCL platform/device"""

    def __init__(self) -> None:
        super().__init__()
        self.platforms = cl.get_platforms()
        self.devices = None

        self.main_layout = QHBoxLayout(self)
        self.platforms_selector = QComboBox()
        self.platforms_selector.addItem("Select Platform", None)
        for platform in self.platforms:
            self.platforms_selector.addItem(platform.name, platform)

        self.platforms_selector.activated.connect(self.on_platform_change)
        self.devices_selector = QComboBox()
        self.devices_selector.addItem("Select Device", None)
        self.devices_selector.setEnabled(False)
        self.main_layout.addWidget(self.platforms_selector)
        self.main_layout.addWidget(self.devices_selector)

    def on_platform_change(self, index: int) -> None:
        """Handle platform change"""
        self.devices = self.platforms_selector.itemData(index).get_devices()
        self.devices_selector.clear()
        self.devices_selector.addItem("Select Device", None)
        for device in self.devices:
            self.devices_selector.addItem(device.name, device)
        self.devices_selector.setEnabled(True)

    def get_platform(self) -> cl.Platform:
        """Get selected platform"""
        return self.platforms_selector.currentData()

    def get_device(self) -> cl.Device:
        """Get selected device"""
        return self.devices_selector.currentData()
