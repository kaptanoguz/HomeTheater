import os
import sys
import re
import json
import threading
import socket
import time
import queue
import io
import zipfile
import traceback
import hashlib
import subprocess
import webbrowser
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, send_file, Response
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Directory Setup ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CACHE_FILE = os.path.join(BASE_DIR, "data_cache.json")
POSTERS_DIR = os.path.join(BASE_DIR, "static", "posters")

# Default config — no API keys or paths hardcoded
DEFAULT_CONFIG = {
    "movie_dir": "",
    "series_dir": "",
    "omdb_api_key": "",
    "opensubtitles_api_key": ""
}

app = Flask(__name__)

# HTTP session with retry logic
retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)
http.headers.update({'User-Agent': 'HomeTheater/1.0'})


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                return {**DEFAULT_CONFIG, **loaded}
        except Exception:
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(conf):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(conf, f, indent=4)
    except Exception:
        pass


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"movies": [], "series": {}}


def save_cache():
    data = {"movies": movies_data, "series": series_data}
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


config = load_config()
cached_data = load_cache()

movies_data = cached_data.get('movies', [])
series_data = cached_data.get('series', {})
metadata_queue = queue.Queue()
is_scanning = False

# Global ID counters
mid = 1
sid = 1
if movies_data:
    mid = max(m['id'] for m in movies_data) + 1
for s in series_data.values():
    for ss in s.get('seasons', {}).values():
        for ep in ss:
            if ep['id'] >= sid:
                sid = ep['id'] + 1


def get_smart_title(path):
    """Extract a clean movie/series title from a filename."""
    filename = os.path.basename(path)
    name = os.path.splitext(filename)[0]

    year = ""
    y_match = re.search(r'[\(\[\.\s](19\d{2}|20\d{2})[\)\]\.\s]', name)
    if y_match:
        year = y_match.group(1)
        name = name[:y_match.start()]

    name = re.sub(r'[\.\-_]', ' ', name)

    junk = ['1080p', '720p', '480p', 'BluRay', 'WEB-DL', 'DVDRip',
            'x264', 'x265', 'AAC', 'DTS', 'HDR', 'BrRip', 'WEBRip']
    for j in junk:
        name = re.sub(r'\b' + j + r'\b', '', name, flags=re.IGNORECASE)

    name = re.sub(r'\s+', ' ', name).strip()

    candidates = [name]
    if ':' in name:
        candidates.append(name.replace(':', ''))

    return candidates, year


def find_local_subtitle(video_path):
    """Find a local subtitle file next to the video."""
    base = os.path.splitext(video_path)[0]
    for ext in ['.srt', '.vtt', '.sub']:
        if os.path.exists(base + ext):
            return base + ext
        if os.path.exists(base + ".en" + ext):
            return base + ".en" + ext
        if os.path.exists(base + ".tr" + ext):
            return base + ".tr" + ext
    return None


def srt_to_vtt(srt_content):
    """Convert SRT subtitle format to VTT."""
    return "WEBVTT\n\n" + re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})', r'\1.\2', srt_content)


def _validate_path(path):
    """Validate that a file path is within configured directories."""
    real_path = os.path.realpath(path)
    movie_dir = os.path.realpath(config.get('movie_dir', ''))
    series_dir = os.path.realpath(config.get('series_dir', ''))
    if movie_dir and real_path.startswith(movie_dir):
        return True
    if series_dir and real_path.startswith(series_dir):
        return True
    return False


