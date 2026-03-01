"""
Toolbar Widget — top action bar with mode selection and file operations.
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import pyqtSignal


class ToolBar(QFrame):
    """Top toolbar with upload, download, save, and load actions."""

    upload_clicked = pyqtSignal()
    download_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    load_clicked = pyqtSignal()
    demo_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # App title
        title = QLabel("TC420 Controller")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("LED Programmable Controller")
        subtitle.setObjectName("subtitle")
        subtitle.setStyleSheet("color: #9090b0; font-size: 12px; margin-left: 8px; background: transparent;")
        layout.addWidget(subtitle)

        layout.addStretch()

        # File operations
        self.load_btn = QPushButton("📂 Ouvrir")
        self.load_btn.setToolTip("Ouvrir un fichier programme (.tc420)")
        self.load_btn.clicked.connect(self.load_clicked.emit)
        layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("💾 Sauvegarder")
        self.save_btn.setToolTip("Sauvegarder le programme actuel")
        self.save_btn.clicked.connect(self.save_clicked.emit)
        layout.addWidget(self.save_btn)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("background-color: #2a2d5a; max-width: 1px;")
        sep1.setFixedWidth(1)
        layout.addWidget(sep1)

        # Device operations
        self.download_btn = QPushButton("📥 Lire Appareil")
        self.download_btn.setToolTip("Lire le programme depuis le TC420")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_clicked.emit)
        layout.addWidget(self.download_btn)

        self.upload_btn = QPushButton("📤 Envoyer")
        self.upload_btn.setObjectName("primary")
        self.upload_btn.setToolTip("Envoyer le programme vers le TC420")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self.upload_clicked.emit)
        layout.addWidget(self.upload_btn)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("background-color: #2a2d5a; max-width: 1px;")
        sep2.setFixedWidth(1)
        layout.addWidget(sep2)

        # Demo
        self.demo_btn = QPushButton("🎨 Démo")
        self.demo_btn.setToolTip("Lancer une démo de lumières")
        self.demo_btn.setEnabled(False)
        self.demo_btn.clicked.connect(self.demo_clicked.emit)
        layout.addWidget(self.demo_btn)

    def set_device_connected(self, connected: bool):
        """Enable/disable device-dependent buttons."""
        self.upload_btn.setEnabled(connected)
        self.download_btn.setEnabled(connected)
        self.demo_btn.setEnabled(connected)


class ModeSelector(QWidget):
    """Mode tab selector (Mode 1-4)."""

    mode_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_mode = 0
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel("Mode:")
        label.setStyleSheet("color: #9090b0; font-weight: 600; font-size: 13px; background: transparent;")
        layout.addWidget(label)

        self._buttons: list[QPushButton] = []
        for i in range(4):
            btn = QPushButton(f"Mode {i + 1}")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda _, idx=i: self._on_mode_clicked(idx))
            self._buttons.append(btn)
            layout.addWidget(btn)

        self._update_styles()
        layout.addStretch()

    def _on_mode_clicked(self, index: int):
        self._active_mode = index
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self._update_styles()
        self.mode_changed.emit(index)

    def _update_styles(self):
        for i, btn in enumerate(self._buttons):
            if i == self._active_mode:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0099cc;
                        border: 1px solid #00d4ff;
                        color: white;
                        font-weight: 700;
                        border-radius: 8px;
                        padding: 6px 20px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #16213e;
                        border: 1px solid #2a2d5a;
                        color: #9090b0;
                        font-weight: 500;
                        border-radius: 8px;
                        padding: 6px 20px;
                    }
                    QPushButton:hover {
                        background-color: #2a2d4a;
                        color: #e8e8f0;
                    }
                """)

    def set_active_mode(self, index: int):
        self._on_mode_clicked(index)
