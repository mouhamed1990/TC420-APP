"""
Main Window — assembles all widgets into the application layout.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStatusBar, QFileDialog, QMessageBox, QFrame, QLabel,
    QDialog, QListWidget, QDialogButtonBox, QAbstractItemView,
    QProgressDialog, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from src.device_manager import TC420DeviceManager
from src.models import AppState, NUM_MODES
from src.utils.file_io import save_program, load_program, load_xml_mode_names, load_xml_program
from src.utils.upload_log import log_upload
from src.widgets.toolbar import ToolBar, ModeSelector
from src.widgets.timeline_editor import TimelineEditor
from src.widgets.channel_controls import ChannelControls
from src.widgets.connection_panel import ConnectionPanel
from src.widgets.log_panel import LogPanel


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

        # Center: Tabs (Timeline | Log) + Channel controls
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background: #16213e;
                color: #9090b0;
                border: 1px solid #2a2d5a;
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 6px 18px;
                font-size: 13px;
                font-weight: 600;
                min-width: 140px;
            }
            QTabBar::tab:selected {
                background: #1a1a2e;
                color: #00d4ff;
                border-bottom: 2px solid #00d4ff;
            }
            QTabBar::tab:hover:!selected {
                background: #1e2040;
                color: #e8e8f0;
            }
        """)

        # Tab 1 — Timeline
        timeline_tab = QWidget()
        tl_layout = QVBoxLayout(timeline_tab)
        tl_layout.setContentsMargins(0, 0, 0, 0)
        tl_layout.setSpacing(0)
        self.timeline = TimelineEditor()
        tl_layout.addWidget(self.timeline)
        self.tabs.addTab(timeline_tab, "📈  Timeline")

        # Tab 2 — Upload Log
        self.log_panel = LogPanel()
        self.tabs.addTab(self.log_panel, "📋  Historique")

        center_layout.addWidget(self.tabs, 3)

        # Channel controls (always visible below tabs)
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
        # Update combo box labels
        mode_names = [m.name for m in self.app_state.modes]
        self.mode_selector.populate_modes(mode_names)
        
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
            "",
            "Tous les programmes supportés (*.tc420 *.xml *.json);;"
            "TC420 Programme (*.tc420);;"
            "XML PLED (*.xml);;"
            "JSON (*.json);;"
            "Tous les fichiers (*)"
        )
        if not filepath:
            return

        if filepath.lower().endswith('.xml'):
            self._load_xml_file(filepath)
        else:
            state = load_program(filepath)
            if state:
                self._apply_loaded_state(state, filepath)
            else:
                QMessageBox.critical(
                    self, "Erreur",
                    "Impossible de charger le fichier. Format invalide."
                )

    def _load_xml_file(self, filepath: str):
        """Load an XML PLED file with mode selection dialog."""
        mode_names = load_xml_mode_names(filepath)
        if not mode_names:
            QMessageBox.critical(
                self, "Erreur",
                "Impossible de lire le fichier XML ou aucun mode trouvé."
            )
            return

        # Show mode selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Sélectionner les modes à importer")
        dialog.setMinimumSize(400, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: #e8e8f0;
            }
            QLabel {
                color: #e8e8f0;
                font-size: 13px;
                background: transparent;
            }
            QListWidget {
                background-color: #16213e;
                color: #e8e8f0;
                border: 1px solid #2a2d5a;
                border-radius: 6px;
                padding: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #0099cc;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #2a2d4a;
            }
            QPushButton {
                background-color: #0099cc;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #00b8e6;
            }
            QPushButton:disabled {
                background-color: #2a2d5a;
                color: #606080;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        info_label = QLabel(
            f"Le fichier contient {len(mode_names)} modes.\n"
            f"Sélectionnez jusqu'à {NUM_MODES} modes à charger (Ctrl+clic pour multi-sélection):"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        mode_list = QListWidget()
        mode_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for i, name in enumerate(mode_names):
            mode_list.addItem(f"{i+1}. {name}")
        layout.addWidget(mode_list)

        warn_label = QLabel("")
        warn_label.setStyleSheet("color: #ff6b6b; font-size: 12px; background: transparent;")
        layout.addWidget(warn_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Importer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def on_selection_changed():
            count = len(mode_list.selectedItems())
            if count > NUM_MODES:
                warn_label.setText(f"⚠ Maximum {NUM_MODES} modes ! Seuls les {NUM_MODES} premiers seront importés.")
            elif count == 0:
                warn_label.setText("")
            else:
                warn_label.setText(f"✓ {count} mode(s) sélectionné(s)")
                warn_label.setStyleSheet("color: #51cf66; font-size: 12px; background: transparent;")

        mode_list.itemSelectionChanged.connect(on_selection_changed)

        # Pre-select first mode
        if mode_names:
            mode_list.item(0).setSelected(True)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected = [mode_list.row(item) for item in mode_list.selectedItems()]
        if not selected:
            return

        state = load_xml_program(filepath, selected[:NUM_MODES])
        if state:
            self._apply_loaded_state(state, filepath)
        else:
            QMessageBox.critical(
                self, "Erreur",
                "Erreur lors de l'import du fichier XML."
            )

    def _apply_loaded_state(self, state: AppState, filepath: str):
        """Apply a loaded state to the app."""
        self.app_state = state
        self._current_file = filepath.split('/')[-1]
        self._update_timeline()
        self.mode_selector.set_active_mode(state.active_mode_index)
        self._show_status(f"Programme chargé: {self._current_file}")

    def _upload_program(self):
        if not self.device.is_connected:
            self._show_status("Aucun appareil connecté!")
            return

        # Ask which modes to send
        non_empty = [
            (i, m) for i, m in enumerate(self.app_state.modes)
            if any(len(ch.points) > 0 for ch in m.channels)
        ]

        if not non_empty:
            # Switch to timeline tab so user can see where to add points
            self.tabs.setCurrentIndex(0)
            QMessageBox.information(
                self, "Aucun programme à envoyer",
                "📭  Aucun mode ne contient de points de contrôle.\n\n"
                "Pour envoyer un programme au TC420, vous devez d'abord :\n\n"
                "  1️⃣  Charger un fichier XML (📂 Ouvrir → fichier .xml)\n"
                "       — ou —\n"
                "  2️⃣  Créer un programme manuellement :\n"
                "       • Sélectionnez un Mode dans la liste déroulante\n"
                "       • Cliquez sur la timeline pour ajouter des points\n"
                "       • Répétez pour chaque mode / journée souhaité(e)\n\n"
                "💾  Pensez à sauvegarder vos programmes (💾 Sauvegarder) !"
            )
            return

        # Confirm
        mode_list_str = "\n".join(
            f"  • Mode {i+1}: {m.name}" for i, m in non_empty
        )
        reply = QMessageBox.question(
            self, "Envoyer les programmes",
            f"Envoyer {len(non_empty)} mode(s) vers le TC420 ?\n\n{mode_list_str}\n\n"
            f"⚠️  Cela effacera TOUS les programmes existants sur l'appareil.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Progress dialog
        progress = QProgressDialog("Envoi en cours…", None, 0, 100, self)
        progress.setWindowTitle("TC420 — Envoi du programme")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()

        def on_progress(done, total, label):
            pct = int(done / max(total, 1) * 100)
            progress.setLabelText(label)
            progress.setValue(pct)
            from PyQt6.QtCore import QCoreApplication
            QCoreApplication.processEvents()

        modes_to_send = [m for _, m in non_empty]
        success, msg = self.device.upload_program(modes_to_send, progress_cb=on_progress)
        progress.close()

        # ── log the result ──────────────────────────────────────────────────
        batch_name = ", ".join(m.name[:12] for m in modes_to_send[:3])
        if len(modes_to_send) > 3:
            batch_name += f" +{len(modes_to_send)-3}"
        entry = log_upload(
            mode_name=batch_name,
            success=success,
            message=msg,
            n_modes=len(modes_to_send),
        )
        self.log_panel.add_entry_live(entry)
        # Switch to log tab so user sees the result
        self.tabs.setCurrentIndex(1)
        # ────────────────────────────────────────────────────────────────────

        if success:
            QMessageBox.information(self, "Succès", msg)
            self._show_status(msg)
        else:
            QMessageBox.critical(self, "Erreur", msg)
            self._show_status(f"Erreur: {msg}")

    def _download_program(self):
        """TC420 does not support reading programs back via USB."""
        QMessageBox.information(
            self,
            "Lecture non supportée",
            "Le TC420 ne supporte pas la lecture des programmes via USB.\n\n"
            "L'appareil est en écriture seule : vous pouvez envoyer des programmes "
            "vers le TC420, mais il n'est pas possible de les relire depuis le PC.\n\n"
            "💡 Conseil : sauvegardez vos programmes dans l'application "
            "(💾 Sauvegarder) pour les conserver et les recharger ultérieurement."
        )
        self._show_status("Lecture non supportée par le TC420")

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
