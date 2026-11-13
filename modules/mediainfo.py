"""
mediainfo.py - Describe media links posted on the channel
Copyright 2026, Rolle Laukkarinen
Licensed under the Eiffel Forum License 2.
"""
import base64
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse

import requests
import sopel.module
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sopel import logger

LOGGER = logger.get_logger(__name__)
load_dotenv('/home/rolle/.sopel/.env')

API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")
API_MODEL = "google/gemini-3.1-flash-lite"

CACHE_FILE = '/home/rolle/.sopel/media_cache.json'
CACHE_MAX = 200
REPOST_SECONDS = 600

HEADER_BYTES = 65536
MAX_REDIRECTS = 3
CLIENT_NAME = 'kummitus-ircbot/1.0 (+https://github.com/pulinairc/kummitus)'

IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff', '.avif')
OTHER_EXT = ('.mp4', '.webm', '.mkv', '.mov', '.m4v', '.mp3', '.ogg', '.oga',
             '.wav', '.flac', '.opus', '.pdf')

# Hosts that serve an image behind an HTML page, resolved via og:image
PAGE_HOSTS = (
    'imgur.com', 'ibb.co', 'imgbb.com', 'postimg.cc', 'postimages.org',
    'prnt.sc', 'snipboard.io', 'gyazo.com', 'lightshot.com', 'flickr.com',
)

VIDEO_TIMEOUT = 30
FRAME_WIDTH = 640

LABELS = {'image': 'Kuva', 'video': 'Video', 'audio': 'Ääni', 'pdf': 'PDF'}

url_pattern = re.compile(r'(?<!\S)(https?://\S+)', re.IGNORECASE)
_recent = {}


def human_size(num):
    if num is None:
        return None
    for unit in ('B', 'KB', 'MB', 'GB'):
        if num < 1024 or unit == 'GB':
            return '%d %s' % (num, unit) if unit == 'B' else '%.2f %s' % (num, unit)
        num /= 1024.0


def is_public_url(url):
    """Reject anything that is not a public http(s) host.
    IRC users choose these URLs, and this box runs local-only services.
    """
    parts = urlparse(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or
                                   (443 if parts.scheme == 'https' else 80))
    except Exception as e:
        LOGGER.debug('DNS failed for %s: %s' % (parts.hostname, e))
        return False
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_multicast or addr.is_reserved or addr.is_unspecified):
            return False
    return True


def fetch_head(url):
    """Follow redirects by hand so every hop is checked, then read the leading
    bytes. Returns (final_url, content_type, total_size, head_bytes).
    """
    seen = url
    for _ in range(MAX_REDIRECTS + 1):
        if not is_public_url(seen):
            return None, None, None, None
        response = requests.get(seen, stream=True, timeout=12, allow_redirects=False,
                                headers={'User-Agent': CLIENT_NAME})
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get('location')
            response.close()
            if not location:
                return None, None, None, None
            seen = urljoin(seen, location)
            continue
        with response:
            if response.status_code != 200:
                return None, None, None, None
            ctype = response.headers.get('content-type', '').split(';')[0].strip().lower()
            length = response.headers.get('content-length')
            total = int(length) if length and length.isdigit() else None
            head = response.raw.read(HEADER_BYTES, decode_content=True)
        return seen, ctype, (total if total is not None else len(head)), head
    return None, None, None, None


def image_size(data):
    """Width and height straight from the file header, no Pillow needed."""
    try:
        if data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR':
            return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')

        if data[:6] in (b'GIF87a', b'GIF89a'):
            return int.from_bytes(data[6:8], 'little'), int.from_bytes(data[8:10], 'little')

        if data[:2] == b'BM':
            return int.from_bytes(data[18:22], 'little'), int.from_bytes(data[22:26], 'little')

        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            chunk = data[12:16]
            if chunk == b'VP8 ':
                return (int.from_bytes(data[26:28], 'little') & 0x3fff,
                        int.from_bytes(data[28:30], 'little') & 0x3fff)
            if chunk == b'VP8L':
                bits = int.from_bytes(data[21:25], 'little')
                return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
            if chunk == b'VP8X':
                return (int.from_bytes(data[24:27], 'little') + 1,
                        int.from_bytes(data[27:30], 'little') + 1)

        if data[:2] == b'\xff\xd8':
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xff:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7,
                              0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                    return (int.from_bytes(data[i + 7:i + 9], 'big'),
                            int.from_bytes(data[i + 5:i + 7], 'big'))
                if marker in (0xd8, 0xd9) or 0xd0 <= marker <= 0xd7:
                    i += 2
                    continue
                i += 2 + int.from_bytes(data[i + 2:i + 4], 'big')
    except Exception as e:
        LOGGER.debug('Dimension parse failed: %s' % e)
    return None, None


