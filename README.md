# Home Theater

A modern, self-hosted media catalog and player for your local movie and TV series collection.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-Web_App-green)
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
- 📺 **TV Series** — browse by season and episode with a Netflix-style interface

## Screenshots

> Launch the app and set up your directories to see it in action!

## Installation

### From .deb Package (Recommended)

Download the latest `.deb` from [Releases](https://github.com/kaptanoguz/HomeTheater/releases):

```bash
sudo dpkg -i home-theater_1.0.0_amd64.deb
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
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

**System dependencies (optional, for native window):**

```bash
sudo apt install python3-gi gir1.2-webkit2-4.1
```

Without these, the app opens in your default web browser.

## Setup

On first launch, you'll see a **Welcome** screen where you configure:

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
3. **Playback** — Videos stream directly through your browser. Formats like `.avi` and `.wmv` are automatically transcoded via ffmpeg
4. **Subtitles** — Local `.srt`/`.vtt` files are auto-detected. You can also search OpenSubtitles or drag-and-drop subtitle files

## Dependencies

- Python 3.8+
- Flask & Waitress (production WSGI server)
- ffmpeg (for non-native video format transcoding)

## License

This project is licensed under the [GPL-3.0 License](LICENSE).

## Author

**kaptanoguz** — [GitHub](https://github.com/kaptanoguz)
