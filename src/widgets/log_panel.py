"""
Log Panel — scrollable widget showing TC420 upload history.
Each row: icon · date · modes · status badge · message.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.utils.upload_log import LogEntry, load_log, clear_log


# ── palette ──────────────────────────────────────────────────────────────────
_BG           = "#0f0f1f"
_PANEL        = "#16213e"
_BORDER       = "#2a2d5a"
_TEXT         = "#e8e8f0"
_DIM          = "#9090b0"
_SUCCESS_BG   = "#0d2b1a"
_SUCCESS_FG   = "#51cf66"
_SUCCESS_BD   = "#1a4d30"
_FAIL_BG      = "#2b0d0d"
_FAIL_FG      = "#ff6b6b"
_FAIL_BD      = "#5a1a1a"
_CLEAR_BTN    = "#1e2040"
_CLEAR_HOVER  = "#2a2d5a"


class _EntryRow(QFrame):
    """One log row."""

    def __init__(self, entry: LogEntry, parent=None):
        super().__init__(parent)
        self.setObjectName("logRow")

        ok = entry.success
        bd = _SUCCESS_BD if ok else _FAIL_BD
        self.setStyleSheet(f"""
            QFrame#logRow {{
                background: {_PANEL};
                border: 1px solid {bd};
                border-radius: 8px;
                margin: 0px 0px 4px 0px;
            }}
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)

        # ── icon ────────────────────────────────────────────────────────────
        icon = QLabel("✅" if ok else "❌")
        icon.setFont(QFont("Segoe UI Emoji", 14))
        icon.setFixedWidth(22)
        row.addWidget(icon)

        # ── date + mode name ────────────────────────────────────────────────
        meta = QVBoxLayout()
        meta.setSpacing(1)

        date_lbl = QLabel(entry.timestamp.replace("T", "  "))
        date_lbl.setStyleSheet(f"color:{_DIM}; font-size:11px; background:transparent;")
        meta.addWidget(date_lbl)

        modes_lbl = QLabel(
            f"{entry.n_modes} mode(s) — {entry.mode_name}"
            if entry.n_modes > 1
            else entry.mode_name
        )
        modes_lbl.setStyleSheet(f"color:{_TEXT}; font-size:13px; font-weight:600; background:transparent;")
        meta.addWidget(modes_lbl)

        row.addLayout(meta, stretch=1)

        # ── status badge ────────────────────────────────────────────────────
        badge_text = "Succès" if ok else "Échec"
        badge_fg   = _SUCCESS_FG if ok else _FAIL_FG
        badge_bg   = _SUCCESS_BG if ok else _FAIL_BG
        badge_bd   = _SUCCESS_BD if ok else _FAIL_BD

        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedWidth(68)
        badge.setStyleSheet(f"""
            QLabel {{
                color: {badge_fg};
                background: {badge_bg};
                border: 1px solid {badge_bd};
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)
        row.addWidget(badge)

        # ── compact message (tooltip for full text) ──────────────────────────
        msg_short = entry.message if len(entry.message) <= 55 else entry.message[:52] + "…"
        msg_lbl = QLabel(msg_short)
        msg_lbl.setFixedWidth(200)
        msg_lbl.setStyleSheet(
            f"color:{_DIM}; font-size:11px; background:transparent;"
        )
        msg_lbl.setToolTip(entry.message)
        row.addWidget(msg_lbl)


class LogPanel(QWidget):
    """Scrollable log panel — call refresh() to reload from disk."""

    log_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f"background: {_BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header bar
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {_PANEL};
                border-bottom: 1px solid {_BORDER};
            }}
        """)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 10, 16, 10)
        hlay.setSpacing(8)

        title = QLabel("📋  Historique des envois")
        title.setStyleSheet(f"color:{_TEXT}; font-size:14px; font-weight:700; background:transparent;")
        hlay.addWidget(title)
        hlay.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(f"color:{_DIM}; font-size:12px; background:transparent;")
        hlay.addWidget(self._count_lbl)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setFixedHeight(28)
        refresh_btn.setStyleSheet(self._btn_style(_CLEAR_BTN, _CLEAR_HOVER))
        refresh_btn.clicked.connect(self.refresh)
        hlay.addWidget(refresh_btn)

        clear_btn = QPushButton("🗑 Effacer")
        clear_btn.setFixedHeight(28)
        clear_btn.setStyleSheet(self._btn_style("#2b0d0d", "#5a1a1a"))
        clear_btn.clicked.connect(self._on_clear)
        hlay.addWidget(clear_btn)

        root.addWidget(header)

        # scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {_BG}; }}
            QScrollBar:vertical {{
                background: {_PANEL}; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {_BORDER}; border-radius: 4px;
            }}
        """)

        self._body = QWidget()
        self._body.setStyleSheet(f"background: {_BG};")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(12, 12, 12, 12)
        self._body_layout.setSpacing(0)
        self._body_layout.addStretch()

        scroll.setWidget(self._body)
        root.addWidget(scroll, 1)

    @staticmethod
    def _btn_style(bg: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background: {bg}; color: #e8e8f0;
                border: 1px solid #3a3d6a; border-radius: 5px;
                padding: 2px 10px; font-size: 12px;
            }}
            QPushButton:hover {{ background: {hover}; }}
        """

    # ── public API ───────────────────────────────────────────────────────────

    def refresh(self):
        """Reload entries from disk and redraw."""
        # clear existing rows (keep the trailing stretch)
        while self._body_layout.count() > 1:
            item = self._body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = load_log()
        self._count_lbl.setText(
            f"{len(entries)} entrée(s)" if entries else "Aucun envoi enregistré"
        )

        if not entries:
            empty = QLabel("Aucun envoi pour le moment.\nEnvoyez un programme vers le TC420 pour voir l'historique ici.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_DIM}; font-size:13px; background:transparent; padding:32px;")
            empty.setWordWrap(True)
            self._body_layout.insertWidget(0, empty)
        else:
            for entry in entries:
                row = _EntryRow(entry)
                self._body_layout.insertWidget(self._body_layout.count() - 1, row)

    def add_entry_live(self, entry: LogEntry):
        """Insert a new entry at the top without reloading from disk."""
        row = _EntryRow(entry)
        # Remove 'empty' label if present
        if self._body_layout.count() == 2:
            item = self._body_layout.itemAt(0)
            if item and item.widget() and isinstance(item.widget(), QLabel):
                item.widget().deleteLater()
                self._body_layout.removeItem(item)

        self._body_layout.insertWidget(0, row)
        entries = load_log()
        self._count_lbl.setText(f"{len(entries)} entrée(s)")

    def _on_clear(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Effacer l'historique",
            "Supprimer tout l'historique des envois ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            clear_log()
            self.refresh()
            self.log_cleared.emit()
