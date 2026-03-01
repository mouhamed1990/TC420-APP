"""
Connection Panel Widget — device connection status and controls.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from src.device_manager import TC420DeviceManager


class StatusIndicator(QLabel):
    """Animated status dot indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("●")
        self.setFixedWidth(20)
        self._connected = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_alpha = 255
        self._pulse_dir = -5
        self._update_style()

    def set_connected(self, connected: bool, mock: bool = False):
        self._connected = connected
        self._mock = mock
        self._update_style()
        if connected:
            self._pulse_timer.start(50)
        else:
            self._pulse_timer.stop()
            self._pulse_alpha = 255

    def _update_style(self):
        if self._connected:
            if hasattr(self, '_mock') and self._mock:
                color = f"rgba(255, 212, 59, {self._pulse_alpha})"
            else:
                color = f"rgba(81, 207, 102, {self._pulse_alpha})"
        else:
            color = "rgba(255, 107, 107, 255)"
        self.setStyleSheet(f"color: {color}; font-size: 16px; background: transparent;")

    def _pulse(self):
        self._pulse_alpha += self._pulse_dir
        if self._pulse_alpha <= 120:
            self._pulse_dir = 5
        elif self._pulse_alpha >= 255:
            self._pulse_dir = -5
        self._update_style()


class ConnectionPanel(QFrame):
    """Device connection panel with status and controls."""

    connection_changed = pyqtSignal(bool)
    status_message = pyqtSignal(str)

    def __init__(self, device_manager: TC420DeviceManager, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.device = device_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("Appareil TC420")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Status row
        status_row = QHBoxLayout()
        self.status_dot = StatusIndicator()
        status_row.addWidget(self.status_dot)

        self.status_label = QLabel("Déconnecté")
        self.status_label.setObjectName("statusDisconnected")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        # Device info
        self.device_info = QLabel("")
        self.device_info.setStyleSheet("color: #9090b0; font-size: 11px; background: transparent;")
        self.device_info.setWordWrap(True)
        layout.addWidget(self.device_info)

        # Buttons
        btn_row = QHBoxLayout()

        self.connect_btn = QPushButton("Connecter")
        self.connect_btn.setObjectName("primary")
        self.connect_btn.clicked.connect(self._toggle_connection)
        btn_row.addWidget(self.connect_btn)

        self.sync_btn = QPushButton("⏱ Sync Heure")
        self.sync_btn.setEnabled(False)
        self.sync_btn.clicked.connect(self._sync_time)
        btn_row.addWidget(self.sync_btn)

        layout.addLayout(btn_row)

    def _toggle_connection(self):
        if self.device.is_connected:
            success, msg = self.device.disconnect()
            self._update_ui(False, False)
            self.connection_changed.emit(False)
            self.status_message.emit(msg)
        else:
            success, msg = self.device.connect()
            self._update_ui(success, self.device.is_mock)
            self.connection_changed.emit(success)
            self.status_message.emit(msg)

    def _update_ui(self, connected: bool, mock: bool):
        self.status_dot.set_connected(connected, mock)

        if connected:
            self.connect_btn.setText("Déconnecter")
            self.connect_btn.setObjectName("danger")
            self.sync_btn.setEnabled(True)

            if mock:
                self.status_label.setText("Mode Simulation")
                self.status_label.setObjectName("statusConnected")
                self.status_label.setStyleSheet("color: #ffd43b; font-weight: 600; background: transparent;")
                self.device_info.setText("Aucun TC420 détecté. Mode simulation actif.\nConnectez un TC420 via USB pour le mode réel.")
            else:
                self.status_label.setText("Connecté")
                self.status_label.setObjectName("statusConnected")
                self.status_label.setStyleSheet("color: #51cf66; font-weight: 600; background: transparent;")
                self.device_info.setText("TC420 LED Controller\nUSB HID")
        else:
            self.connect_btn.setText("Connecter")
            self.connect_btn.setObjectName("primary")
            self.sync_btn.setEnabled(False)
            self.status_label.setText("Déconnecté")
            self.status_label.setObjectName("statusDisconnected")
            self.status_label.setStyleSheet("color: #ff6b6b; font-weight: 600; background: transparent;")
            self.device_info.setText("")

        # Force style refresh
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)

    def _sync_time(self):
        success, msg = self.device.sync_time()
        self.status_message.emit(msg)
