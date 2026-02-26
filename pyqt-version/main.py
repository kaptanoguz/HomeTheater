#!/usr/bin/env python3
"""
Home Theater — Native Desktop Application
A local movie & TV series catalog and media player.
Built with PyQt5.
"""

import sys
import os
import random
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QLabel, QPushButton, QLineEdit,
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QMessageBox,
    QStatusBar, QFrame, QSizePolicy, QTabBar, QListWidget,
    QListWidgetItem, QSplitter, QFileDialog, QAction, QToolBar,
    QSpacerItem
)
from PyQt5.QtCore import (
    Qt, QSize, QTimer, pyqtSignal, QThread, QUrl
)
from PyQt5.QtGui import (
    QPixmap, QIcon, QFont, QPalette, QColor, QCursor,
    QPainter, QFontDatabase
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

from backend import Config, Cache, Scanner, get_poster_path, find_local_subtitle


# --- Dark Theme Stylesheet ---
DARK_STYLE = """
QMainWindow, QDialog {
    background-color: #0a0a0a;
    color: #ffffff;
}
QWidget {
    color: #ffffff;
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 13px;
}
QToolBar {
    background: rgba(0,0,0,0.95);
    border-bottom: 1px solid #333;
    padding: 8px 15px;
    spacing: 10px;
}
QLineEdit {
    background: #1f1f1f;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 8px 15px;
    color: white;
    font-size: 14px;
}
QLineEdit:focus {
    border-color: #e50914;
    background: #2a2a2a;
}
QComboBox {
    background: #1f1f1f;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 6px 12px;
    color: #ccc;
    min-width: 130px;
}
QComboBox:hover {
    border-color: #e50914;
    color: white;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background: #1f1f1f;
    border: 1px solid #444;
    color: white;
    selection-background-color: #e50914;
}
QPushButton {
    background: #333;
    color: #ddd;
    border: 1px solid #555;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background: #ddd;
    color: black;
}
QPushButton#primaryBtn {
    background: #e50914;
    border-color: #e50914;
    color: white;
}
QPushButton#primaryBtn:hover {
    background: #ff1a25;
}
QPushButton#shuffleBtn {
    background: #e50914;
    border-color: #e50914;
    color: white;
    font-size: 14px;
    padding: 8px 18px;
}
QPushButton#shuffleBtn:hover {
    background: #ff1a25;
}
QTabBar::tab {
    background: #1f1f1f;
    color: #aaa;
    border: 1px solid #333;
    border-radius: 15px;
    padding: 6px 18px;
    margin-right: 8px;
    font-weight: bold;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: #e50914;
    color: white;
    border-color: #e50914;
}
QTabBar::tab:hover {
    background: #e50914;
    color: white;
}
QScrollArea {
    background: #0a0a0a;
    border: none;
}
QStatusBar {
    background: #111;
    color: #888;
    border-top: 1px solid #222;
    font-size: 12px;
}
QLabel#logo {
    color: #e50914;
    font-size: 22px;
    font-weight: 900;
    letter-spacing: 1px;
}
QFrame#filterBar {
    background: #111;
    border-bottom: 1px solid #222;
}
QDialog {
    background: #141414;
}
QListWidget {
    background: #111;
    border: none;
    border-right: 1px solid #222;
    color: #888;
    font-weight: bold;
    font-size: 13px;
}
QListWidget::item {
    padding: 12px 15px;
    border-bottom: 1px solid #222;
}
QListWidget::item:selected {
    background: #1f1f1f;
    color: #e50914;
    border-left: 3px solid #e50914;
}
QListWidget::item:hover {
    background: #1a1a1a;
    color: white;
}
"""


class MovieCard(QFrame):
    """A clickable movie poster card with rating and year badges."""
    clicked = pyqtSignal(dict)
    fav_toggled = pyqtSignal(dict)

    def __init__(self, item, is_fav=False, parent=None):
        super().__init__(parent)
        self.item = item
        self.is_fav = is_fav
        self.setFixedSize(170, 255)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet("""
            MovieCard {
                background: #141414;
                border-radius: 8px;
                border: 2px solid transparent;
            }
            MovieCard:hover {
                border: 2px solid #e50914;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Poster
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(170, 220)
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setStyleSheet("""
            background: #222;
            border-radius: 8px 8px 0 0;
        """)
        self.poster_label.setScaledContents(True)

        poster_path = get_poster_path(item)
        if poster_path and os.path.exists(poster_path):
            pix = QPixmap(poster_path)
            if not pix.isNull():
                self.poster_label.setPixmap(pix)
            else:
                self.poster_label.setText(item.get('title', '?')[:20])
        else:
            self.poster_label.setText(item.get('title', '?')[:20])
            self.poster_label.setWordWrap(True)
            self.poster_label.setStyleSheet("""
                background: #222; color: #666;
                font-size: 11px; font-weight: bold;
                border-radius: 8px 8px 0 0;
                padding: 10px;
            """)

        layout.addWidget(self.poster_label)

        # Title bar
        title_frame = QFrame()
        title_frame.setFixedHeight(35)
        title_frame.setStyleSheet("background: #1a1a1a; border-radius: 0 0 8px 8px;")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(8, 0, 8, 0)

        title = item.get('title', 'Unknown')
        title_label = QLabel(title if len(title) <= 18 else title[:16] + '…')
        title_label.setStyleSheet("color: #ccc; font-size: 11px; font-weight: bold;")
        title_layout.addWidget(title_label)

        rating = item.get('rating', '')
        if rating and rating != 'N/A':
            rating_label = QLabel(f"⭐ {rating}")
            rating_label.setStyleSheet("color: #FFD700; font-size: 10px; font-weight: bold;")
            title_layout.addWidget(rating_label)

        layout.addWidget(title_frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.item)
        super().mousePressEvent(event)


class FlowLayout(QGridLayout):
    """A grid layout that auto-adjusts columns based on available width."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSpacing(20)
        self._items = []

    def add_card(self, widget):
        self._items.append(widget)

    def reflow(self, width):
        # Clear layout
        while self.count():
            item = self.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if not self._items:
            return

        card_width = 190  # 170 + spacing
        cols = max(1, width // card_width)

        for i, widget in enumerate(self._items):
            row = i // cols
            col = i % cols
            self.addWidget(widget, row, col, Qt.AlignTop | Qt.AlignLeft)

    def clear_items(self):
        self._items.clear()
        while self.count():
            item = self.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()


class ScanWorker(QThread):
    """Worker thread for scanning."""
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, config, cache):
        super().__init__()
        self.config = config
        self.cache = cache

    def run(self):
        scanner = Scanner(self.config, self.cache, callback=lambda: self.finished.emit())
        scanner.run()
        self.finished.emit()


class SettingsDialog(QDialog):
    """Settings/Setup dialog."""

    def __init__(self, config, title="Settings", parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QDialog { background: #141414; }
            QLabel { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
            QLineEdit { margin-bottom: 10px; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        header = QLabel(f"⚙️ {title}")
        header.setStyleSheet("color: white; font-size: 20px; font-weight: bold; text-transform: none; margin-bottom: 15px;")
        layout.addWidget(header)

        layout.addWidget(QLabel("MOVIES DIRECTORY"))
        self.movie_edit = QLineEdit(config.get("movie_dir"))
        self.movie_edit.setPlaceholderText("/home/user/Movies")
        movie_row = QHBoxLayout()
        movie_row.addWidget(self.movie_edit)
        browse_movie = QPushButton("📂")
        browse_movie.setFixedWidth(40)
        browse_movie.clicked.connect(lambda: self._browse(self.movie_edit))
        movie_row.addWidget(browse_movie)
        layout.addLayout(movie_row)

        layout.addWidget(QLabel("TV SERIES DIRECTORY"))
        self.series_edit = QLineEdit(config.get("series_dir"))
        self.series_edit.setPlaceholderText("/home/user/Series")
        series_row = QHBoxLayout()
        series_row.addWidget(self.series_edit)
        browse_series = QPushButton("📂")
        browse_series.setFixedWidth(40)
        browse_series.clicked.connect(lambda: self._browse(self.series_edit))
        series_row.addWidget(browse_series)
        layout.addLayout(series_row)

        layout.addWidget(QLabel("OMDB API KEY (for posters & metadata)"))
        self.omdb_edit = QLineEdit(config.get("omdb_api_key"))
        self.omdb_edit.setPlaceholderText("Get free key at omdbapi.com")
        layout.addWidget(self.omdb_edit)

        layout.addWidget(QLabel("OPENSUBTITLES API KEY (optional)"))
        self.osub_edit = QLineEdit(config.get("opensubtitles_api_key"))
        self.osub_edit.setPlaceholderText("Get free key at opensubtitles.com")
        layout.addWidget(self.osub_edit)

        layout.addSpacing(15)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save & Scan")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.save_and_accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _browse(self, line_edit):
        d = QFileDialog.getExistingDirectory(self, "Select Directory")
        if d:
            line_edit.setText(d)

    def save_and_accept(self):
        self.config.update({
            "movie_dir": self.movie_edit.text(),
            "series_dir": self.series_edit.text(),
            "omdb_api_key": self.omdb_edit.text(),
            "opensubtitles_api_key": self.osub_edit.text()
        })
        self.accept()


class SeriesDialog(QDialog):
    """Dialog for browsing a TV series seasons and episodes."""
    play_episode = pyqtSignal(dict)

    def __init__(self, series_data, parent=None):
        super().__init__(parent)
        self.series_data = series_data
        self.setWindowTitle(series_data.get('meta', {}).get('title', 'Series'))
        self.setMinimumSize(900, 600)
        self.setStyleSheet("QDialog { background: #141414; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Hero section
        hero = QFrame()
        hero.setFixedHeight(200)
        hero.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #141414, stop:0.6 #1a1a2e, stop:1 #0a0a0a);
                border-bottom: 1px solid #333;
            }
        """)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(30, 20, 30, 20)

        # Poster
        meta = series_data.get('meta', {})
        poster_path = get_poster_path(meta) if meta else ''
        poster_label = QLabel()
        poster_label.setFixedSize(120, 170)
        poster_label.setScaledContents(True)
        poster_label.setStyleSheet("border-radius: 6px; border: 1px solid #444;")
        if poster_path and os.path.exists(poster_path):
            poster_label.setPixmap(QPixmap(poster_path))
        else:
            poster_label.setText(meta.get('title', ''))
            poster_label.setAlignment(Qt.AlignCenter)
            poster_label.setStyleSheet("background: #222; border-radius: 6px; color: #666;")
        hero_layout.addWidget(poster_label)

        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        title_label = QLabel(meta.get('title', ''))
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        info_layout.addWidget(title_label)

        meta_text = []
        if meta.get('rating') and meta['rating'] != 'N/A':
            meta_text.append(f"⭐ {meta['rating']}")
        if meta.get('year'):
            meta_text.append(meta['year'])
        if meta.get('genre'):
            meta_text.append(meta['genre'])

        if meta_text:
            meta_label = QLabel(" · ".join(meta_text))
            meta_label.setStyleSheet("color: #46d369; font-size: 14px; font-weight: bold;")
            info_layout.addWidget(meta_label)

        if meta.get('plot'):
            plot = QLabel(meta['plot'])
            plot.setWordWrap(True)
            plot.setStyleSheet("color: #bbb; font-size: 13px; line-height: 1.5;")
            plot.setMaximumWidth(500)
            info_layout.addWidget(plot)

        info_layout.addStretch()
        hero_layout.addLayout(info_layout)
        hero_layout.addStretch()
        main_layout.addWidget(hero)

        # Content: seasons + episodes
        content = QSplitter(Qt.Horizontal)
        content.setStyleSheet("QSplitter { background: #141414; border: none; }")

        # Season list
        self.season_list = QListWidget()
        self.season_list.setFixedWidth(160)
        seasons = sorted(series_data.get('seasons', {}).keys(), key=lambda x: int(x))
        for s in seasons:
            self.season_list.addItem(f"Season {s}")
        self.season_list.currentRowChanged.connect(self._show_season)
        content.addWidget(self.season_list)

        # Episode list
        self.episode_list = QListWidget()
        self.episode_list.setStyleSheet("""
            QListWidget { background: #141414; border: none; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #222; color: #ddd; font-size: 13px; }
            QListWidget::item:hover { background: #1f1f1f; color: white; }
            QListWidget::item:selected { background: #1f1f1f; color: #e50914; }
        """)
        self.episode_list.itemDoubleClicked.connect(self._play_episode)
        content.addWidget(self.episode_list)

        content.setStretchFactor(0, 0)
        content.setStretchFactor(1, 1)
        main_layout.addWidget(content)

        # Show first season
        if seasons:
            self.season_list.setCurrentRow(0)

    def _show_season(self, row):
        self.episode_list.clear()
        seasons = sorted(self.series_data.get('seasons', {}).keys(), key=lambda x: int(x))
        if row < 0 or row >= len(seasons):
            return
        season_key = seasons[row]
        episodes = self.series_data['seasons'][season_key]
        episodes.sort(key=lambda ep: ep.get('episode', 0))
        for ep in episodes:
            text = f"  E{ep['episode']:02d}  —  {ep.get('filename', ep.get('title', ''))}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ep)
            self.episode_list.addItem(item)

    def _play_episode(self, item):
        ep = item.data(Qt.UserRole)
        if ep:
            self.play_episode.emit(ep)


class PlayerWindow(QDialog):
    """Video player window using system media player."""

    def __init__(self, video_path, title="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or "Home Theater Player")
        self.setMinimumSize(960, 540)
        self.video_path = video_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Use QMediaPlayer with QVideoWidget
        self.video_widget = QVideoWidget()
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget)

        # Controls
        ctrl = QHBoxLayout()
        ctrl.setContentsMargins(10, 5, 10, 5)

        self.play_btn = QPushButton("⏸")
        self.play_btn.setFixedWidth(40)
        self.play_btn.clicked.connect(self.toggle_play)
        ctrl.addWidget(self.play_btn)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #888; font-size: 12px;")
        ctrl.addWidget(self.time_label)

        ctrl.addStretch()

        close_btn = QPushButton("✕ Close")
        close_btn.setObjectName("primaryBtn")
        close_btn.clicked.connect(self.close)
        ctrl.addWidget(close_btn)

        layout.addLayout(ctrl)

        # Timer for position updates
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._update_time)

        # Start playback
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        self.player.play()
        self.timer.start()

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_btn.setText("▶")
        else:
            self.player.play()
            self.play_btn.setText("⏸")

    def _update_time(self):
        pos = self.player.position() // 1000
        dur = self.player.duration() // 1000
        self.time_label.setText(
            f"{pos//60:02d}:{pos%60:02d} / {dur//60:02d}:{dur%60:02d}"
        )

    def closeEvent(self, event):
        self.timer.stop()
        self.player.stop()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Home Theater")
        self.setMinimumSize(1200, 700)

        self.config = Config()
        self.cache = Cache()
        self.favorites = self._load_favorites()
        self.active_category = 'all'
        self.current_items = []
        self.scan_worker = None

        self._setup_ui()

        # First-run setup
        if self.config.needs_setup:
            QTimer.singleShot(300, self._show_setup)
        else:
            self._start_scan()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Toolbar / Header ---
        header = QFrame()
        header.setFixedHeight(65)
        header.setStyleSheet("""
            QFrame { background: rgba(0,0,0,0.95); border-bottom: 1px solid #333; }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 0, 25, 0)

        logo = QLabel("🍿 Home Theater")
        logo.setObjectName("logo")
        logo.setCursor(QCursor(Qt.PointingHandCursor))
        logo.mousePressEvent = lambda e: self._refresh()
        header_layout.addWidget(logo)

        header_layout.addSpacing(20)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(self._apply_filters)
        header_layout.addWidget(self.search_input)

        header_layout.addStretch()

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "📅 Recently Added", "⭐ Highest Rated",
            "🔤 Name A-Z", "📅 Year (Newest)", "📅 Year (Oldest)"
        ])
        self.sort_combo.currentIndexChanged.connect(self._apply_filters)
        header_layout.addWidget(self.sort_combo)

        header_layout.addSpacing(10)

        self.genre_combo = QComboBox()
        self.genre_combo.addItem("All Genres", "all")
        self.genre_combo.currentIndexChanged.connect(self._apply_filters)
        header_layout.addWidget(self.genre_combo)

        header_layout.addSpacing(10)

        shuffle_btn = QPushButton("🎲 Shuffle")
        shuffle_btn.setObjectName("shuffleBtn")
        shuffle_btn.clicked.connect(self._random_movie)
        header_layout.addWidget(shuffle_btn)

        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedWidth(40)
        settings_btn.clicked.connect(self._show_settings)
        header_layout.addWidget(settings_btn)

        main_layout.addWidget(header)

        # --- Category tabs ---
        tab_frame = QFrame()
        tab_frame.setObjectName("filterBar")
        tab_frame.setFixedHeight(50)
        tab_layout = QHBoxLayout(tab_frame)
        tab_layout.setContentsMargins(25, 5, 25, 5)

        self.tab_bar = QTabBar()
        self.tab_bar.setExpanding(False)
        self.tab_bar.addTab("All")
        self.tab_bar.addTab("Movies")
        self.tab_bar.addTab("TV Series")
        self.tab_bar.addTab("❤️ Favorites")
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        tab_layout.addWidget(self.tab_bar)

        tab_layout.addStretch()

        self.count_label = QLabel("0 Items")
        self.count_label.setStyleSheet("color: #666; font-size: 13px; font-weight: bold;")
        tab_layout.addWidget(self.count_label)

        main_layout.addWidget(tab_frame)

        # --- Movie grid ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.grid_widget = QWidget()
        self.grid_layout = FlowLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(30, 20, 30, 20)
        self.scroll_area.setWidget(self.grid_widget)

        main_layout.addWidget(self.scroll_area)

        # --- Status bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.scroll_area.viewport().width() - 60
        self.grid_layout.reflow(w)

    def _show_setup(self):
        dlg = SettingsDialog(self.config, title="Welcome to Home Theater", parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._start_scan()

    def _show_settings(self):
        dlg = SettingsDialog(self.config, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._start_scan()

    def _start_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            return
        self.status_bar.showMessage("🔍 Scanning directories...")
        self.scan_worker = ScanWorker(self.config, self.cache)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.start()

    def _on_scan_finished(self):
        self.status_bar.showMessage("✅ Scan complete", 3000)
        self._populate_genres()
        self._apply_filters()

    def _populate_genres(self):
        genres = set()
        for m in self.cache.movies:
            g = m.get('genre', '')
            if g and g != 'N/A':
                for part in g.split(','):
                    genres.add(part.strip())
        for s in self.cache.series.values():
            g = s.get('genre', '') or (s.get('meta', {}).get('genre', ''))
            if g and g != 'N/A':
                for part in g.split(','):
                    genres.add(part.strip())

        current = self.genre_combo.currentData()
        self.genre_combo.clear()
        self.genre_combo.addItem("All Genres", "all")
        for g in sorted(genres):
            self.genre_combo.addItem(g, g)
        if current:
            idx = self.genre_combo.findData(current)
            if idx >= 0:
                self.genre_combo.setCurrentIndex(idx)

    def _on_tab_changed(self, idx):
        cats = ['all', 'movies', 'series', 'fav']
        self.active_category = cats[idx] if idx < len(cats) else 'all'
        self._apply_filters()

    def _apply_filters(self):
        search = self.search_input.text().lower()
        sort_idx = self.sort_combo.currentIndex()
        genre = self.genre_combo.currentData() or 'all'

        items = []

        # Collect items
        if self.active_category != 'series':
            for m in self.cache.movies:
                items.append({**m, '_type': 'movie'})

        if self.active_category != 'movies':
            for name, s in self.cache.series.items():
                meta = s.get('meta', {})
                items.append({
                    'id': name, 'title': meta.get('title', name),
                    'poster': meta.get('poster', ''),
                    'rating': meta.get('rating', ''),
                    'year': meta.get('year', ''),
                    'genre': meta.get('genre', ''),
                    'plot': meta.get('plot', ''),
                    '_type': 'series', '_data': s
                })

        # Filter
        filtered = []
        for item in items:
            if self.active_category == 'fav':
                fav_id = f"{'s' if item['_type'] == 'series' else 'm'}_{item['id']}"
                if fav_id not in self.favorites:
                    continue

            text = f"{item.get('title', '')} {item.get('plot', '')}".lower()
            if search and search not in text:
                continue

            if genre != 'all':
                ig = item.get('genre', '')
                if not ig or genre not in ig:
                    continue

            filtered.append(item)

        # Sort
        if sort_idx == 1:  # Rating
            filtered.sort(key=lambda x: float(x.get('rating', 0) or 0), reverse=True)
        elif sort_idx == 2:  # Name A-Z
            filtered.sort(key=lambda x: x.get('title', '').lower())
        elif sort_idx == 3:  # Year newest
            filtered.sort(key=lambda x: int(x.get('year', 0) or 0), reverse=True)
        elif sort_idx == 4:  # Year oldest
            filtered.sort(key=lambda x: int(x.get('year', 0) or 0))

        self.current_items = filtered
        self._render_grid()

    def _render_grid(self):
        self.grid_layout.clear_items()
        self.count_label.setText(f"{len(self.current_items)} Items")

        for item in self.current_items:
            fav_id = f"{'s' if item.get('_type') == 'series' else 'm'}_{item['id']}"
            is_fav = fav_id in self.favorites
            card = MovieCard(item, is_fav)
            card.clicked.connect(self._on_card_clicked)
            self.grid_layout.add_card(card)

        w = self.scroll_area.viewport().width() - 60
        self.grid_layout.reflow(w)

    def _on_card_clicked(self, item):
        if item.get('_type') == 'series':
            data = item.get('_data', {})
            dlg = SeriesDialog(data, parent=self)
            dlg.play_episode.connect(self._play_video)
            dlg.exec_()
        else:
            self._play_video(item)

    def _play_video(self, item):
        path = item.get('path', '')
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error", f"File not found:\n{path}")
            return

        title = item.get('title', item.get('filename', 'Video'))

        # Try native Qt player first
        try:
            dlg = PlayerWindow(path, title, parent=self)
            dlg.showMaximized()
            dlg.exec_()
        except Exception:
            # Fallback: open with system default player
            try:
                subprocess.Popen(['xdg-open', path])
            except Exception:
                QMessageBox.warning(self, "Error", "Could not open video player.")

    def _random_movie(self):
        movies = self.cache.movies
        if not movies:
            return
        m = random.choice(movies)
        self.status_bar.showMessage(f"🎲 Random pick: {m.get('title', '')}", 3000)
        self._play_video(m)

    def _refresh(self):
        self.search_input.clear()
        self.sort_combo.setCurrentIndex(0)
        self.genre_combo.setCurrentIndex(0)
        self.tab_bar.setCurrentIndex(0)
        self._start_scan()

    # --- Favorites ---
    def _load_favorites(self):
        fav_file = os.path.join(Config().get("movie_dir") or os.path.expanduser("~"), ".ht_favorites.json")
        # Use data dir instead
        fav_file = os.path.join(get_data_dir(), "favorites.json")
        try:
            with open(fav_file, 'r') as f:
                return set(json.load(f))
        except Exception:
            return set()

    def _save_favorites(self):
        fav_file = os.path.join(get_data_dir(), "favorites.json")
        try:
            with open(fav_file, 'w') as f:
                json.dump(list(self.favorites), f)
        except Exception:
            pass


def get_data_dir():
    d = os.path.join(os.path.expanduser("~"), ".home-theater")
    os.makedirs(d, exist_ok=True)
    return d


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Home Theater")
    app.setOrganizationName("kaptanoguz")
    app.setStyleSheet(DARK_STYLE)

    # Set app icon
    app.setWindowIcon(QIcon.fromTheme("video-display"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
