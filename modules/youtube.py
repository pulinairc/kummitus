"""
youtube.py - Title, uploader, date, length, views and likes for YouTube links
Copyright 2026, Rolle Laukkarinen
Licensed under the Eiffel Forum License 2.
"""
import json
import os
import re
import time
from datetime import date

import requests
import sopel.module
from dotenv import load_dotenv
from sopel import logger

LOGGER = logger.get_logger(__name__)
load_dotenv('/home/rolle/.sopel/.env')

# YouTube's own API gives everything, likes and length too, which the watch page leaves out for servers.
API_URL = 'https://www.googleapis.com/youtube/v3/videos'
API_KEY = os.getenv('YOUTUBE_API_KEY')
ISO_DURATION = re.compile(r'P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?')
GONE = 'Yksityinen tai poistettu video · YouTube'

# With or without https://: youtu.be/<id>, watch?v=<id>, /shorts/, /live/, /embed/, /v/.
YT_RE = re.compile(
    r'(?<![\w/.-])(?:https?://)?(?:www\.|m\.|music\.)?(?:'
    r'youtu\.be/(?P<short>[\w-]{11})'
    r'|youtube\.com/(?:watch\?(?:\S*?&)?v=(?P<watch>[\w-]{11})'
    r'|(?:shorts|live|embed|v)/(?P<path>[\w-]{11})))',
    re.IGNORECASE,
)

# A browser's request with the consent cookie set: without it EU visitors get "Ennen kuin jatkat YouTubeen".
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
    'Accept-Language': 'fi,en;q=0.5',
    'Cookie': 'SOCS=CAI',
}
TIMEOUT = 10
MAX_BYTES = 4 * 1024 * 1024
PLAYER_MARK = 'ytInitialPlayerResponse = '
DATA_MARK = 'ytInitialData = '
LIKES_RE = re.compile(r'"likeCount":"(\d+)"')
REPOST_SECONDS = 600
SAID_PER_LINE = 2

_recent = {}


def video_id(text):
    m = YT_RE.search(text)
    return m and (m.group('short') or m.group('watch') or m.group('path'))


def number(n):
    """666 as is, 89273 as 89.27k, 6230000 as 6.23 miljoonaa: short and without thousands separators."""
    n = int(n)
    for size, one, many in ((10**9, 'miljardi', 'miljardia'), (10**6, 'miljoona', 'miljoonaa')):
        if round(n / size, 2) >= 1:
            shown = decimals(n / size)
            return '%s %s' % (shown, one if shown == '1' else many)
    return '%sk' % decimals(n / 1000) if n >= 1000 else str(n)


def decimals(x):
    """Up to two decimals with a dot, trailing zeros dropped."""
    return ('%.2f' % x).rstrip('0').rstrip('.')


