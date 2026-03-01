"""
Main Window — assembles all widgets into the application layout.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStatusBar, QFileDialog, QMessageBox, QFrame, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from src.device_manager import TC420DeviceManager
from src.models import AppState
from src.utils.file_io import save_program, load_program
from src.widgets.toolbar import ToolBar, ModeSelector
from src.widgets.timeline_editor import TimelineEditor
from src.widgets.channel_controls import ChannelControls
from src.widgets.connection_panel import ConnectionPanel


class MainWindow(QMainWindow):
    """TC420 Controller main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TC420 Controller — LED Programmable Controller")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        # Core state
        self.app_state = AppState()
        self.device = TC420DeviceManager()
        self._current_file = None

        self._init_ui()
        self._connect_signals()
        self._update_timeline()

    def _init_ui(self):
        """Build the full UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 4)
        main_layout.setSpacing(8)

        # --- Top Toolbar ---
        self.toolbar = ToolBar()
        main_layout.addWidget(self.toolbar)

        # --- Mode Selector ---
        self.mode_selector = ModeSelector()
        main_layout.addWidget(self.mode_selector)

        # --- Main Content Area (splitter: left sidebar + center timeline) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left sidebar
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Connection panel
        self.connection_panel = ConnectionPanel(self.device)
        left_layout.addWidget(self.connection_panel)

        # Channel info section
        info_frame = QFrame()
        info_frame.setObjectName("panel")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 12, 16, 12)

        info_title = QLabel("Informations Programme")
        info_title.setObjectName("sectionTitle")
        info_layout.addWidget(info_title)

        self.program_info = QLabel("Mode 1 — 0 points définis\nAucun fichier chargé")
        self.program_info.setStyleSheet("color: #9090b0; font-size: 12px; background: transparent;")
        self.program_info.setWordWrap(True)
        info_layout.addWidget(self.program_info)
        left_layout.addWidget(info_frame)

        # Quick help
        help_frame = QFrame()
        help_frame.setObjectName("panel")
        help_layout = QVBoxLayout(help_frame)
        help_layout.setContentsMargins(16, 12, 16, 12)

        help_title = QLabel("Aide Rapide")
        help_title.setObjectName("sectionTitle")
        help_layout.addWidget(help_title)

        help_text = QLabel(
            "🖱 <b>Clic gauche</b> sur la timeline: ajouter un point\n\n"
            "✋ <b>Glisser</b> un point: modifier l'heure et la luminosité\n\n"
            "🗑 <b>Clic droit</b> sur un point: supprimer\n\n"
            "🎨 Cliquer sur un canal dans la barre du bas pour le sélectionner\n\n"
            "📤 <b>Envoyer</b>: transférer le programme vers le TC420"
        )
        help_text.setStyleSheet("color: #606080; font-size: 11px; line-height: 1.4; background: transparent;")
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.TextFormat.RichText)
        help_layout.addWidget(help_text)
        left_layout.addWidget(help_frame)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Center: Timeline + Channel controls
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        # Timeline editor (takes most space)
        self.timeline = TimelineEditor()
        center_layout.addWidget(self.timeline, 3)

        # Channel controls (bottom)
        self.channel_controls = ChannelControls()
        center_layout.addWidget(self.channel_controls)

        splitter.addWidget(center)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, 1)

        # --- Status Bar ---
        self.statusBar().setStyleSheet(
            "background-color: #1a1a2e; color: #9090b0; "
            "border-top: 1px solid #2a2d5a; padding: 4px 12px; font-size: 12px;"
        )
        self.statusBar().showMessage("Prêt — TC420 Controller v1.0")

    def _connect_signals(self):
        """Wire up all signals."""
        # Toolbar
        self.toolbar.save_clicked.connect(self._save_file)
        self.toolbar.load_clicked.connect(self._load_file)
        self.toolbar.upload_clicked.connect(self._upload_program)
        self.toolbar.download_clicked.connect(self._download_program)
        self.toolbar.demo_clicked.connect(self._run_demo)

        # Mode selector
        self.mode_selector.mode_changed.connect(self._on_mode_changed)

        # Connection
        self.connection_panel.connection_changed.connect(self._on_connection_changed)
        self.connection_panel.status_message.connect(self._show_status)

        # Channel controls
        self.channel_controls.channel_changed.connect(self._on_channel_slider_changed)

        # Timeline
        self.timeline.point_changed.connect(self._on_timeline_changed)

    def _update_timeline(self):
        """Update timeline editor with current mode's program."""
        mode = self.app_state.active_mode
        self.timeline.set_mode_program(mode)
        self._update_program_info()

    def _update_program_info(self):
        """Update the program info panel."""
        mode = self.app_state.active_mode
        total_points = sum(len(ch.points) for ch in mode.channels)
        file_info = f"Fichier: {self._current_file}" if self._current_file else "Aucun fichier chargé"
        self.program_info.setText(
            f"{mode.name} — {total_points} points définis\n{file_info}"
        )

    def _on_mode_changed(self, index: int):
        self.app_state.active_mode_index = index
        self._update_timeline()
        self._show_status(f"Mode {index + 1} sélectionné")

    def _on_connection_changed(self, connected: bool):
        self.toolbar.set_device_connected(connected)
        self.app_state.device.connected = connected

    def _on_channel_slider_changed(self, channel: int, value: int):
        if self.device.is_connected:
            success, msg = self.device.set_channel(channel, value)
            if not success:
                self._show_status(f"Erreur: {msg}")

    def _on_timeline_changed(self):
        self._update_program_info()

    def _save_file(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Sauvegarder le programme",
            "", "TC420 Programme (*.tc420);;Tous les fichiers (*)"
        )
        if filepath:
            if not filepath.endswith('.tc420'):
                filepath += '.tc420'
            if save_program(self.app_state, filepath):
                self._current_file = filepath.split('/')[-1]
                self._show_status(f"Programme sauvegardé: {self._current_file}")
                self._update_program_info()
            else:
                self._show_status("Erreur lors de la sauvegarde!")

    def _load_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un programme",
            "", "TC420 Programme (*.tc420);;JSON (*.json);;Tous les fichiers (*)"
        )
        if filepath:
            state = load_program(filepath)
            if state:
                self.app_state = state
                self._current_file = filepath.split('/')[-1]
                self._update_timeline()
                self.mode_selector.set_active_mode(state.active_mode_index)
                self._show_status(f"Programme chargé: {self._current_file}")
            else:
                QMessageBox.critical(
                    self, "Erreur",
                    "Impossible de charger le fichier. Format invalide."
                )

    def _upload_program(self):
        if not self.device.is_connected:
            self._show_status("Aucun appareil connecté!")
            return

        reply = QMessageBox.question(
            self, "Envoyer le programme",
            f"Envoyer le programme actuel (Mode {self.app_state.active_mode_index + 1}) vers le TC420?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            mode = self.app_state.active_mode
            success, msg = self.device.upload_program(
                self.app_state.active_mode_index, mode
            )
            self._show_status(msg)

            if success:
                # Also set the active mode on device
                self.device.set_active_mode(self.app_state.active_mode_index)

    def _download_program(self):
        self._show_status("Lecture du programme en cours... (simulation)")

    def _run_demo(self):
        """Run a quick demo on the channel sliders."""
        self._show_status("Démo en cours...")
        import random
        for i in range(5):
            val = random.randint(20, 100)
            self.channel_controls.set_channel_value(i, val)
            if self.device.is_connected:
                self.device.set_channel(i, val)
        QTimer.singleShot(3000, lambda: self._show_status("Démo terminée"))

    def _show_status(self, message: str):
        self.statusBar().showMessage(message, 5000)
