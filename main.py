import os
import sys
import re
import threading
import shutil
import subprocess
import urllib.request
import zipfile
import tempfile
from typing import Any, cast
from PyQt6 import QtWidgets, QtGui, QtCore
import yt_dlp

# Minimal translation dict
_TRANSLATIONS = {
    'tr': {
        'title': 'EasyDownload',
        'platform': 'Platform',
        'url': 'URL',
        'mode': 'Mod',
        'single': 'Tekli',
        'playlist': 'Playlist',
        'format': 'Format',
        'mp3': 'MP3',
        'mp4': 'MP4',
        'flac': 'FLAC',
        'quality_audio': 'Ses Kalitesi',
        'quality_flac': 'Kayıpsız',
        'quality_video': 'Görüntü Kalitesi',
        'download_location': 'İndirme Konumu',
        'choose_location': 'Göz At',
        'download': '⬇  İndir',
        'ffmpeg_downloading': 'FFmpeg indiriliyor...',
        'ffmpeg_installed': 'Hazır',
        'ffmpeg_failed': 'FFmpeg indirilemedi.',
        'help': '?',
        'guide_title': 'Kılavuz',
        'guide_text': (
            'EasyDownload Kılavuz:\n\n'
            '• FFmpeg yüklü değilse uygulama otomatik indirir.\n'
            '• YouTube Mix linki girerseniz sadece ilk şarkı indirilir.\n'
            '• FLAC seçeneği kayıpsız ses çıktısı üretir.\n'
            '• Playlist modu aktifken tüm liste indirilir.\n'
            '• İndirmeler büyük olabilir; sabırlı olun.'
        ),
        'dark': '🌙',
        'light': '☀️',
        'download_complete': 'İndirme tamamlandı!',
        'error': 'Hata',
        'info': 'Bilgi',
        'success': 'Başarılı',
        'mix_detected': 'Mix linki algılandı – sadece ilk şarkı indirilecek.',
        'downloading': 'İndiriliyor...',
        'url_placeholder': 'YouTube, Instagram, TikTok linkini yapıştırın...',
        'dir_placeholder': 'İndirme klasörü seçin veya yazın...',
    },
    'en': {
        'title': 'EasyDownload',
        'platform': 'Platform',
        'url': 'URL',
        'mode': 'Mode',
        'single': 'Single',
        'playlist': 'Playlist',
        'format': 'Format',
        'mp3': 'MP3',
        'mp4': 'MP4',
        'flac': 'FLAC',
        'quality_audio': 'Audio Quality',
        'quality_flac': 'Lossless',
        'quality_video': 'Video Quality',
        'download_location': 'Download Location',
        'choose_location': 'Browse',
        'download': '⬇  Download',
        'ffmpeg_downloading': 'Downloading FFmpeg...',
        'ffmpeg_installed': 'Ready',
        'ffmpeg_failed': 'FFmpeg download failed.',
        'help': '?',
        'guide_title': 'Guide',
        'guide_text': (
            'EasyDownload Guide:\n\n'
            '• If FFmpeg is not installed, the app will download it automatically.\n'
            '• YouTube Mix links will only download the first song.\n'
            '• FLAC option produces lossless audio output.\n'
            '• Playlist mode downloads the entire list.\n'
            '• Downloads can be large; be patient.'
        ),
        'dark': '🌙',
        'light': '☀️',
        'download_complete': 'Download complete!',
        'error': 'Error',
        'info': 'Info',
        'success': 'Success',
        'mix_detected': 'Mix link detected – only the first song will be downloaded.',
        'downloading': 'Downloading...',
        'url_placeholder': 'Paste YouTube, Instagram, TikTok link...',
        'dir_placeholder': 'Choose or type download folder...',
    }
}

# ---------- Mix URL helpers ----------
_MIX_LIST_RE = re.compile(r'[?&]list=(RD[A-Za-z0-9_-]+)')


