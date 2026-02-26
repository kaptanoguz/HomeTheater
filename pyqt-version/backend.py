"""
Home Theater — Backend module
Handles configuration, cache, video scanning, and metadata fetching.
"""

import os
import sys
import re
import json
import hashlib
import threading
import queue
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict


def get_data_dir():
    """Get the application data directory."""
    data_dir = os.path.join(os.path.expanduser("~"), ".home-theater")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


DATA_DIR = get_data_dir()
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
CACHE_FILE = os.path.join(DATA_DIR, "data_cache.json")
POSTERS_DIR = os.path.join(DATA_DIR, "posters")
os.makedirs(POSTERS_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "movie_dir": "",
    "series_dir": "",
    "omdb_api_key": "",
    "opensubtitles_api_key": ""
}

# HTTP session with retry
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
_adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", _adapter)
http.mount("http://", _adapter)
http.headers.update({'User-Agent': 'HomeTheater/2.0'})

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v')


class Config:
    """Manages application configuration."""

    def __init__(self):
        self._data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self._data = {**DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                self._data = dict(DEFAULT_CONFIG)

    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._data, f, indent=4)
        except Exception:
            pass

    def get(self, key, default=""):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def update(self, data):
        self._data.update(data)
        self.save()

    @property
    def needs_setup(self):
        return not self._data.get("movie_dir") and not self._data.get("series_dir")


