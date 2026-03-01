"""
Dark theme and styling for TC420 LED Controller GUI.
Premium dark theme with glassmorphism-style panels.
"""

# Color palette
COLORS = {
    # Backgrounds
    "bg_primary": "#0f0f1a",
    "bg_secondary": "#1a1a2e",
    "bg_tertiary": "#16213e",
    "bg_panel": "#1e2240",
    "bg_hover": "#2a2d4a",
    "bg_input": "#0d0d1a",

    # Borders
    "border": "#2a2d5a",
    "border_light": "#3a3d6a",
    "border_focus": "#00d4ff",

    # Text
    "text_primary": "#e8e8f0",
    "text_secondary": "#9090b0",
    "text_muted": "#606080",

    # Accent
    "accent": "#00d4ff",
    "accent_hover": "#33ddff",
    "accent_dark": "#0099cc",

    # Status
    "success": "#51cf66",
    "warning": "#ffd43b",
    "error": "#ff6b6b",

    # Channel colors
    "ch1": "#00d4ff",
    "ch2": "#ff6b6b",
    "ch3": "#51cf66",
    "ch4": "#be4bdb",
    "ch5": "#ffd43b",
}


def get_stylesheet() -> str:
    """Return the complete application stylesheet."""
    return f"""
    /* ===== GLOBAL ===== */
    QWidget {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
        font-family: 'Inter', 'Roboto', 'Segoe UI', 'Ubuntu', sans-serif;
        font-size: 13px;
    }}

    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}

    /* ===== FRAMES & PANELS ===== */
    QFrame {{
        border: none;
    }}

    QFrame#panel {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
    }}

    QFrame#glassPanel {{
        background-color: rgba(26, 26, 46, 220);
        border: 1px solid rgba(42, 45, 90, 150);
        border-radius: 12px;
    }}

    /* ===== LABELS ===== */
    QLabel {{
        color: {COLORS['text_primary']};
        background: transparent;
        border: none;
        padding: 0px;
    }}

    QLabel#title {{
        font-size: 22px;
        font-weight: 700;
        color: {COLORS['accent']};
    }}

    QLabel#subtitle {{
        font-size: 14px;
        font-weight: 500;
        color: {COLORS['text_secondary']};
    }}

    QLabel#sectionTitle {{
        font-size: 15px;
        font-weight: 600;
        color: {COLORS['text_primary']};
        padding: 4px 0;
    }}

    QLabel#statusConnected {{
        color: {COLORS['success']};
        font-weight: 600;
    }}

    QLabel#statusDisconnected {{
        color: {COLORS['error']};
        font-weight: 600;
    }}

    /* ===== BUTTONS ===== */
    QPushButton {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 500;
        font-size: 13px;
        min-height: 20px;
    }}

    QPushButton:hover {{
        background-color: {COLORS['bg_hover']};
        border-color: {COLORS['border_light']};
    }}

    QPushButton:pressed {{
        background-color: {COLORS['bg_input']};
    }}

    QPushButton:disabled {{
        color: {COLORS['text_muted']};
        background-color: {COLORS['bg_input']};
        border-color: {COLORS['bg_secondary']};
    }}

    QPushButton#primary {{
        background-color: {COLORS['accent_dark']};
        border-color: {COLORS['accent']};
        color: white;
        font-weight: 600;
    }}

    QPushButton#primary:hover {{
        background-color: {COLORS['accent']};
    }}

    QPushButton#danger {{
        background-color: #4a1a1a;
        border-color: {COLORS['error']};
        color: {COLORS['error']};
    }}

    QPushButton#danger:hover {{
        background-color: #6a2a2a;
    }}

    /* ===== TAB WIDGET ===== */
    QTabWidget::pane {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 10px 24px;
        margin-right: 2px;
        font-weight: 500;
        font-size: 13px;
    }}

    QTabBar::tab:selected {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['accent']};
        border-color: {COLORS['accent']};
        font-weight: 600;
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {COLORS['bg_hover']};
        color: {COLORS['text_primary']};
    }}

    /* ===== SLIDERS ===== */
    QSlider::groove:horizontal {{
        border: none;
        height: 6px;
        background-color: {COLORS['bg_input']};
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        background-color: {COLORS['accent']};
        border: 2px solid {COLORS['accent']};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 9px;
    }}

    QSlider::handle:horizontal:hover {{
        background-color: {COLORS['accent_hover']};
        border-color: {COLORS['accent_hover']};
    }}

    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLORS['accent_dark']}, stop:1 {COLORS['accent']});
        border-radius: 3px;
    }}

    /* ===== SCROLLBAR ===== */
    QScrollBar:vertical {{
        background-color: {COLORS['bg_primary']};
        width: 8px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background-color: {COLORS['border']};
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['border_light']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* ===== TOOLTIP ===== */
    QToolTip {{
        background-color: {COLORS['bg_panel']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ===== STATUS BAR ===== */
    QStatusBar {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        border-top: 1px solid {COLORS['border']};
        font-size: 12px;
        padding: 2px 8px;
    }}

    /* ===== GROUP BOX ===== */
    QGroupBox {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        margin-top: 16px;
        padding-top: 20px;
        font-weight: 600;
        font-size: 13px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        color: {COLORS['accent']};
    }}

    /* ===== SPIN BOX ===== */
    QSpinBox, QDoubleSpinBox {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 13px;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {COLORS['accent']};
    }}

    /* ===== MENU ===== */
    QMenuBar {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border-bottom: 1px solid {COLORS['border']};
        padding: 2px;
    }}

    QMenuBar::item:selected {{
        background-color: {COLORS['bg_hover']};
        border-radius: 4px;
    }}

    QMenu {{
        background-color: {COLORS['bg_panel']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 8px 24px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {COLORS['bg_hover']};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {COLORS['border']};
        margin: 4px 8px;
    }}

    /* ===== CHECKBOX ===== */
    QCheckBox {{
        color: {COLORS['text_primary']};
        spacing: 8px;
        background: transparent;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {COLORS['border']};
        border-radius: 4px;
        background-color: {COLORS['bg_input']};
    }}

    QCheckBox::indicator:checked {{
        background-color: {COLORS['accent']};
        border-color: {COLORS['accent']};
    }}

    QCheckBox::indicator:hover {{
        border-color: {COLORS['accent']};
    }}

    /* ===== SPLITTER ===== */
    QSplitter::handle {{
        background-color: {COLORS['border']};
        width: 1px;
    }}
    """