def _is_youtube_mix(url: str) -> bool:
    """Return True if the URL contains a YouTube Mix playlist id (starts with RD)."""
    return bool(_MIX_LIST_RE.search(url))


def _extract_single_video_url(url: str) -> str:
    """Strip playlist parameters from a YouTube URL so only the single video remains."""
    # Remove list= and index= and start_radio= params
    cleaned = re.sub(r'[&?](list|index|start_radio)=[^&]*', '', url)
    # If we accidentally removed the leading ? replace first & with ?
    if '?' not in cleaned and '&' in cleaned:
        cleaned = cleaned.replace('&', '?', 1)
    return cleaned


# ───────────── Modern Stylesheet ─────────────

_DARK_STYLE = """
* {
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}

QWidget#mainWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
}

QLabel {
    color: #e0e0ff;
    font-weight: 500;
}

QLabel#titleLabel {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    padding: 4px 0;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #a0a0cc;
    padding-bottom: 8px;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #8888bb;
    padding: 2px 0;
}

QLabel#sectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #9999cc;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding-top: 6px;
}

QLineEdit {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 10px 14px;
    color: #ffffff;
    selection-background-color: #6c63ff;
}
QLineEdit:focus {
    border: 1px solid #6c63ff;
    background: rgba(255, 255, 255, 0.10);
}

QComboBox {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 8px 14px;
    color: #ffffff;
    min-width: 100px;
}
QComboBox:hover {
    border: 1px solid #6c63ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #aaaadd;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #2a2850;
    border: 1px solid #3a3870;
    border-radius: 8px;
    selection-background-color: #6c63ff;
    color: #ffffff;
    padding: 4px;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 6px 10px;
    border: none;
    outline: none;
}
QComboBox QAbstractItemView::item:selected {
    background: #6c63ff;
    color: #ffffff;
    border: none;
}

QPushButton {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
    padding: 8px 18px;
    color: #e0e0ff;
    font-weight: 600;
}
QPushButton:hover {
    background: rgba(108, 99, 255, 0.3);
    border: 1px solid #6c63ff;
}
QPushButton:pressed {
    background: rgba(108, 99, 255, 0.5);
}

QPushButton#downloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #e040fb);
    border: none;
    border-radius: 14px;
    padding: 14px 48px;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    min-width: 220px;
}
QPushButton#downloadBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7b73ff, stop:1 #e860ff);
}
QPushButton#downloadBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5a52dd, stop:1 #c030dd);
}
QPushButton#downloadBtn:disabled {
    background: rgba(108, 99, 255, 0.3);
    color: rgba(255,255,255,0.4);
}

QPushButton#modeBtn {
    border-radius: 10px;
    padding: 8px 20px;
    min-width: 90px;
}
QPushButton#modeBtn:checked {
    background: rgba(108, 99, 255, 0.4);
    border: 1px solid #6c63ff;
    color: #ffffff;
}

QPushButton#helpBtn {
    border-radius: 16px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    font-size: 15px;
    font-weight: 700;
}

QPushButton#themeBtn {
    border-radius: 16px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    font-size: 15px;
}

QRadioButton {
    color: #ccccee;
    spacing: 6px;
    padding: 4px 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #6666aa;
    background: transparent;
}
QRadioButton::indicator:checked {
    background: #6c63ff;
    border: 2px solid #6c63ff;
}
QRadioButton::indicator:hover {
    border: 2px solid #8880ff;
}

QProgressBar {
    background: rgba(255, 255, 255, 0.06);
    border: none;
    border-radius: 8px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #e040fb);
}

QFrame#card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 16px;
}

QFrame#separator {
    background: rgba(255, 255, 255, 0.06);
    max-height: 1px;
    margin: 4px 0;
}
"""