class Cache:
    """Manages movie/series cache."""

    def __init__(self):
        self.movies = []
        self.series = {}
        self.load()

    def load(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.movies = data.get("movies", [])
                    self.series = data.get("series", {})
            except Exception:
                pass

    def save(self):
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({"movies": self.movies, "series": self.series},
                          f, indent=4, ensure_ascii=False)
        except Exception:
            pass


def get_smart_title(path):
    """Extract a clean title and year from a video filename."""
    filename = os.path.basename(path)
    name = os.path.splitext(filename)[0]

    year = ""
    y_match = re.search(r'[\(\[\.\s](19\d{2}|20\d{2})[\)\]\.\s]', name)
    if y_match:
        year = y_match.group(1)
        name = name[:y_match.start()]

    name = re.sub(r'[\.\-_]', ' ', name)
    junk = ['1080p', '720p', '480p', 'BluRay', 'WEB-DL', 'DVDRip',
            'x264', 'x265', 'AAC', 'DTS', 'HDR', 'BrRip', 'WEBRip',
            'REMUX', 'HEVC', 'H264', 'H265', 'IMAX', 'YIFY', 'RARBG']
    for j in junk:
        name = re.sub(r'\b' + j + r'\b', '', name, flags=re.IGNORECASE)

    name = re.sub(r'\s+', ' ', name).strip()
    return name, year


def find_local_subtitle(video_path):
    """Find a subtitle file next to the video file."""
    base = os.path.splitext(video_path)[0]
    for ext in ['.srt', '.vtt', '.sub']:
        for suffix in ['', '.en', '.tr']:
            candidate = base + suffix + ext
            if os.path.exists(candidate):
                return candidate
    return None


class Scanner(threading.Thread):
    """Background thread that scans directories for video files."""

    def __init__(self, config, cache, callback=None):
        super().__init__(daemon=True)
        self.config = config
        self.cache = cache
        self.callback = callback
        self.scanning = False
        self.progress_text = ""
        self.metadata_queue = queue.Queue()
        self._mid = 1
        self._sid = 1

        # Initialize counters from cache
        if self.cache.movies:
            self._mid = max(m['id'] for m in self.cache.movies) + 1
        for s in self.cache.series.values():
            for ss in s.get('seasons', {}).values():
                for ep in ss:
                    if ep['id'] >= self._sid:
                        self._sid = ep['id'] + 1

    def run(self):
        self.scanning = True
        self.progress_text = "Scanning directories..."
        self._scan_movies()
        self._scan_series()
        self.cache.save()
        self.scanning = False
        self.progress_text = ""

        # Start metadata worker
        self._fetch_metadata()

        if self.callback:
            self.callback()

    def _scan_movies(self):
        movie_dir = self.config.get("movie_dir")
        if not movie_dir or not os.path.exists(movie_dir):
            return

        existing = {m['path']: m for m in self.cache.movies}
        new_movies = []

        for root, _, files in os.walk(movie_dir):
            for f in files:
                if f.lower().endswith(VIDEO_EXTENSIONS):
                    if re.search(r'[Ss]\d+[Ee]\d+', f):
                        continue
                    path = os.path.join(root, f)
                    if path in existing:
                        m = existing[path]
                        if not m.get('rating'):
                            self.metadata_queue.put(m)
                        new_movies.append(m)
                    else:
                        title, year = get_smart_title(path)
                        m = {
                            'id': self._mid, 'title': title,
                            'year': year, 'path': path,
                            'poster': '', 'rating': '', 'plot': '', 'genre': ''
                        }
                        new_movies.append(m)
                        self.metadata_queue.put(m)
                        self._mid += 1

        self.cache.movies = new_movies

    def _scan_series(self):
        series_dir = self.config.get("series_dir")
        if not series_dir or not os.path.exists(series_dir):
            return

        new_series = defaultdict(lambda: defaultdict(list))

        for root, _, files in os.walk(series_dir):
            for f in files:
                if f.lower().endswith(VIDEO_EXTENSIONS):
                    try:
                        path = os.path.join(root, f)
                        sm = re.search(r'[Ss](\d+)', f) or re.search(r'Season\s*(\d+)', f)
                        em = re.search(r'[Ee](\d+)', f) or re.search(r'Episode\s*(\d+)', f)
                        if sm and em:
                            s, e = int(sm.group(1)), int(em.group(1))
                            title, year = get_smart_title(path)
                            sname = title
                            if re.search(r'[Ss]\d+[Ee]\d+', sname):
                                sname = re.split(r'[Ss]\d+[Ee]\d+', sname)[0].strip()
                            ep = {
                                'id': self._sid, 'title': sname,
                                'season': s, 'episode': e,
                                'path': path, 'filename': f
                            }
                            new_series[sname][s].append(ep)
                            self._sid += 1
                    except Exception:
                        pass

        for name, seasons in new_series.items():
            meta = None
            if name in self.cache.series and 'meta' in self.cache.series[name]:
                meta = self.cache.series[name]['meta']

            if not meta:
                meta = {
                    'id': name, 'title': name,
                    'year': '', 'poster': '',
                    'rating': '', 'plot': '', 'genre': ''
                }
                self.metadata_queue.put(meta)
            elif not meta.get('rating'):
                self.metadata_queue.put(meta)

            self.cache.series[name] = {
                'poster': meta.get('poster', ''),
                'rating': meta.get('rating', ''),
                'plot': meta.get('plot', ''),
                'genre': meta.get('genre', ''),
                'year': meta.get('year', ''),
                'seasons': {str(k): v for k, v in seasons.items()},
                'meta': meta
            }

    def _fetch_metadata(self):
        """Fetch metadata from OMDB for all queued items."""
        apikey = self.config.get("omdb_api_key")
        if not apikey:
            return

        count = 0
        while not self.metadata_queue.empty():
            try:
                item = self.metadata_queue.get_nowait()
            except queue.Empty:
                break

            count += 1
            self.progress_text = f"Fetching metadata ({count})..."

            try:
                title = item['title']
                year = item.get('year', '')
                url = f"http://www.omdbapi.com/?apikey={apikey}&t={title}"
                if year:
                    url += f"&y={year}"

                res = http.get(url, timeout=10).json()
                if res.get('Response') == 'True':
                    item['rating'] = res.get('imdbRating', 'N/A')
                    item['plot'] = res.get('Plot', '')
                    item['genre'] = res.get('Genre', '')
                    item['year'] = res.get('Year', year)

                    poster_url = res.get('Poster')
                    if poster_url and poster_url != 'N/A':
                        self._download_poster(item, poster_url)

                    # Update series meta
                    if isinstance(item.get('id'), str) and item['id'] in self.cache.series:
                        self.cache.series[item['id']]['meta'] = item
                        self.cache.series[item['id']]['poster'] = item.get('poster', '')
                        self.cache.series[item['id']]['rating'] = item.get('rating', '')

                    self.cache.save()
            except Exception:
                pass

            if self.callback:
                self.callback()
            time.sleep(0.5)

        self.progress_text = ""
        if self.callback:
            self.callback()

    def _download_poster(self, item, url):
        """Download and cache a poster image."""
        try:
            img_data = http.get(url, timeout=10).content
            item_id = item['id']
            safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(item_id))
            local_path = os.path.join(POSTERS_DIR, f"poster_{safe_id}.jpg")
            with open(local_path, 'wb') as f:
                f.write(img_data)
            item['poster'] = local_path
        except Exception:
            pass


