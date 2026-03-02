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
        self.download_btn = QPushButton("ℹ️ Infos appareil")
        self.download_btn.setToolTip(
            "Le TC420 est en écriture seule — impossible de relire les programmes depuis l'appareil"
        )
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
    """Mode tab selector (Supports up to 50 modes)."""

    mode_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_mode = 0
        from PyQt6.QtWidgets import QComboBox
        self._init_ui()

    def _init_ui(self):
        from PyQt6.QtWidgets import QComboBox
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel("Mode:")
        label.setStyleSheet("color: #9090b0; font-weight: 600; font-size: 13px; background: transparent;")
        layout.addWidget(label)

        self.combo = QComboBox()
        self.combo.setFixedHeight(32)
        self.combo.setMinimumWidth(150)
        self.combo.setStyleSheet("""
            QComboBox {
                background-color: #16213e;
                border: 1px solid #2a2d5a;
                color: #e8e8f0;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 13px;
                font-weight: 600;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #00d4ff;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                border: 1px solid #2a2d5a;
                color: #e8e8f0;
                selection-background-color: #0099cc;
                selection-color: white;
            }
        """)
        
        self.combo.currentIndexChanged.connect(self._on_mode_clicked)
        layout.addWidget(self.combo)
        layout.addStretch()

    def populate_modes(self, mode_names: list[str]):
        """Populate the combo box with mode names."""
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(mode_names)
        self.combo.setCurrentIndex(self._active_mode)
        self.combo.blockSignals(False)

    def _on_mode_clicked(self, index: int):
        if index >= 0:
            self._active_mode = index
            self.mode_changed.emit(index)

    def set_active_mode(self, index: int):
        if index >= 0 and index < self.combo.count():
            self._active_mode = index
            self.combo.setCurrentIndex(index)