_LIGHT_STYLE = """
* {
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}

QWidget#mainWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #e8eaf6, stop:0.5 #f3e5f5, stop:1 #e3f2fd);
}

QLabel {
    color: #333355;
    font-weight: 500;
}

QLabel#titleLabel {
    font-size: 22px;
    font-weight: 700;
    color: #1a1a3e;
    padding: 4px 0;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #666688;
    padding-bottom: 8px;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #888899;
    padding: 2px 0;
}

QLabel#sectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #5555aa;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding-top: 6px;
}

QLineEdit {
    background: rgba(255, 255, 255, 0.75);
    border: 1px solid rgba(0, 0, 0, 0.10);
    border-radius: 10px;
    padding: 10px 14px;
    color: #222244;
    selection-background-color: #6c63ff;
}
QLineEdit:focus {
    border: 1px solid #6c63ff;
    background: rgba(255, 255, 255, 0.9);
}

QComboBox {
    background: rgba(255, 255, 255, 0.75);
    border: 1px solid rgba(0, 0, 0, 0.10);
    border-radius: 10px;
    padding: 8px 14px;
    color: #222244;
    min-width: 100px;
}
QComboBox:hover {
    border: 1px solid #6c63ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #666688;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #ddddee;
    border-radius: 8px;
    selection-background-color: #6c63ff;
    selection-color: #ffffff;
    color: #222244;
    padding: 4px;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 6px 10px;
    border: none;
    outline: none;
}
QComboBox QAbstractItemView::item:selected {
    background: #6c63ff;
    color: #ffffff;
    border: none;
}

QPushButton {
    background: rgba(255, 255, 255, 0.6);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 10px;
    padding: 8px 18px;
    color: #333355;
    font-weight: 600;
}
QPushButton:hover {
    background: rgba(108, 99, 255, 0.15);
    border: 1px solid #6c63ff;
    color: #4a42dd;
}
QPushButton:pressed {
    background: rgba(108, 99, 255, 0.25);
}

QPushButton#downloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #e040fb);
    border: none;
    border-radius: 14px;
    padding: 14px 48px;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    min-width: 220px;
}
QPushButton#downloadBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7b73ff, stop:1 #e860ff);
}
QPushButton#downloadBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5a52dd, stop:1 #c030dd);
}
QPushButton#downloadBtn:disabled {
    background: rgba(108, 99, 255, 0.3);
    color: rgba(255,255,255,0.4);
}

QPushButton#modeBtn {
    border-radius: 10px;
    padding: 8px 20px;
    min-width: 90px;
}
QPushButton#modeBtn:checked {
    background: rgba(108, 99, 255, 0.25);
    border: 1px solid #6c63ff;
    color: #4a42dd;
}

QPushButton#helpBtn {
    border-radius: 16px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    font-size: 15px;
    font-weight: 700;
}

QPushButton#themeBtn {
    border-radius: 16px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    font-size: 15px;
}

QRadioButton {
    color: #333355;
    spacing: 6px;
    padding: 4px 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #8888bb;
    background: transparent;
}
QRadioButton::indicator:checked {
    background: #6c63ff;
    border: 2px solid #6c63ff;
}
QRadioButton::indicator:hover {
    border: 2px solid #6c63ff;
}

QProgressBar {
    background: rgba(0, 0, 0, 0.06);
    border: none;
    border-radius: 8px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #e040fb);
}

QFrame#card {
    background: rgba(255, 255, 255, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.6);
    border-radius: 16px;
    padding: 16px;
}

QFrame#separator {
    background: rgba(0, 0, 0, 0.06);
    max-height: 1px;
    margin: 4px 0;
}
"""