def scan_videos():
    """Scan configured directories for video files."""
    global is_scanning, mid, sid
    is_scanning = True
    exts = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v')

    existing_movies = {m['path']: m for m in movies_data}
    existing_movies_by_name = {os.path.basename(m['path']): m for m in movies_data}

    new_movies = []
    new_series = defaultdict(lambda: defaultdict(list))

    if config.get('movie_dir') and os.path.exists(config['movie_dir']):
        for root, _, files in os.walk(config['movie_dir']):
            for f in files:
                if f.lower().endswith(exts):
                    if re.search(r'[Ss]\d+[Ee]\d+', f, re.IGNORECASE):
                        continue
                    path = os.path.join(root, f)

                    m = existing_movies.get(path)
                    if not m:
                        m = existing_movies_by_name.get(f)
                        if m:
                            m['path'] = path

                    if m:
                        if not m.get('rating'):
                            metadata_queue.put(m)
                        new_movies.append(m)
                    else:
                        c, y = get_smart_title(path)
                        m = {
                            'id': mid, 'title': c[0], 'candidates': c,
                            'year': y, 'path': path,
                            'poster': '/static/placeholder.png',
                            'rating': '', 'plot': ''
                        }
                        new_movies.append(m)
                        metadata_queue.put(m)
                        mid += 1
    movies_data[:] = new_movies

    if config.get('series_dir') and os.path.exists(config['series_dir']):
        for root, _, files in os.walk(config['series_dir']):
            for f in files:
                if f.lower().endswith(exts):
                    try:
                        path = os.path.join(root, f)
                        sm = re.search(r'[Ss](\d+)', f) or re.search(r'Season\s*(\d+)', f)
                        em = re.search(r'[Ee](\d+)', f) or re.search(r'Episode\s*(\d+)', f)
                        if sm and em:
                            s, e = int(sm.group(1)), int(em.group(1))
                            c, y = get_smart_title(path)
                            sname = c[0]
                            if re.search(r'[Ss]\d+[Ee]\d+', sname):
                                sname = re.split(r'[Ss]\d+[Ee]\d+', sname)[0].strip()
                            ep = {
                                'id': sid, 'title': sname,
                                'season': s, 'episode': e,
                                'path': path, 'filename': f
                            }
                            new_series[sname][s].append(ep)
                            sid += 1
                    except Exception:
                        pass

    final_series = {}
    for name, seasons in new_series.items():
        meta = None
        if name in series_data and 'meta' in series_data[name]:
            meta = series_data[name]['meta']

        if meta:
            if not meta.get('rating'):
                metadata_queue.put(meta)
        else:
            meta = {
                'id': name, 'title': name, 'candidates': [name],
                'year': '', 'poster': '/static/placeholder.png',
                'rating': '', 'plot': '', 'genre': ''
            }
            metadata_queue.put(meta)
        final_series[name] = {
            'poster': meta.get('poster', ''),
            'rating': meta.get('rating', ''),
            'plot': meta.get('plot', ''),
            'seasons': seasons, 'meta': meta
        }

    series_data.update(final_series)
    is_scanning = False
    save_cache()


# --- Flask Routes ---

@app.route('/')
def index():
    needs_setup = not config.get('movie_dir') and not config.get('series_dir')
    return render_template('index.html', needs_setup=needs_setup)


@app.route('/api/data')
def get_data():
    for s in series_data.values():
        if 'meta' in s:
            s['poster'] = s['meta'].get('poster')
            s['rating'] = s['meta'].get('rating')
            s['plot'] = s['meta'].get('plot')
            s['year'] = s['meta'].get('year')
            s['genre'] = s['meta'].get('genre')
    return jsonify({
        'movies': movies_data,
        'series': series_data,
        'scanning': is_scanning,
        'queue': metadata_queue.qsize()
    })


@app.route('/api/scan', methods=['POST'])
def scan():
    if not is_scanning:
        threading.Thread(target=scan_videos, daemon=True).start()
    return jsonify({'status': 'started'})


@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        return jsonify(config)
    config.update(request.json)
    save_config(config)
    return jsonify({'status': 'ok'})


@app.route('/get_poster/<path:vid>')
def poster(vid):
    # Sanitize the vid parameter
    safe_vid = re.sub(r'[^a-zA-Z0-9_\-]', '', str(vid))
    p = os.path.join(POSTERS_DIR, f"poster_{safe_vid}.jpg")
    if os.path.exists(p) and os.path.realpath(p).startswith(os.path.realpath(POSTERS_DIR)):
        return send_file(p)
    return "", 404