def get_poster_path(item):
    """Get the poster path for an item, or empty string."""
    poster = item.get('poster', '')
    if poster and os.path.exists(poster):
        return poster
    # Check by ID
    safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(item.get('id', '')))
    candidate = os.path.join(POSTERS_DIR, f"poster_{safe_id}.jpg")
    if os.path.exists(candidate):
        return candidate
    return ''


def search_subtitles(config, video_path, title, year=""):
    """Search OpenSubtitles API for subtitles."""
    api_key = config.get('opensubtitles_api_key')
    if not api_key:
        return []

    headers = {
        'Api-Key': api_key,
        'Content-Type': 'application/json',
        'User-Agent': 'HomeTheater/2.0'
    }

    results = []

    # Search by hash
    try:
        size = os.path.getsize(video_path)
        with open(video_path, 'rb') as f:
            data = f.read(65536)
            f.seek(max(0, size - 65536))
            data += f.read(65536)
        moviehash = hashlib.md5(data).hexdigest()

        url = f"https://api.opensubtitles.com/api/v1/subtitles?moviehash={moviehash}"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            for item in r.json().get('data', []):
                attr = item['attributes']
                if attr['language'] in ['tr', 'en']:
                    results.append({
                        'file_id': attr['files'][0]['file_id'],
                        'title': f"[HASH] {attr['language']} - {attr['release']}",
                        'dl_count': attr['download_count']
                    })
    except Exception:
        pass

    # Search by title
    if len(results) < 5:
        query = title
        if year:
            query += f" {year}"
        try:
            r = requests.get(
                "https://api.opensubtitles.com/api/v1/subtitles",
                params={'query': query}, headers=headers, timeout=10
            )
            if r.status_code == 200:
                for item in r.json().get('data', []):
                    attr = item['attributes']
                    if attr['language'] in ['tr', 'en']:
                        fid = attr['files'][0]['file_id']
                        if not any(r['file_id'] == fid for r in results):
                            results.append({
                                'file_id': fid,
                                'title': f"[NAME] {attr['language']} - {attr['release']}",
                                'dl_count': attr['download_count']
                            })
        except Exception:
            pass

    results.sort(key=lambda x: x['dl_count'], reverse=True)
    return results


def download_subtitle(config, file_id):
    """Download a subtitle from OpenSubtitles. Returns VTT content or None."""
    api_key = config.get('opensubtitles_api_key')
    if not api_key:
        return None

    headers = {
        'Api-Key': api_key,
        'Content-Type': 'application/json',
        'User-Agent': 'HomeTheater/2.0'
    }

    try:
        r = requests.post(
            "https://api.opensubtitles.com/api/v1/download",
            headers=headers, json={'file_id': file_id}, timeout=10
        )
        if r.status_code == 200:
            link = r.json().get('link')
            if link:
                sub_content = requests.get(link).content
                try:
                    decoded = sub_content.decode('utf-8')
                except Exception:
                    try:
                        decoded = sub_content.decode('cp1254')
                    except Exception:
                        decoded = sub_content.decode('latin-1', errors='ignore')

                # Convert SRT to VTT
                vtt = "WEBVTT\n\n" + re.sub(
                    r'(\d{2}:\d{2}:\d{2}),(\d{3})', r'\1.\2', decoded
                )
                return vtt
    except Exception:
        pass
    return None