class DownloaderWindow(QtWidgets.QWidget):
    # Signals for thread-safe GUI updates
    status_changed = QtCore.pyqtSignal(str)
    show_info = QtCore.pyqtSignal(str, str)
    show_error = QtCore.pyqtSignal(str, str)
    progress_changed = QtCore.pyqtSignal(int)

    lang: str
    theme: str

    def __init__(self) -> None:
        super().__init__()
        self._settings = QtCore.QSettings('EasyDownload', 'EasyDownload')
        self.lang = 'tr'
        self.theme = str(self._settings.value('theme', 'dark'))
        self.setObjectName('mainWidget')
        self.init_ui()
        # Restore saved window geometry
        self._restore_geometry()
        # Connect signals
        cast(Any, self.status_changed).connect(self.status_label.setText)
        cast(Any, self.show_info).connect(self._on_show_info)
        cast(Any, self.show_error).connect(self._on_show_error)
        cast(Any, self.progress_changed).connect(self.progress.setValue)
        # Start background FFmpeg check
        threading.Thread(target=self.check_ffmpeg, daemon=True).start()

    def _on_show_info(self, title: str, text: str) -> None:
        QtWidgets.QMessageBox.information(self, title, text)

    def _on_show_error(self, title: str, text: str) -> None:
        QtWidgets.QMessageBox.critical(self, title, text)

    def show_guide(self) -> None:
        self.show_info.emit(
            _TRANSLATIONS[self.lang]['guide_title'],
            _TRANSLATIONS[self.lang]['guide_text']
        )

    def _make_separator(self) -> QtWidgets.QFrame:
        sep = QtWidgets.QFrame()
        sep.setObjectName('separator')
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        return sep

    def _make_section_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName('sectionLabel')
        return lbl

    def _restore_geometry(self) -> None:
        """Restore saved window position and size from QSettings."""
        geo = self._settings.value('geometry')
        if geo is not None:
            self.restoreGeometry(geo)  # type: ignore[arg-type]
        else:
            # Center on screen with default size
            screen = QtWidgets.QApplication.primaryScreen()
            if screen:
                sg = screen.availableGeometry()
                x = (sg.width() - 560) // 2
                y = (sg.height() - 780) // 2
                self.setGeometry(x, y, 560, 780)
            else:
                self.resize(560, 780)

    def closeEvent(self, event: Any) -> None:
        """Save window geometry and theme before closing."""
        self._settings.setValue('geometry', self.saveGeometry())
        self._settings.setValue('theme', self.theme)
        super().closeEvent(event)

    def init_ui(self) -> None:
        self.setWindowTitle(_TRANSLATIONS[self.lang]['title'])
        self.resize(560, 780)
        self.setMinimumSize(480, 560)

        # Main layout with padding
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        # ── Header row ──
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(8)

        # Title + subtitle
        title_col = QtWidgets.QVBoxLayout()
        title_col.setSpacing(0)
        title_lbl = QtWidgets.QLabel('EasyDownload')
        title_lbl.setObjectName('titleLabel')
        subtitle_lbl = QtWidgets.QLabel('YouTube • Instagram • TikTok • Pinterest • Spotify')
        subtitle_lbl.setObjectName('subtitleLabel')
        title_col.addWidget(title_lbl)
        title_col.addWidget(subtitle_lbl)
        header.addLayout(title_col)
        header.addStretch()

        # Small round buttons
        self.help_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['help'])
        self.help_btn.setObjectName('helpBtn')
        self.help_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        cast(Any, self.help_btn.clicked).connect(self.show_guide)
        header.addWidget(self.help_btn)

        self.theme_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['dark'])
        self.theme_btn.setObjectName('themeBtn')
        self.theme_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        cast(Any, self.theme_btn.clicked).connect(self.toggle_theme)
        header.addWidget(self.theme_btn)

        self.lang_combo = QtWidgets.QComboBox()
        cast(Any, self.lang_combo).addItems(['🇹🇷 TR', '🇬🇧 EN'])
        self.lang_combo.setCurrentIndex(0)
        self.lang_combo.setFixedWidth(80)
        cast(Any, self.lang_combo.currentIndexChanged).connect(self.change_language)
        header.addWidget(self.lang_combo)

        outer.addLayout(header)

        # ── Card container ──
        card = QtWidgets.QFrame()
        card.setObjectName('card')
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        # Platform + Mode row
        self.platform_section = self._make_section_label(_TRANSLATIONS[self.lang]['platform'] + ' & ' + _TRANSLATIONS[self.lang]['mode'])
        card_layout.addWidget(self.platform_section)

        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(10)
        self.platform_combo = QtWidgets.QComboBox()
        cast(Any, self.platform_combo).addItems(['YouTube', 'Instagram', 'TikTok', 'Pinterest', 'Spotify'])
        row1.addWidget(self.platform_combo, 2)

        self.mode_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['single'])
        self.mode_btn.setObjectName('modeBtn')
        self.mode_btn.setCheckable(True)
        self.mode_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        cast(Any, self.mode_btn.toggled).connect(self.mode_toggled)
        row1.addWidget(self.mode_btn, 1)
        card_layout.addLayout(row1)

        card_layout.addWidget(self._make_separator())

        # URL
        self.url_section = self._make_section_label(_TRANSLATIONS[self.lang]['url'])
        card_layout.addWidget(self.url_section)
        self.url_edit = QtWidgets.QLineEdit()
        self.url_edit.setPlaceholderText(_TRANSLATIONS[self.lang]['url_placeholder'])
        card_layout.addWidget(self.url_edit)

        card_layout.addWidget(self._make_separator())

        # Format
        self.format_section = self._make_section_label(_TRANSLATIONS[self.lang]['format'])
        card_layout.addWidget(self.format_section)

        format_row = QtWidgets.QHBoxLayout()
        format_row.setSpacing(12)
        self.format_group = QtWidgets.QButtonGroup(self)
        self.mp3_radio = QtWidgets.QRadioButton(_TRANSLATIONS[self.lang]['mp3'])
        self.flac_radio = QtWidgets.QRadioButton(_TRANSLATIONS[self.lang]['flac'])
        self.mp4_radio = QtWidgets.QRadioButton(_TRANSLATIONS[self.lang]['mp4'])
        self.mp4_radio.setChecked(True)
        for r in (self.mp3_radio, self.flac_radio, self.mp4_radio):
            self.format_group.addButton(r)
            cast(Any, r.toggled).connect(self.update_quality_ui)
            r.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            format_row.addWidget(r)
        card_layout.addLayout(format_row)

        # Quality
        self.quality_section = self._make_section_label(_TRANSLATIONS[self.lang]['quality_video'])
        card_layout.addWidget(self.quality_section)
        self.quality_combo = QtWidgets.QComboBox()
        cast(Any, self.quality_combo).addItems(['360p', '480p', '720p', '1080p'])
        card_layout.addWidget(self.quality_combo)

        card_layout.addWidget(self._make_separator())

        # Download location
        self.dir_section = self._make_section_label(_TRANSLATIONS[self.lang]['download_location'])
        card_layout.addWidget(self.dir_section)

        dir_row = QtWidgets.QHBoxLayout()
        dir_row.setSpacing(8)
        self.dir_edit = QtWidgets.QLineEdit()
        self.dir_edit.setPlaceholderText(_TRANSLATIONS[self.lang]['dir_placeholder'])
        dir_row.addWidget(self.dir_edit, 1)
        self.choose_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['choose_location'])
        self.choose_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        cast(Any, self.choose_btn.clicked).connect(self.choose_folder)
        dir_row.addWidget(self.choose_btn)
        card_layout.addLayout(dir_row)

        outer.addWidget(card)

        # ── Progress ──
        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(0)
        outer.addWidget(self.progress)

        # ── Status ──
        self.status_label = QtWidgets.QLabel('')
        self.status_label.setObjectName('statusLabel')
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.status_label)

        # ── Download button ──
        self.download_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['download'])
        self.download_btn.setObjectName('downloadBtn')
        self.download_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        cast(Any, self.download_btn.clicked).connect(self.start_download)
        outer.addWidget(self.download_btn, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        outer.addStretch()

        self.apply_theme()
        self.update_quality_ui()

        # Remove ugly OS frame from all QComboBox popups
        for combo in self.findChildren(QtWidgets.QComboBox):
            popup = combo.view().window()
            if popup:
                popup.setWindowFlags(
                    QtCore.Qt.WindowType.Popup
                    | QtCore.Qt.WindowType.FramelessWindowHint
                    | QtCore.Qt.WindowType.NoDropShadowWindowHint
                )
                popup.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

    # ── Slots ──

    def mode_toggled(self, checked: bool) -> None:
        t = _TRANSLATIONS[self.lang]
        self.mode_btn.setText(t['playlist'] if checked else t['single'])

    def choose_folder(self) -> None:
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if d:
            self.dir_edit.setText(d)

    def change_language(self, idx: int) -> None:
        self.lang = 'tr' if idx == 0 else 'en'
        t = _TRANSLATIONS[self.lang]
        self.setWindowTitle(t['title'])
        self.mode_btn.setText(t['single'] if not self.mode_btn.isChecked() else t['playlist'])
        self.mp3_radio.setText(t['mp3'])
        self.mp4_radio.setText(t['mp4'])
        self.flac_radio.setText(t['flac'])
        self.choose_btn.setText(t['choose_location'])
        self.download_btn.setText(t['download'])
        self.help_btn.setText(t['help'])
        self.url_edit.setPlaceholderText(t['url_placeholder'])
        self.dir_edit.setPlaceholderText(t['dir_placeholder'])
        self.platform_section.setText(t['platform'] + ' & ' + t['mode'])
        self.url_section.setText(t['url'])
        self.format_section.setText(t['format'])
        self.dir_section.setText(t['download_location'])
        self.update_quality_ui()
        self.theme_btn.setText(t['light'] if self.theme == 'dark' else t['dark'])

    def update_quality_ui(self, _checked: bool = False) -> None:
        t = _TRANSLATIONS[self.lang]
        if self.flac_radio.isChecked():
            label = t['quality_flac']
            items = [label]
        elif self.mp3_radio.isChecked():
            label = t['quality_audio']
            items = ['128', '192', '256', '320']
        else:
            label = t['quality_video']
            items = ['360p', '480p', '720p', '1080p']

        self.quality_section.setText(label)
        current = self.quality_combo.currentText()
        self.quality_combo.blockSignals(True)
        self.quality_combo.clear()
        cast(Any, self.quality_combo).addItems(items)
        if current in items:
            self.quality_combo.setCurrentText(current)
        self.quality_combo.blockSignals(False)

    def toggle_theme(self) -> None:
        self.theme = 'dark' if self.theme == 'light' else 'light'
        self.apply_theme()
        t = _TRANSLATIONS[self.lang]
        self.theme_btn.setText(t['light'] if self.theme == 'dark' else t['dark'])

    def apply_theme(self) -> None:
        if self.theme == 'dark':
            self.setStyleSheet(_DARK_STYLE)
        else:
            self.setStyleSheet(_LIGHT_STYLE)

    # ── FFmpeg ──

    def check_ffmpeg(self) -> None:
        if shutil.which('ffmpeg') is not None:
            self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_installed'])
            return

        app_ffmpeg_bin = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin')
        embedded_ffmpeg = shutil.which(
            'ffmpeg',
            path=app_ffmpeg_bin + os.pathsep + os.environ.get('PATH', '')
        )
        if embedded_ffmpeg:
            os.environ['PATH'] = app_ffmpeg_bin + os.pathsep + os.environ.get('PATH', '')
            self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_installed'])
            return

        self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_downloading'])
        try:
            if sys.platform.startswith('win'):
                url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
                fd, tmpzip = tempfile.mkstemp(suffix='.zip')
                os.close(fd)
                urllib.request.urlretrieve(url, tmpzip)

                extract_root = os.path.join(os.path.dirname(__file__), 'ffmpeg')
                if os.path.exists(extract_root):
                    try:
                        shutil.rmtree(extract_root)
                    except Exception:
                        pass
                os.makedirs(extract_root, exist_ok=True)

                with zipfile.ZipFile(tmpzip, 'r') as z:
                    members = z.namelist()
                    ffexes = [m for m in members if m.lower().endswith('ffmpeg.exe')]
                    if not ffexes:
                        raise Exception('ffmpeg.exe not found in archive')
                    z.extractall(extract_root)

                found_bin = None
                for root, _, files in os.walk(extract_root):
                    if 'ffmpeg.exe' in files:
                        found_bin = root
                        break
                if not found_bin:
                    raise Exception('Could not locate ffmpeg binary after extraction')

                final_bin = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin')
                if os.path.exists(final_bin):
                    shutil.rmtree(final_bin)
                shutil.move(found_bin, final_bin)
                os.environ['PATH'] = final_bin + os.pathsep + os.environ.get('PATH', '')

                try:
                    os.remove(tmpzip)
                except Exception:
                    pass

                if shutil.which('ffmpeg') is not None:
                    self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_installed'])
                else:
                    raise Exception('ffmpeg executable not found after installation')
            else:
                subprocess.run(
                    [sys.executable, '-m', 'spotdl', '--download-ffmpeg'],
                    check=True, capture_output=True, timeout=60
                )
                self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_installed'])
        except Exception as e:
            self.status_changed.emit(
                _TRANSLATIONS[self.lang].get('ffmpeg_failed', 'FFmpeg download failed.')
            )
            try:
                self.show_error.emit(_TRANSLATIONS[self.lang]['error'], str(e))
            except Exception:
                pass

    # ── Download ──

    def start_download(self) -> None:
        self.download_btn.setEnabled(False)
        threading.Thread(target=self._download_thread, daemon=True).start()

    def _download_thread(self) -> None:
        t = _TRANSLATIONS[self.lang]
        url = self.url_edit.text().strip()
        if not url:
            self.show_error.emit(t['error'], t['url'])
            self.download_btn.setEnabled(True)
            return

        platform = self.platform_combo.currentText()

        # ── Mix link detection ──
        is_mix = False
        if _is_youtube_mix(url):
            is_mix = True
            url = _extract_single_video_url(url)
            self.status_changed.emit(t['mix_detected'])

        if self.mp3_radio.isChecked():
            format_type = 'MP3'
        elif self.flac_radio.isChecked():
            format_type = 'FLAC'
        else:
            format_type = 'MP4'

        self.status_changed.emit(t['downloading'])
        self.progress_changed.emit(0)

        try:
            out_dir = self.dir_edit.text() or os.path.join(os.path.dirname(__file__), 'Downloads')
            os.makedirs(out_dir, exist_ok=True)

            if platform == 'Spotify':
                cmd = [sys.executable, '-m', 'spotdl', 'download', url, '--output', out_dir]
                subprocess.run(cmd, check=True)
            else:
                ydl_opts: dict[str, Any] = {
                    'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
                    'noplaylist': not self.mode_btn.isChecked() or is_mix,
                    'progress_hooks': [self._progress_hook],
                }

                if format_type == 'FLAC':
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'flac',
                        'preferredquality': '0',
                    }]
                elif format_type == 'MP3':
                    quality = self.quality_combo.currentText()
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality,
                    }]
                else:
                    q = self.quality_combo.currentText().replace('p', '')
                    ydl_opts['format'] = f'bestvideo[height<={q}]+bestaudio/best[height<={q}]/best'

                with yt_dlp.YoutubeDL(cast(Any, ydl_opts)) as ydl:
                    ydl.download([url])

            self.progress_changed.emit(100)
            self.status_changed.emit(t['download_complete'])
            self.show_info.emit(t['success'], t['download_complete'])
        except Exception as e:
            self.show_error.emit(t['error'], str(e))
            self.status_changed.emit('')
        finally:
            self.download_btn.setEnabled(True)

    def _progress_hook(self, d: dict) -> None:
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                pct = int(downloaded / total * 100)
                self.progress_changed.emit(min(pct, 99))
        elif d.get('status') == 'finished':
            self.progress_changed.emit(100)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    win = DownloaderWindow()
    win.show()
    sys.exit(app.exec())
