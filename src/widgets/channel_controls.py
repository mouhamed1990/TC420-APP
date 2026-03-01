"""
Channel Controls Widget — manual brightness sliders for each channel.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.models import CHANNEL_COLORS, CHANNEL_NAMES, NUM_CHANNELS


class ChannelSlider(QFrame):
    """A single channel slider with label and value display."""

    value_changed = pyqtSignal(int, int)  # channel, value

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.setObjectName("panel")
        self._init_ui()

    def _init_ui(self):
        color = CHANNEL_COLORS[self.channel]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # Color indicator dot
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 18px; background: transparent;")
        dot.setFixedWidth(20)
        layout.addWidget(dot)

        # Channel name
        name_label = QLabel(CHANNEL_NAMES[self.channel])
        name_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 13px; min-width: 80px; background: transparent;")
        layout.addWidget(name_label)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: none;
                height: 6px;
                background-color: #0d0d1a;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background-color: {color};
                border: 2px solid {color};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 9px;
            }}
            QSlider::handle:horizontal:hover {{
                background-color: white;
                border-color: {color};
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({self._hex_to_rgb(color)}, 0.3),
                    stop:1 {color});
                border-radius: 3px;
            }}
        """)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider, 1)

        # Value display
        self.value_label = QLabel("0%")
        self.value_label.setFixedWidth(45)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setStyleSheet(f"""
            color: {color};
            font-weight: 700;
            font-size: 14px;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            background: transparent;
        """)
        layout.addWidget(self.value_label)

    def _hex_to_rgb(self, hex_color: str) -> str:
        """Convert hex color to RGB string for CSS."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"

    def _on_value_changed(self, value: int):
        self.value_label.setText(f"{value}%")
        self.value_changed.emit(self.channel, value)

    def set_value(self, value: int):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.value_label.setText(f"{value}%")
        self.slider.blockSignals(False)


class ChannelControls(QWidget):
    """Panel with 5 channel sliders for manual brightness control."""

    channel_changed = pyqtSignal(int, int)  # channel, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Contrôle Manuel")
        title.setObjectName("sectionTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # All off button
        self.all_off_btn = QPushButton("Tout éteindre")
        self.all_off_btn.setObjectName("danger")
        self.all_off_btn.setFixedHeight(28)
        self.all_off_btn.clicked.connect(self._all_off)
        header_layout.addWidget(self.all_off_btn)

        # All max button
        self.all_max_btn = QPushButton("Tout à 100%")
        self.all_max_btn.setObjectName("primary")
        self.all_max_btn.setFixedHeight(28)
        self.all_max_btn.clicked.connect(self._all_max)
        header_layout.addWidget(self.all_max_btn)

        layout.addLayout(header_layout)

        # Channel sliders
        self.sliders: list[ChannelSlider] = []
        for i in range(NUM_CHANNELS):
            slider = ChannelSlider(i, self)
            slider.value_changed.connect(self.channel_changed.emit)
            self.sliders.append(slider)
            layout.addWidget(slider)

    def _all_off(self):
        for slider in self.sliders:
            slider.set_value(0)
            self.channel_changed.emit(slider.channel, 0)

    def _all_max(self):
        for slider in self.sliders:
            slider.set_value(100)
            self.channel_changed.emit(slider.channel, 100)

    def set_channel_value(self, channel: int, value: int):
        if 0 <= channel < len(self.sliders):
            self.sliders[channel].set_value(value)