@app.route('/play/<int:vid>')
def play(vid):
    target = next((m for m in movies_data if m['id'] == vid), None)
    if not target:
        for s in series_data.values():
            for ss in s.get('seasons', {}).values():
                for ep in ss:
                    if ep['id'] == vid:
                        target = ep
                        break

    if not target:
        return "Not Found", 404

    path = target['path']

    # Security: validate path is within allowed directories
    if not _validate_path(path):
        return "Forbidden", 403

    if not os.path.exists(path):
        return "File Not Found", 404

    # Transcode non-native formats via ffmpeg
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.avi', '.wmv', '.flv', '.divx']:
        cmd = [
            'ffmpeg', '-i', path, '-c:v', 'libx264',
            '-preset', 'ultrafast', '-c:a', 'aac',
            '-b:a', '128k', '-f', 'mp4',
            '-movflags', 'frag_keyframe+empty_moov', 'pipe:1'
        ]
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, bufsize=10**8
            )

            def stream():
                try:
                    while True:
                        data = process.stdout.read(1024 * 1024)
                        if not data:
                            break
                        yield data
                finally:
                    process.kill()
            return Response(stream(), mimetype="video/mp4")
        except Exception:
            pass

    try:
        size = os.path.getsize(path)
    except Exception:
        return "Error", 404

    start, length = 0, size
    range_header = request.headers.get('Range', None)
    if range_header:
        m = re.search(r'(\d+)-(\d*)', range_header)
        if m:
            start = int(m.group(1))
            if m.group(2):
                length = int(m.group(2)) - start + 1
            else:
                length = size - start

    chunk = 5 * 1024 * 1024

    def generate():
        with open(path, 'rb') as f:
            f.seek(start)
            rem = length
            while rem > 0:
                data = f.read(min(chunk, rem))
                if not data:
                    break
                rem -= len(data)
                yield data

    r = Response(generate(), 206, mimetype="video/mp4", direct_passthrough=True)
    r.headers.add('Content-Range', f'bytes {start}-{start+length-1}/{size}')
    return r