def kind_of(url, ctype):
    if ctype.startswith('image/'):
        return 'image'
    if ctype.startswith('video/'):
        return 'video'
    if ctype.startswith('audio/'):
        return 'audio'
    if ctype == 'application/pdf':
        return 'pdf'
    if urlparse(url).path.lower().endswith(IMAGE_EXT):
        return 'image'
    return None


def type_name(url, ctype):
    if ctype and '/' in ctype:
        subtype = ctype.split('/')[1]
        if subtype != 'octet-stream':
            return subtype.replace('jpeg', 'jpg').replace('quicktime', 'mov').upper()
    ext = os.path.splitext(urlparse(url).path)[1].lstrip('.').upper()
    return ext or 'TUNTEMATON'


def resolve_page(url):
    """Turn an image-host page into the direct image URL via og:image."""
    if not is_public_url(url):
        return None
    try:
        response = requests.get(url, timeout=12, headers={'User-Agent': CLIENT_NAME})
        if response.status_code != 200:
            return None
        if 'html' not in response.headers.get('content-type', ''):
            return None
        soup = BeautifulSoup(response.content[:400000], 'html.parser')
        for prop in ('og:image', 'twitter:image', 'og:image:secure_url'):
            tag = soup.find('meta', attrs={'property': prop}) or \
                soup.find('meta', attrs={'name': prop})
            if tag and tag.get('content'):
                return urljoin(url, tag['content'])
    except Exception as e:
        LOGGER.debug('og:image lookup failed for %s: %s' % (url, e))
    return None


def direct_url(url):
    """A Dropbox share link opens a web page; with raw=1 it serves the file itself."""
    parts = urlparse(url)
    host = (parts.hostname or '').lower()
    if host not in ('dropbox.com', 'www.dropbox.com'):
        return url
    if not parts.path.startswith(('/scl/fi/', '/s/')):
        return url
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != 'dl']
    return parts._replace(query=urlencode(query + [('raw', '1')])).geturl()


def candidate_url(url):
    """The direct media URL for a posted link, or None when it is not media."""
    clean = direct_url(url.rstrip('.,;:!?)]}\'"'))
    path = urlparse(clean).path.lower()
    if path.endswith(IMAGE_EXT) or path.endswith(OTHER_EXT):
        return clean
    host = (urlparse(clean).hostname or '').lower()
    host = host[4:] if host.startswith('www.') else host
    if any(host == h or host.endswith('.' + h) for h in PAGE_HOSTS):
        return resolve_page(clean)
    return None


def describe_image(url):
    """One short Finnish sentence about the picture, from the cheap model."""
    if not API_KEY:
        return None
    try:
        response = requests.post(
            API_URL,
            json={
                'model': API_MODEL,
                'messages': [{'role': 'user', 'content': [
                    {'type': 'text', 'text':
                        'Kuvaile kuva yhdellä lyhyellä suomenkielisellä lauseella, '
                        'enintään 120 merkkiä. Pelkkä kuvaus, ei johdantoa, ei '
                        'lainausmerkkejä, ei emojeita, ei loppupistettä.'},
                    {'type': 'image_url', 'image_url': {'url': url}},
                ]}],
                'max_tokens': 120,
                'temperature': 0.3,
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer %s' % API_KEY,
                'HTTP-Referer': 'https://github.com/pulinairc/kummitus',
                'X-Title': 'kummitus',
            },
            timeout=45,
        )
        if response.status_code != 200:
            LOGGER.error('[MEDIA] API %s: %s' % (response.status_code, response.text[:200]))
            return None
        text = response.json()['choices'][0]['message']['content'] or ''
        text = ' '.join(text.split()).strip(' "\'').rstrip('.')
        return text[:160] or None
    except Exception as e:
        LOGGER.error('[MEDIA] Description failed: %s' % e)
        return None


def load_cache():
    try:
        with open(CACHE_FILE, 'r') as handle:
            return json.loads(handle.read())
    except Exception:
        return {}


def save_cache(cache):
    if len(cache) > CACHE_MAX:
        oldest = sorted(cache.items(), key=lambda kv: kv[1].get('ts', 0))
        cache = dict(oldest[-CACHE_MAX:])
    try:
        with open(CACHE_FILE, 'w') as handle:
            handle.write(json.dumps(cache, ensure_ascii=False, indent=1))
    except Exception as e:
        LOGGER.error('[MEDIA] Cache write failed: %s' % e)
    return cache


