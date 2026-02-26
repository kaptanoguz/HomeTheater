# Home Theater

A modern, native desktop application to catalog and play your local movie and TV series collection.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-Desktop_App-green)
![License](https://img.shields.io/badge/License-GPL--3.0-red)
![Platform](https://img.shields.io/badge/Platform-Linux-yellow)

## Features

- 🎬 **Auto-scan** your local movie and TV series directories
- 📋 **Metadata & Posters** fetched automatically from OMDB/IMDb
- 🎲 **Shuffle** — get random movie suggestions
- ⭐ **Ratings & Genres** — filter, sort, and search your library
- ❤️ **Favorites** — mark and filter your favorite titles
- 🎥 **Built-in Player** — watch directly in the app with subtitle support
- 📝 **Subtitle Search** — find and download subtitles from OpenSubtitles
- 📺 **TV Series** — browse by season and episode
- 🌙 **Dark Theme** — Netflix-inspired dark UI

## Project Structure

```
HomeTheater/
├── main.py                # PyQt5 desktop application (UI)
├── backend.py             # Config, cache, scanning, metadata
├── requirements.txt       # PyQt5 dependencies
├── flask-web-version/     # Alternative Web/HTML based version
│   ├── app.py
│   ├── templates/
│   └── requirements.txt
├── LICENSE
└── README.md
```

Home Theater comes in two versions:
1. **Native Desktop App (Default)** — Built with PyQt5. Best for daily desktop use.
2. **Web Version (`flask-web-version/`)** — Built with Flask and HTML/JS. Best if you want to run it on a server and access it from a browser.

## Installation

### From .deb Package (Recommended)

Download the latest `.deb` from [Releases](https://github.com/kaptanoguz/HomeTheater/releases):

```bash
sudo dpkg -i home-theater_2.0.0_amd64.deb
sudo apt install -f  # Install any missing dependencies
```

Then launch from your application menu, or run:

```bash
home-theater
```

### From Source

```bash
git clone https://github.com/kaptanoguz/HomeTheater.git
cd HomeTheater
pip install -r requirements.txt
python main.py
```

*Note: If you prefer the web-based version, navigate to the `flask-web-version` directory and run `app.py` instead.*

**System dependencies:**

```bash
sudo apt install python3-pyqt5 python3-pyqt5.qtmultimedia \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-libav ffmpeg
```

## Setup

On first launch, a **Welcome** dialog will prompt you to configure:

| Setting | Description |
|---------|-------------|
| **Movies Directory** | Path to your movies folder (e.g. `/home/user/Movies`) |
| **TV Series Directory** | Path to your TV series folder (e.g. `/home/user/Series`) |
| **OMDB API Key** | For fetching posters and metadata |
| **OpenSubtitles API Key** | For searching and downloading subtitles (optional) |

### Getting Your API Keys

#### OMDB API Key (for posters & metadata)

1. Go to [https://www.omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)
2. Select **FREE** tier (1,000 daily requests)
3. Enter your email and submit
4. Check your email for the API key
5. Paste it into Home Theater settings

#### OpenSubtitles API Key (for subtitles, optional)

1. Create an account at [https://www.opensubtitles.com](https://www.opensubtitles.com)
2. Go to [https://www.opensubtitles.com/consumers](https://www.opensubtitles.com/consumers)
3. Register a new consumer/app to get your API key
4. Paste it into Home Theater settings

## How It Works

1. **Scanning** — The app scans your configured directories for video files (`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`)
2. **Metadata** — For each video, it extracts a clean title from the filename and queries OMDB for poster, rating, plot, and genre
3. **Browsing** — Movies display in a responsive poster grid; TV series open in a season/episode browser
4. **Playback** — Videos play in the built-in Qt media player. GStreamer handles format decoding
5. **Subtitles** — Local `.srt`/`.vtt` files are auto-detected. You can also search OpenSubtitles

## Technology Stack

- **Python 3.8+** — Core language
- **PyQt5** — Native desktop UI framework
- **GStreamer** — Media playback backend
- **OMDB API** — Movie metadata and posters
- **OpenSubtitles API** — Subtitle search and download

## License

This project is licensed under the [GPL-3.0 License](LICENSE).

## Author

**kaptanoguz** — [GitHub](https://github.com/kaptanoguz)
