import os
import sys
import threading
import shutil
import subprocess
import urllib.request
import zipfile
import tempfile
import platform
import time
from PyQt6 import QtWidgets, QtGui, QtCore
import yt_dlp

# Minimal translation dict
_TRANSLATIONS = {
    'tr': {
        'title': 'Şarkı/Video İndirici',
        'platform': 'Platform Seçin:',
        'url': 'URL:',
        'mode': 'Mod:',
        'single': 'Tekli',
        'playlist': 'Playlist',
        'format': 'Format:',
        'mp3': 'MP3 (Ses)',
        'mp4': 'MP4 (Video)',
        'flac': 'FLAC (Kayıpsız)',
        'quality_audio': 'Ses Kalitesi (kbps):',
        'quality_flac': 'Kayıpsız',
        'quality_video': 'Görüntü Kalitesi:',
        'download_location': 'İndirme Konumu:',
        'choose_location': 'Konum Seç',
        'download': 'İndir',
        'ffmpeg_downloading': 'FFmpeg indiriliyor...',
        'ffmpeg_installed': 'FFmpeg zaten yüklü.',
        'ffmpeg_failed': 'FFmpeg indirilemedi.',
        'help': 'Yardım',
        'guide_title': 'Kılavuz',
        'guide_text': 'Kısa kılavuz:\n- FFmpeg yüklü değilse uygulama otomatik indirir ve ./ffmpeg/bin içine yerleştirir.\n- FLAC seçeneği MP3 ve MP4 arasında yer alır; FLAC seçildiğinde çıktı .flac olur.\n- Test: bir YouTube URL\'si girin, Format=FLAC seçip indir; dosya .flac olarak çıkmalıdır.\n- Not: İndirmeler büyük olabilir; sabırlı olun.',
    'dark': 'Koyu',
    'light': 'Aydınlık',
        'download_complete': 'İndirme tamamlandı!',
        'error': 'Hata',
        'info': 'Bilgi',
        'success': 'Başarılı',
    },
    'en': {
        'title': 'Song/Video Downloader',
        'platform': 'Select Platform:',
        'url': 'URL:',
        'mode': 'Mode:',
        'single': 'Single',
        'playlist': 'Playlist',
        'format': 'Format:',
        'mp3': 'MP3 (Audio)',
        'mp4': 'MP4 (Video)',
        'flac': 'FLAC (Lossless)',
        'quality_audio': 'Audio Quality (kbps):',
        'quality_flac': 'Lossless',
        'quality_video': 'Video Quality:',
        'download_location': 'Download Location:',
        'choose_location': 'Choose Location',
        'download': 'Download',
        'ffmpeg_downloading': 'Downloading FFmpeg...',
        'ffmpeg_installed': 'FFmpeg already installed.',
        'ffmpeg_failed': 'FFmpeg download failed.',
        'help': 'Help',
        'guide_title': 'Guide',
        'guide_text': 'Short guide:\n- If ffmpeg is not installed, the app will download and embed it in ./ffmpeg/bin.\n- FLAC option is between MP3 and MP4; selecting FLAC produces .flac files.\n- Test: paste a YouTube URL, choose Format=FLAC and Download; check output folder for .flac.\n- Note: downloads can be large and may take time.',
    'dark': 'Dark',
    'light': 'Light',
        'download_complete': 'Download complete!',
        'error': 'Error',
        'info': 'Info',
        'success': 'Success',
    }
}