@app.route('/subtitle/<int:vid>')
def sub(vid):
    target = next((m for m in movies_data if m['id'] == vid), None)
    if not target:
        for s in series_data.values():
            for ss in s.get('seasons', {}).values():
                for ep in ss:
                    if ep['id'] == vid:
                        target = ep
                        break

    if target:
        local_sub = find_local_subtitle(target['path'])
        if local_sub:
            try:
                encodings = ['utf-8', 'cp1254', 'iso-8859-9', 'latin-1']
                content = None
                for enc in encodings:
                    try:
                        with open(local_sub, 'r', encoding=enc, errors='strict') as f:
                            content = f.read()
                        break
                    except Exception:
                        continue

                if not content:
                    try:
                        with open(local_sub, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    except Exception:
                        pass

                if content:
                    if local_sub.endswith('.vtt'):
                        return Response(content, mimetype="text/vtt")
                    vtt_content = srt_to_vtt(content)
                    return Response(vtt_content, mimetype="text/vtt")
            except Exception:
                pass
    return "", 404


# --- Subtitle Search (OpenSubtitles API) ---

@app.route('/api/search_subs_hash/<int:vid>')
def search_subs_by_hash(vid):
    api_key = config.get('opensubtitles_api_key', '')
    if not api_key:
        return jsonify({'error': 'OpenSubtitles API key not configured'}), 400

    target = next((m for m in movies_data if m['id'] == vid), None)
    if not target:
        for s in series_data.values():
            for ss in s.get('seasons', {}).values():
                for ep in ss:
                    if ep['id'] == vid:
                        target = ep
                        break

    if not target:
        return jsonify([])

    path = target['path']
    if not _validate_path(path):
        return jsonify([])

    moviehash = None
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as f:
            data = f.read(65536)
            f.seek(max(0, size - 65536))
            data += f.read(65536)
        moviehash = hashlib.md5(data).hexdigest()
    except Exception:
        pass

    results = []
    headers = {
        'Api-Key': api_key,
        'Content-Type': 'application/json',
        'User-Agent': 'HomeTheater/1.0'
    }

    # Search by hash
    if moviehash:
        url = f"https://api.opensubtitles.com/api/v1/subtitles?moviehash={moviehash}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for item in data.get('data', []):
                    attr = item['attributes']
                    if attr['language'] in ['tr', 'en']:
                        results.append({
                            'file_id': attr['files'][0]['file_id'],
                            'title': f"[HASH] {attr['language']} - {attr['release']}",
                            'dl_count': attr['download_count']
                        })
        except Exception:
            pass

    # Fallback: search by title
    if len(results) < 5:
        query = target['title']
        if target.get('year'):
            query += f" {target['year']}"

        url = "https://api.opensubtitles.com/api/v1/subtitles"
        params = {'query': query}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for item in data.get('data', []):
                    attr = item['attributes']
                    if attr['language'] in ['tr', 'en']:
                        if not any(r['file_id'] == attr['files'][0]['file_id'] for r in results):
                            results.append({
                                'file_id': attr['files'][0]['file_id'],
                                'title': f"[NAME] {attr['language']} - {attr['release']}",
                                'dl_count': attr['download_count']
                            })
        except Exception:
            pass

    results.sort(key=lambda x: x['dl_count'], reverse=True)
    return jsonify(results)


@app.route('/api/download_sub_hash', methods=['POST'])
def download_sub_hash():
    api_key = config.get('opensubtitles_api_key', '')
    if not api_key:
        return "API key not configured", 400

    fid = request.json.get('file_id')
    if not fid:
        return "No file ID provided", 400

    url = "https://api.opensubtitles.com/api/v1/download"
    headers = {
        'Api-Key': api_key,
        'Content-Type': 'application/json',
        'User-Agent': 'HomeTheater/1.0'
    }

    try:
        r = requests.post(url, headers=headers, json={'file_id': fid}, timeout=10)
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

                vtt = "WEBVTT\n\n" + re.sub(
                    r'(\d{2}:\d{2}:\d{2}),(\d{3})', r'\1.\2', decoded
                )
                return Response(vtt, mimetype="text/vtt")
    except Exception:
        pass
    return "Download failed", 500


# --- Metadata Worker ---

def metadata_worker():
    """Background worker that fetches movie metadata from OMDB."""
    while True:
        item = metadata_queue.get()
        if item is None:
            break

        apikey = config.get('omdb_api_key', '')
        if not apikey:
            continue

        title = item['title']
        year = item.get('year', '')

        try:
            u = f"http://www.omdbapi.com/?apikey={apikey}&t={title}"
            if year:
                u += f"&y={year}"

            res = http.get(u, timeout=10).json()
            if res.get('Response') == 'True':
                item['rating'] = res.get('imdbRating', 'N/A')
                item['plot'] = res.get('Plot', '')
                item['genre'] = res.get('Genre', '')
                item['year'] = res.get('Year', year)

                poster_url = res.get('Poster')
                if poster_url and poster_url != 'N/A':
                    try:
                        img_data = http.get(poster_url, timeout=10).content
                        local_name = f"poster_{item['id']}.jpg"
                        local_path = os.path.join(POSTERS_DIR, local_name)

                        if not os.path.exists(POSTERS_DIR):
                            os.makedirs(POSTERS_DIR)

                        with open(local_path, 'wb') as f:
                            f.write(img_data)

                        item['poster'] = f"/get_poster/{item['id']}"
                    except Exception:
                        pass

                # Update series metadata
                if 'seasons' in item:
                    if item['id'] in series_data:
                        series_data[item['id']]['meta'] = item

                save_cache()
        except Exception:
            pass
        time.sleep(1)


threading.Thread(target=metadata_worker, daemon=True).start()


# --- Main Entry Point ---

if __name__ == '__main__':
    webview = None
    should_try_webview = True

    if sys.platform.startswith('linux'):
        try:
            import gi  # noqa: F401
        except ImportError:
            should_try_webview = False
            print("System libraries (python3-gi) not found. Opening in browser.")

    if should_try_webview:
        try:
            import webview
        except Exception:
            print("pywebview not available. Opening in browser.")
            webview = None

    def start_server():
        from waitress import serve
        print("Server starting at http://127.0.0.1:5000")
        serve(app, host='127.0.0.1', port=5000, threads=20)

    try:
        t_scan = threading.Thread(target=scan_videos, daemon=True)
        t_scan.start()
        t_server = threading.Thread(target=start_server, daemon=True)
        t_server.start()

        time.sleep(1)

        if webview:
            try:
                webview.create_window(
                    'Home Theater',
                    'http://127.0.0.1:5000',
                    width=1280, height=800,
                    confirm_close=True,
                    background_color='#000000'
                )
                webview.start()
            except Exception as e:
                print(f"Webview error: {e}")
                print("Opening in browser...")
                webbrowser.open('http://127.0.0.1:5000')
                while True:
                    time.sleep(1)
        else:
            print("Opening in browser...")
            webbrowser.open('http://127.0.0.1:5000')
            while True:
                time.sleep(1)

    except Exception as e:
        with open("error_log.txt", "w") as f:
            f.write(str(e))
            traceback.print_exc(file=f)
