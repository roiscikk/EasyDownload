EasyDownload — Kullanım Rehberi / Quick Guide

TR
---
- Uygulama YouTube, Instagram, TikTok, Pinterest ve Spotify linklerinden indirme yapabilir.
- FLAC desteği: Format seçiminde "FLAC" seçerseniz ses dosyaları `.flac` olarak çıktı alırsınız.
- FFmpeg: Eğer sisteminizde `ffmpeg` yoksa uygulama otomatik olarak Windows için bir FFmpeg ZIP indirip `./ffmpeg/bin` içine çıkarır ve uygulama çalışmasında kullanır.
- Test: Uygulamayı açın, bir YouTube URL'si yapıştırın, `Format` olarak `FLAC` seçin ve `İndir` butonuna basın. İndirme klasöründe `.flac` dosyası oluşmalıdır.
- Not: İndirme ve dönüştürme işlemleri internet hızınıza göre zaman alabilir.

EN
---
- The app can download from YouTube, Instagram, TikTok, Pinterest, and Spotify.
- FLAC support: Choose "FLAC" to get lossless `.flac` audio files.
- FFmpeg: If `ffmpeg` is not installed, the app will download a Windows FFmpeg ZIP, extract it to `./ffmpeg/bin` and use it for conversions.
- Test: Start the app, paste a YouTube URL, select `FLAC` as Format, and click `Download`. Check the output folder for a `.flac` file.
- Note: Downloads and conversions may take time depending on your network and CPU.

Build Windows GUI EXE (no console)
---
1. Ensure `pyinstaller` is installed: `pip install pyinstaller`.
2. Run the included script `build_no_console.bat` (double-click or run in PowerShell/Command Prompt).
3. Output EXE will be in `dist\EasyDownload\EasyDownload.exe` and will use `EasyDownload.ico` from the project root.

Tip: If the icon doesn't appear, ensure the ICO file is a valid Windows icon (contains proper icon sizes).

Gui :

<img width="690" height="498" alt="image" src="https://github.com/user-attachments/assets/063721a8-bc6e-471c-8b00-7b82403394ef" />
