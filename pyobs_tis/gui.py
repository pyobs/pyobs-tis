import asyncio
import sys
from typing import Any

import numpy as np
import qasync  # type: ignore[import-untyped]
from pyobs.utils.gui.camera import ListPickerDialog
from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore[import-untyped]

from . import TIS


class LivePreviewWidget(QtWidgets.QLabel):
    """Lightweight image label for continuous frame updates (not FITS-backed, unlike DataDisplayWidget)."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(320, 240)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setText("No image yet")
        self._pixmap: QtGui.QPixmap | None = None

    def set_frame(self, frame: np.ndarray) -> None:
        frame = np.ascontiguousarray(frame)
        if frame.ndim == 3 and frame.shape[2] == 4:
            height, width = frame.shape[:2]
            image = QtGui.QImage(frame.data, width, height, 4 * width, QtGui.QImage.Format.Format_RGB32)
        else:
            if frame.ndim == 3:
                frame = frame[:, :, 0]
            if frame.dtype == np.uint16:
                frame = (frame >> 8).astype(np.uint8)
            frame = np.ascontiguousarray(frame)
            height, width = frame.shape[:2]
            image = QtGui.QImage(frame.data, width, height, width, QtGui.QImage.Format.Format_Grayscale8)

        self._pixmap = QtGui.QPixmap.fromImage(image.copy())
        self._update_pixmap()

    def _update_pixmap(self) -> None:
        if self._pixmap is not None:
            self.setPixmap(self._pixmap.scaled(self.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # type: ignore[override]
        self._update_pixmap()
        super().resizeEvent(event)


class PropertyPanel(QtWidgets.QGroupBox):
    """Generic panel over TIS's tcam properties — numeric ranges get a spinbox, booleans a
    checkbox, everything else (enums, buttons, strings) is shown read-only, since the tcam
    property type strings aren't reliably decodable without the SDK docs at hand."""

    def __init__(self, camera: TIS.TIS) -> None:
        super().__init__("Properties")
        self._camera = camera

        layout = QtWidgets.QFormLayout(self)
        for name in camera.get_property_names():
            try:
                prop = camera.Get_Property(name)
            except Exception:
                continue
            widget = self._build_widget(name, prop)
            if widget is not None:
                layout.addRow(name, widget)

    def _build_widget(self, name: str, prop: TIS.CameraProperty) -> QtWidgets.QWidget | None:
        value = prop.value

        if isinstance(value, bool):
            box = QtWidgets.QCheckBox()
            box.setChecked(value)
            box.toggled.connect(lambda checked, n=name: self._set(n, checked))
            return box

        if isinstance(value, (int, float)) and prop.min is not None and prop.max is not None and prop.min != prop.max:
            is_int = isinstance(value, int)
            spin = QtWidgets.QDoubleSpinBox()
            spin.setDecimals(0 if is_int else 3)
            spin.setRange(float(prop.min), float(prop.max))
            spin.setSingleStep(float(prop.step) if prop.step else 1.0)
            spin.setValue(float(value))
            spin.valueChanged.connect(lambda v, n=name, i=is_int: self._set(n, int(v) if i else v))
            return spin

        label = QtWidgets.QLabel(str(value))
        label.setEnabled(False)
        return label

    def _set(self, name: str, value: Any) -> None:
        try:
            self._camera.Set_Property(name, value)
        except Exception as e:
            print(f"Could not set property {name}: {e}")


class MainWindow(QtWidgets.QMainWindow):
    frame_received = QtCore.Signal(object)

    def __init__(self, serial: str) -> None:
        super().__init__()
        self.setWindowTitle(f"TIS Camera ({serial})")

        self._camera = TIS.TIS()
        self._camera.serialnumber = serial

        formats = self._camera.createFormats()
        if not formats:
            raise ValueError("No formats available for this device.")

        format_name = "GRAY8" if "GRAY8" in formats else next(iter(formats))
        fmt = formats[format_name]
        res = fmt.res_list[0]
        fps = res.fps[0]

        sink_format = TIS.SinkFormats.GRAY8 if format_name == "GRAY8" else TIS.SinkFormats.BGRA
        self._camera.openDevice(serial, res.width, res.height, fps, sink_format, False)
        # frames arrive on TIS's own GStreamer thread; the queued cross-thread signal connection
        # below is what makes it safe to hand them to a widget living on the Qt/GUI thread.
        self._camera.Set_Image_Callback(self._on_new_frame)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        controls = QtWidgets.QVBoxLayout()
        layout.addLayout(controls)

        self._start_button = QtWidgets.QPushButton("Start")
        self._start_button.clicked.connect(self._start_clicked)
        controls.addWidget(self._start_button)

        self._stop_button = QtWidgets.QPushButton("Stop")
        self._stop_button.clicked.connect(self._stop_clicked)
        self._stop_button.setEnabled(False)
        controls.addWidget(self._stop_button)

        controls.addWidget(PropertyPanel(self._camera))
        controls.addStretch()

        self._preview = LivePreviewWidget()
        layout.addWidget(self._preview, stretch=1)

        self.frame_received.connect(self._preview.set_frame)

    def _on_new_frame(self, tis: TIS.TIS) -> None:
        self.frame_received.emit(tis.Get_image())

    def _start_clicked(self) -> None:
        if not self._camera.Start_pipeline():
            self._camera.Stop_pipeline()
            QtWidgets.QMessageBox.critical(self, "Error", "Could not start pipeline.")
            return
        self._start_button.setEnabled(False)
        self._stop_button.setEnabled(True)

    def _stop_clicked(self) -> None:
        self._camera.Stop_pipeline()
        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        self._camera.Stop_pipeline()
        super().closeEvent(event)


async def async_main(app: QtWidgets.QApplication) -> None:
    devices = TIS.TIS.list_devices()
    if not devices:
        QtWidgets.QMessageBox.critical(None, "Error", "No TIS camera found.")
        return

    if len(devices) > 1:
        picker = ListPickerDialog([f"{d.name} ({d.serial})" for d in devices])
        if picker.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        device = devices[picker.comboBox().currentIndex()]
    else:
        device = devices[0]

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    window = MainWindow(device.serial)
    window.show()

    await app_close_event.wait()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    asyncio.run(async_main(app), loop_factory=qasync.QEventLoop)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