def clock(seconds):
    s = int(round(seconds))
    h, m = divmod(s // 60, 60)
    return '%d:%02d:%02d' % (h, m, s % 60) if h else '%d:%02d' % (m, s % 60)


def ffmpeg_args(url):
    # Only the web: ffmpeg must not be talked into reading local files.
    return ['-protocol_whitelist', 'https,http,tls,tcp', '-rw_timeout', '15000000', '-i', url]


def video_facts(url):
    """Size, length and a still from the start of a video, when ffmpeg is on the server."""
    facts = {}
    if not shutil.which('ffprobe'):
        return facts
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
             'stream=width,height:format=duration', '-of', 'json'] + ffmpeg_args(url),
            capture_output=True, timeout=VIDEO_TIMEOUT, check=False).stdout
        info = json.loads(out or b'{}')
        stream = (info.get('streams') or [{}])[0]
        if stream.get('width') and stream.get('height'):
            facts['dimensions'] = '%dx%d' % (stream['width'], stream['height'])
        duration = float((info.get('format') or {}).get('duration') or 0)
        if duration:
            facts['duration'] = clock(duration)
    except Exception as e:
        LOGGER.debug('[MEDIA] ffprobe failed for %s: %s' % (url, e))
        return facts
    if not shutil.which('ffmpeg'):
        return facts
    try:
        at = min(1.0, duration / 10) if duration else 0
        still = subprocess.run(
            ['ffmpeg', '-v', 'error', '-ss', '%.2f' % at] + ffmpeg_args(url) +
            ['-frames:v', '1', '-vf', 'scale=%d:-2' % FRAME_WIDTH, '-f', 'image2', '-c:v', 'mjpeg', 'pipe:1'],
            capture_output=True, timeout=VIDEO_TIMEOUT, check=False).stdout
        if still:
            facts['description'] = describe_image('data:image/jpeg;base64,' + base64.b64encode(still).decode())
    except Exception as e:
        LOGGER.debug('[MEDIA] Still failed for %s: %s' % (url, e))
    return facts


def describe_media(url):
    """Build the facts for one media URL, reusing the cache when possible."""
    cache = load_cache()
    if url in cache:
        return cache[url]

    target = candidate_url(url)
    if not target:
        return None

    final, ctype, size, head = fetch_head(target)
    if not final:
        return None

    kind = kind_of(final, ctype or '')
    if not kind:
        return None

    width, height = image_size(head) if kind == 'image' else (None, None)
    entry = {
        'label': LABELS[kind],
        'type': type_name(final, ctype),
        'size': human_size(size),
        'dimensions': '%dx%d' % (width, height) if width and height else None,
        'description': describe_image(final) if kind == 'image' else None,
        'duration': None,
        'url': final,
        'ts': time.time(),
    }
    if kind == 'video':
        entry.update(video_facts(final))
    cache[url] = entry
    save_cache(cache)
    return entry


def format_line(entry):
    parts = [entry['type'], entry.get('size'), entry.get('dimensions'),
             entry.get('duration'), entry.get('description')]
    return '\x02%s:\x0F %s' % (entry['label'], ' • '.join(p for p in parts if p))


@sopel.module.rule(r'(?u).*https?://\S+.*')
@sopel.module.require_chanmsg
def media_auto(bot, trigger):
    if trigger.nick == bot.nick:
        return

    now = time.time()
    for url in url_pattern.findall(trigger.group(0))[:2]:
        if url.startswith(getattr(bot.config.url, 'exclusion_char', '!')):
            continue
        if now - _recent.get(url, 0) < REPOST_SECONDS:
            continue
        try:
            entry = describe_media(url)
        except Exception as e:
            LOGGER.error('[MEDIA] %s failed: %s' % (url, e))
            continue
        if entry:
            _recent[url] = now
            bot.say(format_line(entry), trigger.sender)


@sopel.module.commands('media', 'kuva')
@sopel.module.require_chanmsg
def media_command(bot, trigger):
    """Kerro mitä annetussa medialinkissä on."""
    arg = trigger.group(2)
    url = (arg or '').strip() or bot.memory.get('last_seen_url', {}).get(trigger.sender)
    if not url:
        bot.say('%s: Anna medialinkki.' % trigger.nick, trigger.sender)
        return
    entry = describe_media(url)
    if entry:
        bot.say(format_line(entry), trigger.sender)
    else:
        bot.say('%s: Tuo ei näytä medialinkiltä.' % trigger.nick, trigger.sender)
