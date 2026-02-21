import os
import sys
import re
import json
import threading
import shutil
import subprocess
import urllib.request
import zipfile
import tempfile
from typing import Any
import customtkinter as ctk
from tkinter import filedialog, messagebox
import yt_dlp

# ─── Translations ───
_TR = {
    'title': 'EasyDownload',
    'platform': 'PLATFORM',
    'url': 'URL',
    'mode': 'MOD',
    'mode_single': 'Tekli',
    'mode_playlist': 'Playlist',
    'format': 'FORMAT',
    'quality_audio': 'SES KALİTESİ',
    'quality_flac': 'KAYIPSIZ',
    'quality_video': 'GÖRÜNTÜ KALİTESİ',
    'download_location': 'İNDİRME KONUMU',
    'browse': 'Göz At',
    'download': 'İndir',
    'ffmpeg_downloading': 'FFmpeg indiriliyor...',
    'ffmpeg_installed': '✓ Hazır',
    'ffmpeg_failed': 'FFmpeg indirilemedi.',
    'download_complete': 'İndirme tamamlandı!',
    'error': 'Hata',
    'success': 'Başarılı',
    'mix_detected': 'Mix algılandı – sadece ilk şarkı.',
    'downloading': 'İndiriliyor...',
    'url_placeholder': 'YouTube, Instagram, TikTok linkini yapıştırın...',
    'dir_placeholder': 'İndirme klasörü...',
    'guide_title': 'Kılavuz',
    'guide_text': (
        'EasyDownload Kılavuz:\n\n'
        '• FFmpeg yoksa otomatik indirir.\n'
        '• YouTube Mix → sadece ilk şarkı.\n'
        '• FLAC = kayıpsız ses.\n'
        '• Playlist modu ile tüm liste indirilir.'
    ),
}

_EN = {
    'title': 'EasyDownload',
    'platform': 'PLATFORM',
    'url': 'URL',
    'mode': 'MODE',
    'mode_single': 'Single',
    'mode_playlist': 'Playlist',
    'format': 'FORMAT',
    'quality_audio': 'AUDIO QUALITY',
    'quality_flac': 'LOSSLESS',
    'quality_video': 'VIDEO QUALITY',
    'download_location': 'DOWNLOAD LOCATION',
    'browse': 'Browse',
    'download': 'Download',
    'ffmpeg_downloading': 'Downloading FFmpeg...',
    'ffmpeg_installed': '✓ Ready',
    'ffmpeg_failed': 'FFmpeg download failed.',
    'download_complete': 'Download complete!',
    'error': 'Error',
    'success': 'Success',
    'mix_detected': 'Mix detected – first song only.',
    'downloading': 'Downloading...',
    'url_placeholder': 'Paste YouTube, Instagram, TikTok link...',
    'dir_placeholder': 'Download folder...',
    'guide_title': 'Guide',
    'guide_text': (
        'EasyDownload Guide:\n\n'
        '• Auto-downloads FFmpeg if missing.\n'
        '• YouTube Mix → first song only.\n'
        '• FLAC = lossless audio.\n'
        '• Playlist mode downloads entire list.'
    ),
}

_LANGS = {'tr': _TR, 'en': _EN}

# ─── Mix URL helpers ───
_MIX_RE = re.compile(r'[?&]list=(RD[A-Za-z0-9_-]+)')


def _is_mix(url: str) -> bool:
    return bool(_MIX_RE.search(url))


def _strip_mix(url: str) -> str:
    cleaned = re.sub(r'[&?](list|index|start_radio)=[^&]*', '', url)
    if '?' not in cleaned and '&' in cleaned:
        cleaned = cleaned.replace('&', '?', 1)
    return cleaned


# ─── Settings ───
_CFG_DIR = os.path.join(os.path.expanduser('~'), 'EasyDownload')
_CFG = os.path.join(_CFG_DIR, 'settings.json')


def _load() -> dict:
    try:
        with open(_CFG, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d: dict) -> None:
    try:
        os.makedirs(_CFG_DIR, exist_ok=True)
        with open(_CFG, 'w') as f:
            json.dump(d, f)
    except Exception:
        pass