class DownloaderWindow(QtWidgets.QWidget):
    # Signals for thread-safe GUI updates
    status_changed = QtCore.pyqtSignal(str)
    show_info = QtCore.pyqtSignal(str, str)
    show_error = QtCore.pyqtSignal(str, str)
    progress_changed = QtCore.pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.lang = 'tr'
        self.theme = 'light'
        self.init_ui()
        # Connect signals to GUI slots
        self.status_changed.connect(self.status_label.setText)
        self.show_info.connect(self._on_show_info)
        self.show_error.connect(self._on_show_error)
        self.progress_changed.connect(self.progress.setValue)

        # Start background FFmpeg check
        threading.Thread(target=self.check_ffmpeg, daemon=True).start()

    def _on_show_info(self, title, text):
        QtWidgets.QMessageBox.information(self, title, text)

    def _on_show_error(self, title, text):
        QtWidgets.QMessageBox.critical(self, title, text)

    def show_guide(self):
        # show localized guide text in an info dialog
        self.show_info.emit(_TRANSLATIONS[self.lang]['guide_title'], _TRANSLATIONS[self.lang]['guide_text'])

    def init_ui(self):
        self.setWindowTitle(_TRANSLATIONS[self.lang]['title'])
        self.resize(640, 520)

        main_layout = QtWidgets.QVBoxLayout(self)

        # Top controls row (language and theme)
        top_row = QtWidgets.QHBoxLayout()
        top_row.addStretch()
        self.help_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['help'])
        self.help_btn.clicked.connect(self.show_guide)
        top_row.addWidget(self.help_btn)
        self.theme_btn = QtWidgets.QPushButton('Dark')
        self.theme_btn.clicked.connect(self.toggle_theme)
        top_row.addWidget(self.theme_btn)
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItems(['Türkçe', 'English'])
        self.lang_combo.setCurrentIndex(0)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        top_row.addWidget(self.lang_combo)
        main_layout.addLayout(top_row)

        form = QtWidgets.QFormLayout()

        # Platform
        self.platform_label = QtWidgets.QLabel(_TRANSLATIONS[self.lang]['platform'])
        self.platform_combo = QtWidgets.QComboBox()
        self.platform_combo.addItems(['YouTube', 'Instagram', 'TikTok', 'Pinterest', 'Spotify'])
        form.addRow(self.platform_label, self.platform_combo)

        # URL
        self.url_label = QtWidgets.QLabel(_TRANSLATIONS[self.lang]['url'])
        self.url_edit = QtWidgets.QLineEdit()
        form.addRow(self.url_label, self.url_edit)

        # Mode
        mode_h = QtWidgets.QHBoxLayout()
        self.mode_label = QtWidgets.QLabel(_TRANSLATIONS[self.lang]['mode'])
        self.mode_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['single'])
        self.mode_btn.setCheckable(True)
        self.mode_btn.toggled.connect(self.mode_toggled)
        mode_h.addWidget(self.mode_label)
        mode_h.addWidget(self.mode_btn)
        form.addRow(mode_h)

        # Format
        format_h = QtWidgets.QHBoxLayout()
        self.format_group = QtWidgets.QButtonGroup(self)
        self.mp3_radio = QtWidgets.QRadioButton(_TRANSLATIONS[self.lang]['mp3'])
        self.mp4_radio = QtWidgets.QRadioButton(_TRANSLATIONS[self.lang]['mp4'])
        self.flac_radio = QtWidgets.QRadioButton(_TRANSLATIONS[self.lang]['flac'])
        self.mp4_radio.setChecked(True)
        self.format_group.addButton(self.mp3_radio)
        self.format_group.addButton(self.mp4_radio)
        self.format_group.addButton(self.flac_radio)
        # connect toggles to update quality UI
        self.mp3_radio.toggled.connect(self.update_quality_ui)
        self.mp4_radio.toggled.connect(self.update_quality_ui)
        self.flac_radio.toggled.connect(self.update_quality_ui)
        self.format_label = QtWidgets.QLabel(_TRANSLATIONS[self.lang]['format'])
        format_h.addWidget(self.format_label)
        format_h.addWidget(self.mp3_radio)
        format_h.addWidget(self.flac_radio)
        format_h.addWidget(self.mp4_radio)
        form.addRow(format_h)

        # Quality
        self.quality_label = QtWidgets.QLabel(_TRANSLATIONS[self.lang]['quality_video'])
        self.quality_combo = QtWidgets.QComboBox()
        self.quality_combo.addItems(['360p', '480p', '720p', '1080p'])
        form.addRow(self.quality_label, self.quality_combo)

        # Download location
        self.dir_edit = QtWidgets.QLineEdit()
        self.choose_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['choose_location'])
        self.choose_btn.clicked.connect(self.choose_folder)
        dir_h = QtWidgets.QHBoxLayout()
        dir_h.addWidget(self.dir_edit)
        dir_h.addWidget(self.choose_btn)
        self.dir_label = QtWidgets.QLabel(_TRANSLATIONS[self.lang]['download_location'])
        form.addRow(self.dir_label, dir_h)

        main_layout.addLayout(form)

        # Progress
        self.progress = QtWidgets.QProgressBar()
        main_layout.addWidget(self.progress)

        # Status
        self.status_label = QtWidgets.QLabel('')
        main_layout.addWidget(self.status_label)

        # Download button
        self.download_btn = QtWidgets.QPushButton(_TRANSLATIONS[self.lang]['download'])
        self.download_btn.clicked.connect(self.start_download)
        main_layout.addWidget(self.download_btn, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.apply_theme()
        # ensure quality UI reflects current format on startup
        self.update_quality_ui()

    def mode_toggled(self, checked):
        self.mode_btn.setText(_TRANSLATIONS[self.lang]['playlist'] if checked else _TRANSLATIONS[self.lang]['single'])

    def choose_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if d:
            self.dir_edit.setText(d)

    def change_language(self, idx):
        self.lang = 'tr' if idx == 0 else 'en'
        self.setWindowTitle(_TRANSLATIONS[self.lang]['title'])
        # update labels
        # update other UI text
        self.mode_btn.setText(_TRANSLATIONS[self.lang]['single'] if not self.mode_btn.isChecked() else _TRANSLATIONS[self.lang]['playlist'])
        self.mp3_radio.setText(_TRANSLATIONS[self.lang]['mp3'])
        self.mp4_radio.setText(_TRANSLATIONS[self.lang]['mp4'])
        self.flac_radio.setText(_TRANSLATIONS[self.lang]['flac'])
        self.choose_btn.setText(_TRANSLATIONS[self.lang]['choose_location'])
        self.download_btn.setText(_TRANSLATIONS[self.lang]['download'])
        self.help_btn.setText(_TRANSLATIONS[self.lang]['help'])
        # update labels
        self.platform_label.setText(_TRANSLATIONS[self.lang]['platform'])
        self.url_label.setText(_TRANSLATIONS[self.lang]['url'])
        self.mode_label.setText(_TRANSLATIONS[self.lang]['mode'])
        self.format_label.setText(_TRANSLATIONS[self.lang]['format'])
        # update quality label/items according to current format and language
        self.update_quality_ui()
        self.dir_label.setText(_TRANSLATIONS[self.lang]['download_location'])
        # update theme button text to localized value
        self.theme_btn.setText(_TRANSLATIONS[self.lang]['dark'] if self.theme == 'light' else _TRANSLATIONS[self.lang]['light'])

    def update_quality_ui(self):
        # Update the quality label and combo items based on selected format and current language
        if self.flac_radio.isChecked():
            label = _TRANSLATIONS[self.lang].get('quality_flac', 'Lossless')
            items = [label]
        elif self.mp3_radio.isChecked():
            label = _TRANSLATIONS[self.lang].get('quality_audio', 'Ses Kalitesi (kbps):')
            items = ['128', '192', '256', '320']
        else:
            label = _TRANSLATIONS[self.lang].get('quality_video', 'Görüntü Kalitesi:')
            items = ['360p', '480p', '720p', '1080p']

        # set label
        try:
            self.quality_label.setText(label)
        except Exception:
            pass

        # update combo while trying to preserve selection
        current = self.quality_combo.currentText()
        self.quality_combo.blockSignals(True)
        self.quality_combo.clear()
        self.quality_combo.addItems(items)
        # restore if present
        if current in items:
            self.quality_combo.setCurrentText(current)
        self.quality_combo.blockSignals(False)

    def toggle_theme(self):
        self.theme = 'dark' if self.theme == 'light' else 'light'
        self.apply_theme()
        self.theme_btn.setText('Dark' if self.theme == 'light' else 'Light')

    def apply_theme(self):
        if self.theme == 'dark':
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor('#2e2e2e'))
            palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor('#ffffff'))
            palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('#3a3a3a'))
            palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#2e2e2e'))
            palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor('#ffffff'))
            palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor('#3e3e3e'))
            palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor('#ffffff'))
            self.setPalette(palette)
        else:
            self.setPalette(self.style().standardPalette())

    def check_ffmpeg(self):
        # Prefer system ffmpeg if available
        if shutil.which('ffmpeg') is not None:
            self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_installed'])
            return

        # Check if we already embedded ffmpeg in app folder
        app_ffmpeg_bin = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin')
        # if ffmpeg exists inside embedded bin, add to PATH for the process
        embedded_ffmpeg = shutil.which('ffmpeg', path=app_ffmpeg_bin + os.pathsep + os.environ.get('PATH', ''))
        if embedded_ffmpeg:
            os.environ['PATH'] = app_ffmpeg_bin + os.pathsep + os.environ.get('PATH', '')
            self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_installed'])
            return

        # Otherwise try to download latest FFmpeg (Windows only fallback). Show status updates.
        self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_downloading'])
        try:
            if sys.platform.startswith('win'):
                url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
                fd, tmpzip = tempfile.mkstemp(suffix='.zip')
                os.close(fd)
                # download (blocking) - for large files this may take a while
                urllib.request.urlretrieve(url, tmpzip)

                extract_root = os.path.join(os.path.dirname(__file__), 'ffmpeg')
                # ensure clean extract root
                if os.path.exists(extract_root):
                    try:
                        shutil.rmtree(extract_root)
                    except Exception:
                        pass
                os.makedirs(extract_root, exist_ok=True)

                with zipfile.ZipFile(tmpzip, 'r') as z:
                    members = z.namelist()
                    # find any ffmpeg.exe entries
                    ffexes = [m for m in members if m.lower().endswith('ffmpeg.exe')]
                    if not ffexes:
                        raise Exception('ffmpeg.exe not found in archive')
                    # Extract all files (cheap) then move bin to standard location
                    z.extractall(extract_root)

                # find actual bin dir containing ffmpeg.exe
                found_bin = None
                for root, dirs, files in os.walk(extract_root):
                    if 'ffmpeg.exe' in files:
                        found_bin = root
                        break
                if not found_bin:
                    raise Exception('Could not locate ffmpeg binary after extraction')

                final_bin = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin')
                # remove existing final_bin if exists
                if os.path.exists(final_bin):
                    shutil.rmtree(final_bin)
                # move the found bin directory to final_bin
                shutil.move(found_bin, final_bin)

                # Add to process PATH so subsequent subprocess calls pick it up
                os.environ['PATH'] = final_bin + os.pathsep + os.environ.get('PATH', '')

                # cleanup tmp zip
                try:
                    os.remove(tmpzip)
                except Exception:
                    pass

                # verify ffmpeg now accessible
                if shutil.which('ffmpeg') is not None:
                    self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_installed'])
                else:
                    raise Exception('ffmpeg executable not found after installation')
            else:
                # Non-windows fallback: try spotdl download helper
                subprocess.run([sys.executable, '-m', 'spotdl', '--download-ffmpeg'], check=True, capture_output=True, timeout=60)
                self.status_changed.emit(_TRANSLATIONS[self.lang]['ffmpeg_installed'])
        except Exception as e:
            # show friendly failure message and details
            self.status_changed.emit(_TRANSLATIONS[self.lang].get('ffmpeg_failed', 'FFmpeg download failed.'))
            try:
                self.show_error.emit(_TRANSLATIONS[self.lang]['error'], str(e))
            except Exception:
                pass

    def start_download(self):
        # Start a download thread with current settings
        threading.Thread(target=self._download_thread, daemon=True).start()

    def _download_thread(self):
        url = self.url_edit.text().strip()
        if not url:
            # emit error to GUI thread
            self.show_error.emit(_TRANSLATIONS[self.lang]['error'], _TRANSLATIONS[self.lang]['url'])
            return
        platform = self.platform_combo.currentText()
        if self.mp3_radio.isChecked():
            format_type = 'MP3'
        elif self.flac_radio.isChecked():
            format_type = 'FLAC'
        else:
            format_type = 'MP4'
        quality = self.quality_combo.currentText()
        is_playlist = self.mode_btn.isChecked()

        self.status_changed.emit('Downloading...')
        try:
            out_dir = self.dir_edit.text() or os.path.join(os.path.dirname(__file__), 'Downloads')
            if platform == 'Spotify':
                # use spotdl
                cmd = [sys.executable, '-m', 'spotdl', 'download', url, '--output', out_dir]
                subprocess.run(cmd, check=True)
            else:
                if format_type == 'FLAC':
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'flac',
                            'preferredquality': '0',
                        }]
                    }
                else:
                    ydl_opts = {'format': 'bestaudio/best' if format_type == 'MP3' else 'best', 'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s')}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            self.status_changed.emit(_TRANSLATIONS[self.lang]['download_complete'])
            # show info on GUI thread
            self.show_info.emit(_TRANSLATIONS[self.lang]['success'], _TRANSLATIONS[self.lang]['download_complete'])
        except Exception as e:
            self.show_error.emit(_TRANSLATIONS[self.lang]['error'], str(e))


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    win = DownloaderWindow()
    win.show()
    sys.exit(app.exec())
