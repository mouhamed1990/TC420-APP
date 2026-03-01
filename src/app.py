"""
QApplication setup — applies global theme, fonts, and launches the main window.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtCore import Qt

from src.utils.theme import get_stylesheet
from src.main_window import MainWindow


def create_app():
    """Create and configure the QApplication."""
    app = QApplication(sys.argv)

    # Application metadata
    app.setApplicationName("TC420 Controller")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("TC420App")

    # Load fonts
    for font_family in ["Inter", "Roboto", "Ubuntu"]:
        QFontDatabase.families()  # Trigger font database loading

    # Set default font
    default_font = QFont("Inter", 11)
    default_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(default_font)

    # Apply dark theme
    app.setStyleSheet(get_stylesheet())

    return app


def run():
    """Run the application."""
    app = create_app()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