def clock(seconds):
    s = int(seconds)
    h, m = divmod(s // 60, 60)
    return '%d:%02d:%02d' % (h, m, s % 60) if h else '%d:%02d' % (m, s % 60)


def fetch_page(vid):
    r = requests.get('https://www.youtube.com/watch?v=%s&hl=fi' % vid, headers=HEADERS, timeout=TIMEOUT, stream=True)
    body = b''
    for chunk in r.iter_content(65536):
        body += chunk
        if len(body) > MAX_BYTES:
            break
    r.close()
    return body.decode('utf-8', errors='ignore')


def json_after(page, mark):
    start = page.find(mark)
    if start == -1:
        return None
    found, _ = json.JSONDecoder().raw_decode(page, start + len(mark))
    return found


def first(o, key):
    """The first value under key anywhere in nested JSON."""
    if isinstance(o, dict):
        if key in o:
            return o[key]
        o = list(o.values())
    if isinstance(o, list):
        for v in o:
            found = first(v, key)
            if found is not None:
                return found
    return None


def text_of(o):
    o = o or {}
    return o.get('simpleText') or ''.join(r.get('text', '') for r in o.get('runs', []))


def page_line(page):
    """Title, uploader, date and views from the page itself: YouTube still shows them to servers it asks
    to sign in, only the player details are left out."""
    data = json_after(page, DATA_MARK)
    primary = first(data, 'videoPrimaryInfoRenderer')
    if not primary or not text_of(primary.get('title')):
        return None
    owner = first(first(data, 'videoSecondaryInfoRenderer'), 'videoOwnerRenderer') or {}
    views = first(primary, 'originalViewCount')
    parts = [text_of(primary['title']), 'lataaja: %s' % text_of(owner.get('title')) if owner.get('title') else None,
             text_of(primary.get('dateText')), '%s katselua' % number(views) if views else None, 'YouTube']
    return ' · '.join(p for p in parts if p)


def oembed_line(vid):
    """Title and uploader only, when the page itself gives nothing."""
    r = requests.get('https://www.youtube.com/oembed',
                     params={'url': 'https://www.youtube.com/watch?v=%s' % vid, 'format': 'json'},
                     headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    o = r.json()
    return '%s · lataaja: %s · YouTube' % (o['title'], o['author_name'])


def iso_seconds(text):
    """"PT1H2M3S" as 3723."""
    m = ISO_DURATION.fullmatch(text or '')
    if not m or not any(m.groups()):
        return None
    d, h, mins, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mins) * 60 + s


def line_from_api(item):
    snippet, stats = item.get('snippet') or {}, item.get('statistics') or {}
    parts = [snippet.get('title'), 'lataaja: %s' % snippet.get('channelTitle')]
    if snippet.get('publishedAt'):
        parts.append(date.fromisoformat(snippet['publishedAt'][:10]).strftime('%-d.%-m.%Y'))
    if snippet.get('liveBroadcastContent') == 'live':
        parts.append('suora lähetys')
    else:
        seconds = iso_seconds((item.get('contentDetails') or {}).get('duration'))
        if seconds:
            parts.append(clock(seconds))
    if stats.get('viewCount'):
        parts.append('%s katselua' % number(stats['viewCount']))
    if stats.get('likeCount'):
        parts.append('%s tykkäystä' % number(stats['likeCount']))
    parts.append('YouTube')
    return ' · '.join(p for p in parts if p)


def api_line(vid):
    """None without a key or when the API fails, so the page is read instead."""
    if not API_KEY:
        return None
    r = requests.get(API_URL, params={'part': 'snippet,statistics,contentDetails', 'id': vid, 'key': API_KEY}, timeout=TIMEOUT)
    if r.status_code != 200:
        LOGGER.warning('[YOUTUBE] API %s for %s' % (r.status_code, vid))
        return None
    items = r.json().get('items') or []
    return line_from_api(items[0]) if items else GONE


def describe(vid):
    line = api_line(vid)
    if line:
        return line
    page = fetch_page(vid)
    player = json_after(page, PLAYER_MARK)
    details = (player or {}).get('videoDetails')
    if not details:
        # A server's address gets "sign in to confirm you're not a bot" (LOGIN_REQUIRED) for every video.
        line = page_line(page) or oembed_line(vid)
        status = ((player or {}).get('playabilityStatus') or {}).get('status')
        if not line and status in ('ERROR', 'LOGIN_REQUIRED', 'UNPLAYABLE'):
            return GONE
        return line

    micro = (player.get('microformat') or {}).get('playerMicroformatRenderer') or {}
    parts = [details.get('title'), 'lataaja: %s' % details.get('author')]
    published = micro.get('publishDate') or micro.get('uploadDate')
    if published:
        parts.append(date.fromisoformat(published[:10]).strftime('%-d.%-m.%Y'))
    if details.get('isLive'):
        parts.append('suora lähetys')
    elif details.get('lengthSeconds') not in (None, '0'):
        parts.append(clock(details['lengthSeconds']))
    if details.get('viewCount'):
        parts.append('%s katselua' % number(details['viewCount']))
    likes = LIKES_RE.search(page)
    if likes:
        parts.append('%s tykkäystä' % number(likes.group(1)))
    parts.append('YouTube')
    return ' · '.join(p for p in parts if p)


@sopel.module.rule(r'(?iu).*(?:youtube\.com|youtu\.be)/\S+')
def youtube_auto(bot, trigger):
    if trigger.nick == bot.nick:
        return
    now = time.time()
    seen = []
    for m in YT_RE.finditer(trigger.group(0)):
        vid = m.group('short') or m.group('watch') or m.group('path')
        if vid in seen or now - _recent.get(vid, 0) < REPOST_SECONDS:
            continue
        seen.append(vid)
        try:
            line = describe(vid)
        except Exception as e:
            LOGGER.error('[YOUTUBE] %s failed: %s' % (vid, e))
            continue
        if line:
            _recent[vid] = now
            bot.say('\x02%s\x0F' % line, trigger.sender)
        else:
            LOGGER.warning('[YOUTUBE] %s: nothing to say' % vid)
        if len(seen) >= SAID_PER_LINE:
            break


if __name__ == '__main__':
    assert video_id('katso https://youtu.be/dQw4w9WgXcQ?si=x') == 'dQw4w9WgXcQ'
    assert video_id('youtube.com/shorts/ZUcoknZFUPg toimiiko') == 'ZUcoknZFUPg'
    assert video_id('https://m.youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=4') == 'dQw4w9WgXcQ'
    assert video_id('https://notyoutube.com/watch?v=dQw4w9WgXcQ') is None
    assert number(666) == '666' and number(999) == '999' and number(1000) == '1k' and number(66000) == '66k'
    assert number(66660) == '66.66k' and number(89273) == '89.27k' and number(666666) == '666.67k'
    assert number(999995) == '1 miljoona' and number(6230000) == '6.23 miljoonaa' and number(1836175875) == '1.84 miljardia'
    assert clock(213) == '3:33' and clock(3700) == '1:01:40'
    assert iso_seconds('PT3M33S') == 213 and iso_seconds('PT1H1M40S') == 3700 and iso_seconds('P1DT1S') == 86401
    assert iso_seconds('P0D') == 0 and iso_seconds('') is None
    item = {'snippet': {'title': 'Walking In The Air', 'channelTitle': 'Jarkko Ahola', 'publishedAt': '2020-12-14T17:00:09Z',
                        'liveBroadcastContent': 'none'},
            'statistics': {'viewCount': '314266', 'likeCount': '3849'}, 'contentDetails': {'duration': 'PT4M35S'}}
    assert line_from_api(item) == ('Walking In The Air · lataaja: Jarkko Ahola · 14.12.2020 · 4:35 · 314.27k katselua'
                                   ' · 3.85k tykkäystä · YouTube'), line_from_api(item)
    print('ok')