class App(ctk.CTk):
    # ─── Colors ───
    D = {
        'bg': '#0d0b1e', 'card': '#16132e', 'brd': '#252252',
        'acc': '#7c6fff', 'acc_h': '#9589ff',
        'txt': '#eeeeff', 'txt2': '#9995cc', 'txt3': '#6662aa',
        'inp': '#1c1940', 'inp_b': '#2e2a60',
        'seg': '#1c1940', 'seg_s': '#7c6fff', 'seg_txt': '#ccccff',
    }
    L = {
        'bg': '#f0ecff', 'card': '#ffffff', 'brd': '#d5d0f0',
        'acc': '#7c6fff', 'acc_h': '#6558e0',
        'txt': '#1a1835', 'txt2': '#6660aa', 'txt3': '#8880cc',
        'inp': '#f5f2ff', 'inp_b': '#d5d0f0',
        'seg': '#e8e4ff', 'seg_s': '#7c6fff', 'seg_txt': '#333355',
    }

    def __init__(self) -> None:
        super().__init__()
        self._s = _load()
        self.lang = 'tr'
        self._thm = self._s.get('theme', 'dark')
        self._playlist = False

        ctk.set_appearance_mode(self._thm)
        self.title('EasyDownload')
        self.minsize(520, 800)

        geo = self._s.get('geo')
        if geo:
            parts = geo.split('+')[0]
            self.geometry(parts)
        else:
            self.geometry('560x950')
        self.after(30, self._center)

        self.protocol('WM_DELETE_WINDOW', self._quit)
        self._build()
        threading.Thread(target=self._ffmpeg_check, daemon=True).start()

    @property
    def t(self) -> dict:
        return _LANGS[self.lang]

    @property
    def c(self) -> dict:
        return self.D if self._thm == 'dark' else self.L

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f'{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}')

    def _quit(self) -> None:
        self._s['geo'] = self.geometry()
        self._s['theme'] = self._thm
        _save(self._s)
        self.destroy()

    # ───────────── BUILD ─────────────

    def _build(self) -> None:
        c = self.c
        for w in self.winfo_children():
            w.destroy()

        self.configure(fg_color=c['bg'])

        wrap = ctk.CTkFrame(self, fg_color='transparent')
        wrap.pack(fill='both', expand=True, padx=26, pady=(16, 24))

        # ── Header ──
        hdr = ctk.CTkFrame(wrap, fg_color='transparent')
        hdr.pack(fill='x', pady=(0, 14))

        lf = ctk.CTkFrame(hdr, fg_color='transparent')
        lf.pack(side='left')
        ctk.CTkLabel(lf, text='EasyDownload',
                     font=ctk.CTkFont('Segoe UI', 26, 'bold'),
                     text_color=c['txt']).pack(anchor='w')
        ctk.CTkLabel(lf, text='YouTube • Instagram • TikTok • Pinterest • Spotify',
                     font=ctk.CTkFont('Segoe UI', 11),
                     text_color=c['txt3']).pack(anchor='w', pady=(1, 0))

        rf = ctk.CTkFrame(hdr, fg_color='transparent')
        rf.pack(side='right')

        ctk.CTkButton(rf, text='?', width=32, height=32, corner_radius=16,
                      fg_color=c['card'], hover_color=c['brd'],
                      text_color=c['txt'], border_width=1, border_color=c['brd'],
                      font=ctk.CTkFont(size=14, weight='bold'),
                      command=self._guide).pack(side='left', padx=3)

        ctk.CTkButton(rf, text='☀️' if self._thm == 'dark' else '🌙',
                      width=32, height=32, corner_radius=16,
                      fg_color=c['card'], hover_color=c['brd'],
                      text_color=c['txt'], border_width=1, border_color=c['brd'],
                      font=ctk.CTkFont(size=14),
                      command=self._flip_theme).pack(side='left', padx=3)

        self._lang_seg = ctk.CTkSegmentedButton(
            rf, values=['TR', 'EN'], width=80, height=30,
            font=ctk.CTkFont(size=11, weight='bold'),
            fg_color=c['seg'], selected_color=c['seg_s'],
            selected_hover_color=c['acc_h'],
            unselected_color=c['card'], unselected_hover_color=c['brd'],
            text_color=c['seg_txt'],
            command=self._lang_changed)
        self._lang_seg.set('TR' if self.lang == 'tr' else 'EN')
        self._lang_seg.pack(side='left', padx=(6, 0))

        # ── Card ──
        card = ctk.CTkFrame(wrap, fg_color=c['card'], corner_radius=18,
                            border_width=1, border_color=c['brd'])
        card.pack(fill='x', pady=(0, 16))

        inn = ctk.CTkFrame(card, fg_color='transparent')
        inn.pack(fill='x', padx=20, pady=16)

        # — Platform —
        self._lp = self._section(inn, self.t['platform'])
        self._plat_seg = ctk.CTkSegmentedButton(
            inn, values=['YouTube', 'Instagram', 'TikTok', 'Pinterest', 'Spotify'],
            height=34, font=ctk.CTkFont(size=12, weight='bold'),
            fg_color=c['seg'], selected_color=c['seg_s'],
            selected_hover_color=c['acc_h'],
            unselected_color=c['card'], unselected_hover_color=c['brd'],
            text_color=c['seg_txt'])
        self._plat_seg.set('YouTube')
        self._plat_seg.pack(fill='x', pady=(0, 10))

        # — Mode —
        self._lm = self._section(inn, self.t['mode'])
        self._mode_seg = ctk.CTkSegmentedButton(
            inn, values=[self.t['mode_single'], self.t['mode_playlist']],
            height=34, font=ctk.CTkFont(size=12, weight='bold'),
            fg_color=c['seg'], selected_color=c['seg_s'],
            selected_hover_color=c['acc_h'],
            unselected_color=c['card'], unselected_hover_color=c['brd'],
            text_color=c['seg_txt'])
        self._mode_seg.set(self.t['mode_single'])
        self._mode_seg.pack(fill='x', pady=(0, 10))

        self._sep(inn, c)

        # — URL —
        self._lu = self._section(inn, self.t['url'])
        self._url = ctk.CTkEntry(
            inn, height=40, corner_radius=10,
            fg_color=c['inp'], border_color=c['inp_b'],
            text_color=c['txt'], placeholder_text=self.t['url_placeholder'],
            placeholder_text_color=c['txt3'], font=ctk.CTkFont(size=13))
        self._url.pack(fill='x', pady=(0, 10))

        self._sep(inn, c)

        # — Format —
        self._lf = self._section(inn, self.t['format'])
        self._fmt_seg = ctk.CTkSegmentedButton(
            inn, values=['MP3', 'MP4'],
            height=34, font=ctk.CTkFont(size=13, weight='bold'),
            fg_color=c['seg'], selected_color=c['seg_s'],
            selected_hover_color=c['acc_h'],
            unselected_color=c['card'], unselected_hover_color=c['brd'],
            text_color=c['seg_txt'],
            command=self._fmt_changed)
        self._fmt_seg.set('MP4')
        self._fmt_seg.pack(fill='x', pady=(0, 10))

        # — Quality —
        self._lq = self._section(inn, self.t['quality_video'])
        self._qual_seg = ctk.CTkSegmentedButton(
            inn, values=['360p', '480p', '720p', '1080p'],
            height=34, font=ctk.CTkFont(size=12, weight='bold'),
            fg_color=c['seg'], selected_color=c['seg_s'],
            selected_hover_color=c['acc_h'],
            unselected_color=c['card'], unselected_hover_color=c['brd'],
            text_color=c['seg_txt'])
        self._qual_seg.set('1080p')
        self._qual_seg.pack(fill='x', pady=(0, 10))

        self._sep(inn, c)

        # — Download location —
        self._ld = self._section(inn, self.t['download_location'])
        dr = ctk.CTkFrame(inn, fg_color='transparent')
        dr.pack(fill='x')

        self._dir = ctk.CTkEntry(
            dr, height=38, corner_radius=10,
            fg_color=c['inp'], border_color=c['inp_b'],
            text_color=c['txt'], placeholder_text=self.t['dir_placeholder'],
            placeholder_text_color=c['txt3'], font=ctk.CTkFont(size=13))
        self._dir.pack(side='left', fill='x', expand=True, padx=(0, 8))

        self._browse = ctk.CTkButton(
            dr, text=self.t['browse'], height=38, width=80, corner_radius=10,
            fg_color=c['card'], hover_color=c['brd'],
            text_color=c['txt2'], border_width=1, border_color=c['brd'],
            font=ctk.CTkFont(size=12), command=self._pick_dir)
        self._browse.pack(side='right')

        # ── Progress ──
        self._prog = ctk.CTkProgressBar(
            wrap, height=6, corner_radius=3,
            fg_color=c['inp'], progress_color=c['acc'])
        self._prog.set(0)
        self._prog.pack(fill='x', pady=(10, 4))

        # ── Status ──
        self._status = ctk.CTkLabel(wrap, text='',
                                     font=ctk.CTkFont(size=11),
                                     text_color=c['txt3'])
        self._status.pack(pady=(2, 10))

        # ── Download button ──
        self._dl_btn = ctk.CTkButton(
            wrap, text=self.t['download'], height=52, width=240,
            corner_radius=14, font=ctk.CTkFont('Segoe UI', 15, 'bold'),
            fg_color=c['acc'], hover_color=c['acc_h'],
            text_color='#ffffff', command=self._go)
        self._dl_btn.pack(pady=(0, 8))

    def _section(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(parent, text=text,
                           font=ctk.CTkFont('Segoe UI', 10, 'bold'),
                           text_color=self.c['txt3'])
        lbl.pack(anchor='w', pady=(8, 5))
        return lbl

    @staticmethod
    def _sep(parent: ctk.CTkFrame, c: dict) -> None:
        ctk.CTkFrame(parent, fg_color=c['brd'], height=1, corner_radius=0).pack(fill='x', pady=4)

    # ───────────── ACTIONS ─────────────

    def _pick_dir(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self._dir.delete(0, 'end')
            self._dir.insert(0, d)

    def _lang_changed(self, val: str) -> None:
        self.lang = 'tr' if val == 'TR' else 'en'
        t = self.t
        self._lp.configure(text=t['platform'])
        self._lm.configure(text=t['mode'])
        self._lu.configure(text=t['url'])
        self._lf.configure(text=t['format'])
        self._ld.configure(text=t['download_location'])
        self._browse.configure(text=t['browse'])
        self._dl_btn.configure(text=t['download'])
        self._url.configure(placeholder_text=t['url_placeholder'])
        self._dir.configure(placeholder_text=t['dir_placeholder'])
        # Update mode segmented button values
        old_mode = self._mode_seg.get()
        is_playlist = old_mode in [_TR['mode_playlist'], _EN['mode_playlist']]
        self._mode_seg.configure(values=[t['mode_single'], t['mode_playlist']])
        self._mode_seg.set(t['mode_playlist'] if is_playlist else t['mode_single'])
        self._fmt_changed(self._fmt_seg.get())

    def _fmt_changed(self, val: str) -> None:
        t = self.t
        if val == 'MP3':
            self._lq.configure(text=t['quality_audio'])
            self._qual_seg.configure(values=['128', '192', '256', '320', 'FLAC'])
            self._qual_seg.set('320')
        else:
            self._lq.configure(text=t['quality_video'])
            self._qual_seg.configure(values=['360p', '480p', '720p', '1080p'])
            self._qual_seg.set('1080p')

    def _flip_theme(self) -> None:
        self._thm = 'light' if self._thm == 'dark' else 'dark'
        ctk.set_appearance_mode(self._thm)
        self._build()
        self._fmt_changed(self._fmt_seg.get())

    def _guide(self) -> None:
        t = self.t
        c = self.c
        w = ctk.CTkToplevel(self)
        w.title(t['guide_title'])
        w.geometry('400x260')
        w.resizable(False, False)
        w.transient(self)
        w.grab_set()
        w.configure(fg_color=c['bg'])
        ctk.CTkLabel(w, text=f"📖  {t['guide_title']}",
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=c['txt']).pack(pady=(20, 8))
        ctk.CTkLabel(w, text=t['guide_text'], font=ctk.CTkFont(size=12),
                     text_color=c['txt2'], justify='left', wraplength=340).pack(padx=24, anchor='w')
        ctk.CTkButton(w, text='OK', width=90, height=32, corner_radius=10,
                      fg_color=c['acc'], hover_color=c['acc_h'],
                      command=w.destroy).pack(pady=(14, 16))

    # ───────────── FFmpeg ─────────────

    def _ss(self, txt: str) -> None:
        self.after(0, lambda: self._status.configure(text=txt))

    def _sp(self, v: float) -> None:
        self.after(0, lambda: self._prog.set(v))

    def _ffmpeg_check(self) -> None:
        if shutil.which('ffmpeg'):
            self._ss(self.t['ffmpeg_installed']); return

        fb = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'bin')
        if shutil.which('ffmpeg', path=fb + os.pathsep + os.environ.get('PATH', '')):
            os.environ['PATH'] = fb + os.pathsep + os.environ.get('PATH', '')
            self._ss(self.t['ffmpeg_installed']); return

        self._ss(self.t['ffmpeg_downloading'])
        try:
            if sys.platform.startswith('win'):
                url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
                fd, tmp = tempfile.mkstemp(suffix='.zip'); os.close(fd)
                urllib.request.urlretrieve(url, tmp)
                root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')
                if os.path.exists(root): shutil.rmtree(root, True)
                os.makedirs(root, exist_ok=True)
                with zipfile.ZipFile(tmp, 'r') as z:
                    if not any(m.lower().endswith('ffmpeg.exe') for m in z.namelist()):
                        raise RuntimeError('ffmpeg.exe missing')
                    z.extractall(root)
                found = None
                for r, _, fs in os.walk(root):
                    if 'ffmpeg.exe' in fs: found = r; break
                if not found: raise RuntimeError('ffmpeg not found')
                final = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'bin')
                if os.path.exists(final): shutil.rmtree(final)
                shutil.move(found, final)
                os.environ['PATH'] = final + os.pathsep + os.environ.get('PATH', '')
                try: os.remove(tmp)
                except Exception: pass
                if shutil.which('ffmpeg'): self._ss(self.t['ffmpeg_installed'])
                else: raise RuntimeError('ffmpeg not accessible')
            else:
                subprocess.run([sys.executable, '-m', 'spotdl', '--download-ffmpeg'],
                               check=True, capture_output=True, timeout=60)
                self._ss(self.t['ffmpeg_installed'])
        except Exception as e:
            self._ss(self.t['ffmpeg_failed'])
            self.after(0, lambda: messagebox.showerror(self.t['error'], str(e)))

    # ───────────── DOWNLOAD ─────────────

    def _go(self) -> None:
        self._dl_btn.configure(state='disabled')
        threading.Thread(target=self._dl, daemon=True).start()

    def _dl(self) -> None:
        t = self.t
        url = self._url.get().strip()
        if not url:
            self.after(0, lambda: messagebox.showwarning(t['error'], 'URL boş / empty'))
            self.after(0, lambda: self._dl_btn.configure(state='normal'))
            return

        platform = self._plat_seg.get()
        mix = _is_mix(url)
        if mix:
            url = _strip_mix(url)
            self._ss(t['mix_detected'])

        mode_val = self._mode_seg.get()
        is_playlist = mode_val in [_TR['mode_playlist'], _EN['mode_playlist']]

        fmt = self._fmt_seg.get()
        self._ss(t['downloading'])
        self._sp(0)

        try:
            out = self._dir.get().strip() or os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'Downloads')
            os.makedirs(out, exist_ok=True)

            if platform == 'Spotify':
                subprocess.run(
                    [sys.executable, '-m', 'spotdl', 'download', url, '--output', out],
                    check=True)
            else:
                opts: dict[str, Any] = {
                    'outtmpl': os.path.join(out, '%(title)s.%(ext)s'),
                    'noplaylist': not is_playlist or mix,
                    'progress_hooks': [self._hook],
                }
                qual = self._qual_seg.get()
                if fmt == 'MP3' and qual == 'FLAC':
                    opts['format'] = 'bestaudio/best'
                    opts['postprocessors'] = [{'key': 'FFmpegExtractAudio',
                                               'preferredcodec': 'flac',
                                               'preferredquality': '0'}]
                elif fmt == 'MP3':
                    opts['format'] = 'bestaudio/best'
                    opts['postprocessors'] = [{'key': 'FFmpegExtractAudio',
                                               'preferredcodec': 'mp3',
                                               'preferredquality': qual}]
                else:
                    q = qual.replace('p', '')
                    opts['format'] = f'bestvideo[height<={q}]+bestaudio/best[height<={q}]/best'

                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])

            self._sp(1.0)
            self._ss(t['download_complete'])
            self.after(0, lambda: messagebox.showinfo(t['success'], t['download_complete']))
        except Exception as e:
            self._ss('')
            self.after(0, lambda: messagebox.showerror(t['error'], str(e)))
        finally:
            self.after(0, lambda: self._dl_btn.configure(state='normal'))

    def _hook(self, d: dict) -> None:
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done = d.get('downloaded_bytes', 0)
            if total > 0:
                self._sp(min(done / total, 0.99))
        elif d.get('status') == 'finished':
            self._sp(1.0)


if __name__ == '__main__':
    app = App()
    app.mainloop()
