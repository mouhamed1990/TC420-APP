"""
Timeline Editor Widget — the core visual component.
Displays a 24-hour timeline with 5 color-coded channel curves.
Users can add, drag, and delete control points.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QFrame, QToolTip
)
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QLinearGradient, QBrush, QFont,
    QPainterPath, QMouseEvent, QPaintEvent, QResizeEvent, QCursor
)
from datetime import datetime
from src.models import (
    ModeProgram, ChannelProgram, TimePoint,
    CHANNEL_COLORS, CHANNEL_NAMES, NUM_CHANNELS
)


class TimelineCanvas(QWidget):
    """Custom painting canvas for the 24h timeline."""

    point_changed = pyqtSignal()  # Emitted when any point is modified

    MARGIN_LEFT = 55
    MARGIN_RIGHT = 20
    MARGIN_TOP = 20
    MARGIN_BOTTOM = 40
    POINT_RADIUS = 7
    POINT_HIT_RADIUS = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 300)
        self.setMouseTracking(True)
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._mode_program: ModeProgram = ModeProgram()
        self._channel_visible = [True] * NUM_CHANNELS
        self._active_channel = 0

        # Drag state
        self._dragging = False
        self._drag_channel = -1
        self._drag_point_idx = -1
        self._hover_channel = -1
        self._hover_point_idx = -1

        # Current time indicator
        self._show_current_time = True
        self._current_time_timer = QTimer(self)
        self._current_time_timer.timeout.connect(self.update)
        self._current_time_timer.start(30000)  # Update every 30s

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_mode_program(self, program: ModeProgram):
        self._mode_program = program
        # Reset all interaction state — stale indices from the previous mode
        # would cause IndexError on the new (possibly empty) mode.
        self._dragging = False
        self._drag_channel = -1
        self._drag_point_idx = -1
        self._hover_channel = -1
        self._hover_point_idx = -1
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.update()

    def set_channel_visible(self, channel: int, visible: bool):
        if 0 <= channel < NUM_CHANNELS:
            self._channel_visible[channel] = visible
            self.update()

    def set_active_channel(self, channel: int):
        self._active_channel = channel
        self.update()

    @property
    def plot_rect(self) -> QRectF:
        """The drawable area for the timeline."""
        return QRectF(
            self.MARGIN_LEFT,
            self.MARGIN_TOP,
            self.width() - self.MARGIN_LEFT - self.MARGIN_RIGHT,
            self.height() - self.MARGIN_TOP - self.MARGIN_BOTTOM
        )

    def time_to_x(self, time_minutes: int) -> float:
        r = self.plot_rect
        return r.x() + (time_minutes / 1440.0) * r.width()

    def x_to_time(self, x: float) -> int:
        r = self.plot_rect
        t = int(((x - r.x()) / r.width()) * 1440)
        return max(0, min(1439, t))

    def brightness_to_y(self, brightness: int) -> float:
        r = self.plot_rect
        return r.y() + r.height() - (brightness / 100.0) * r.height()

    def y_to_brightness(self, y: float) -> int:
        r = self.plot_rect
        b = int(((r.y() + r.height() - y) / r.height()) * 100)
        return max(0, min(100, b))

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self.plot_rect

        # Background gradient
        bg_grad = QLinearGradient(0, 0, 0, self.height())
        bg_grad.setColorAt(0, QColor(15, 15, 26))
        bg_grad.setColorAt(1, QColor(22, 33, 62))
        painter.fillRect(self.rect(), bg_grad)

        # Plot area background
        plot_bg = QColor(10, 10, 20, 200)
        painter.fillRect(r.toRect(), plot_bg)

        # Grid
        self._draw_grid(painter, r)

        # Current time indicator
        if self._show_current_time:
            self._draw_current_time(painter, r)

        # Channel curves (draw inactive first, active last)
        draw_order = list(range(NUM_CHANNELS))
        if self._active_channel in draw_order:
            draw_order.remove(self._active_channel)
            draw_order.append(self._active_channel)

        for ch in draw_order:
            if self._channel_visible[ch]:
                is_active = (ch == self._active_channel)
                alpha = 255 if is_active else 80
                self._draw_channel_curve(painter, r, ch, alpha)

        # Draw points on top
        for ch in draw_order:
            if self._channel_visible[ch]:
                is_active = (ch == self._active_channel)
                alpha = 255 if is_active else 100
                self._draw_channel_points(painter, r, ch, alpha)

        # Axis labels
        self._draw_axes(painter, r)

        painter.end()

    def _draw_grid(self, painter: QPainter, r: QRectF):
        """Draw hour grid lines."""
        pen = QPen(QColor(40, 40, 70), 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)

        # Vertical lines (every hour)
        for h in range(25):
            x = self.time_to_x(h * 60)
            painter.drawLine(QPointF(x, r.y()), QPointF(x, r.y() + r.height()))

        # Horizontal lines (every 10%)
        for pct in range(0, 101, 10):
            y = self.brightness_to_y(pct)
            painter.drawLine(QPointF(r.x(), y), QPointF(r.x() + r.width(), y))

    def _draw_current_time(self, painter: QPainter, r: QRectF):
        """Draw vertical line at current time."""
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        x = self.time_to_x(current_minutes)

        pen = QPen(QColor(255, 255, 255, 80), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(x, r.y()), QPointF(x, r.y() + r.height()))

        # Time label
        painter.setPen(QPen(QColor(255, 255, 255, 150)))
        font = QFont("Inter", 9)
        painter.setFont(font)
        painter.drawText(QPointF(x + 4, r.y() + 14), now.strftime("%H:%M"))

    def _draw_channel_curve(self, painter: QPainter, r: QRectF, channel: int, alpha: int):
        """Draw the smooth interpolated curve for a channel."""
        program = self._mode_program.channels[channel]
        if not program.points:
            return

        color = QColor(CHANNEL_COLORS[channel])
        color.setAlpha(alpha)

        # Draw filled area under curve
        fill_color = QColor(CHANNEL_COLORS[channel])
        fill_color.setAlpha(alpha // 8)

        path = QPainterPath()
        fill_path = QPainterPath()

        # Sample curve at regular intervals
        step = 2  # Sample every 2 minutes
        first = True
        for t in range(0, 1441, step):
            b = program.get_brightness_at(t)
            x = self.time_to_x(t)
            y = self.brightness_to_y(b)

            if first:
                path.moveTo(x, y)
                fill_path.moveTo(x, r.y() + r.height())
                fill_path.lineTo(x, y)
                first = False
            else:
                path.lineTo(x, y)
                fill_path.lineTo(x, y)

        # Close fill path
        fill_path.lineTo(self.time_to_x(1440), r.y() + r.height())
        fill_path.closeSubpath()

        # Draw fill
        painter.setPen(Qt.PenStyle.NoPen)
        fill_grad = QLinearGradient(0, r.y(), 0, r.y() + r.height())
        fill_grad.setColorAt(0, fill_color)
        fill_grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(fill_grad))
        painter.drawPath(fill_path)

        # Draw curve line
        line_width = 2.5 if channel == self._active_channel else 1.5
        pen = QPen(color, line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _draw_channel_points(self, painter: QPainter, r: QRectF, channel: int, alpha: int):
        """Draw control points for a channel."""
        program = self._mode_program.channels[channel]
        color = QColor(CHANNEL_COLORS[channel])

        is_active = (channel == self._active_channel)
        radius = self.POINT_RADIUS if is_active else self.POINT_RADIUS - 2

        for i, point in enumerate(program.points):
            x = self.time_to_x(point.time_minutes)
            y = self.brightness_to_y(point.brightness)

            is_hovered = (self._hover_channel == channel and self._hover_point_idx == i)
            is_dragged = (self._drag_channel == channel and self._drag_point_idx == i)

            if is_hovered or is_dragged:
                # Glow effect
                glow = QColor(CHANNEL_COLORS[channel])
                glow.setAlpha(60)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(QPointF(x, y), radius + 6, radius + 6)

            # Point outline
            outline = QColor(CHANNEL_COLORS[channel])
            outline.setAlpha(alpha)
            painter.setPen(QPen(outline, 2))

            # Point fill
            fill = QColor(CHANNEL_COLORS[channel])
            fill.setAlpha(alpha)
            if not is_active:
                fill = QColor(30, 30, 50, alpha)
            painter.setBrush(QBrush(fill))

            painter.drawEllipse(QPointF(x, y), radius, radius)

    def _draw_axes(self, painter: QPainter, r: QRectF):
        """Draw axis labels."""
        font = QFont("Inter", 9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(144, 144, 176)))

        # X axis: hours
        for h in range(0, 25, 2):
            x = self.time_to_x(h * 60)
            label = f"{h:02d}:00"
            painter.drawText(
                QRectF(x - 25, r.y() + r.height() + 6, 50, 20),
                Qt.AlignmentFlag.AlignCenter,
                label
            )

        # Y axis: brightness percentage
        for pct in range(0, 101, 20):
            y = self.brightness_to_y(pct)
            label = f"{pct}%"
            painter.drawText(
                QRectF(4, y - 10, self.MARGIN_LEFT - 10, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label
            )

    def _find_point_at(self, pos: QPoint) -> tuple[int, int]:
        """Find a control point at the given screen position. Returns (channel, point_index)."""
        # Search active channel first, then others
        channels_to_search = [self._active_channel] + [
            c for c in range(NUM_CHANNELS) if c != self._active_channel
        ]

        for ch in channels_to_search:
            if not self._channel_visible[ch]:
                continue
            program = self._mode_program.channels[ch]
            for i, point in enumerate(program.points):
                px = self.time_to_x(point.time_minutes)
                py = self.brightness_to_y(point.brightness)
                dist = ((pos.x() - px) ** 2 + (pos.y() - py) ** 2) ** 0.5
                if dist <= self.POINT_HIT_RADIUS:
                    return ch, i
        return -1, -1

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            ch, idx = self._find_point_at(event.pos())
            if ch >= 0:
                # Start dragging existing point
                self._dragging = True
                self._drag_channel = ch
                self._drag_point_idx = idx
                self._active_channel = ch
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            else:
                # Add new point on active channel
                r = self.plot_rect
                if r.contains(QPointF(event.pos())):
                    t = self.x_to_time(event.pos().x())
                    b = self.y_to_brightness(event.pos().y())
                    channel = self._mode_program.channels[self._active_channel]
                    tp = channel.add_point(t, b)
                    if tp:
                        # Find the newly added point index
                        for i, p in enumerate(channel.points):
                            if p.time_minutes == t and p.brightness == b:
                                self._dragging = True
                                self._drag_channel = self._active_channel
                                self._drag_point_idx = i
                                break
                        self.point_changed.emit()

            self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            # Delete point
            ch, idx = self._find_point_at(event.pos())
            if ch >= 0:
                self._mode_program.channels[ch].remove_point(idx)
                self.point_changed.emit()
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            r = self.plot_rect
            x = max(r.x(), min(r.x() + r.width(), event.pos().x()))
            y = max(r.y(), min(r.y() + r.height(), event.pos().y()))

            t = self.x_to_time(x)
            b = self.y_to_brightness(y)

            channel = self._mode_program.channels[self._drag_channel]
            if 0 <= self._drag_point_idx < len(channel.points):
                channel.points[self._drag_point_idx].time_minutes = t
                channel.points[self._drag_point_idx].brightness = b

                # Show tooltip
                tp = channel.points[self._drag_point_idx]
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"{tp.time_str} — {tp.brightness}%"
                )

            self.update()
        else:
            # Hover detection
            ch, idx = self._find_point_at(event.pos())
            if ch != self._hover_channel or idx != self._hover_point_idx:
                self._hover_channel = ch
                self._hover_point_idx = idx
                if ch >= 0:
                    self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    tp = self._mode_program.channels[ch].points[idx]
                    QToolTip.showText(
                        event.globalPosition().toPoint(),
                        f"{CHANNEL_NAMES[ch]}\n{tp.time_str} — {tp.brightness}%"
                    )
                else:
                    self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging:
            # Sort points after drag
            channel = self._mode_program.channels[self._drag_channel]
            channel.sort()
            self._dragging = False
            self._drag_channel = -1
            self._drag_point_idx = -1
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            self.point_changed.emit()
            self.update()

    def leaveEvent(self, event):
        self._hover_channel = -1
        self._hover_point_idx = -1
        self.update()


class TimelineEditor(QWidget):
    """Complete timeline editor with canvas + channel toggles."""

    point_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Canvas
        self.canvas = TimelineCanvas(self)
        self.canvas.point_changed.connect(self.point_changed.emit)
        layout.addWidget(self.canvas, 1)

        # Channel toggle bar
        toggle_frame = QFrame()
        toggle_frame.setObjectName("panel")
        toggle_layout = QHBoxLayout(toggle_frame)
        toggle_layout.setContentsMargins(12, 8, 12, 8)
        toggle_layout.setSpacing(16)

        legend_label = QLabel("Canaux:")
        legend_label.setStyleSheet("font-weight: 600; color: #9090b0;")
        toggle_layout.addWidget(legend_label)

        self._checkboxes = []
        for i in range(NUM_CHANNELS):
            cb = QCheckBox(CHANNEL_NAMES[i])
            cb.setChecked(True)
            color = CHANNEL_COLORS[i]
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {color};
                    font-weight: 500;
                    spacing: 6px;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {color};
                    border-color: {color};
                }}
            """)
            ch_idx = i
            cb.toggled.connect(lambda checked, c=ch_idx: self.canvas.set_channel_visible(c, checked))
            cb.clicked.connect(lambda _, c=ch_idx: self.canvas.set_active_channel(c))
            self._checkboxes.append(cb)
            toggle_layout.addWidget(cb)

        toggle_layout.addStretch()

        # Instructions label
        help_label = QLabel("Clic gauche: ajouter  |  Glisser: déplacer  |  Clic droit: supprimer")
        help_label.setStyleSheet("color: #606080; font-size: 11px;")
        toggle_layout.addWidget(help_label)

        layout.addWidget(toggle_frame)

    def set_mode_program(self, program: ModeProgram):
        self.canvas.set_mode_program(program)

    def set_active_channel(self, channel: int):
        self.canvas.set_active_channel(channel)
