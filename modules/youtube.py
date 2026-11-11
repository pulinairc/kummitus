"""
youtube.py - Title, uploader, date, length, views and likes for YouTube links
Copyright 2026, Rolle Laukkarinen
Licensed under the Eiffel Forum License 2.
"""
import json
import re
import time
from datetime import date

import requests
import sopel.module
from sopel import logger

LOGGER = logger.get_logger(__name__)

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
LIKES_RE = re.compile(r'"likeCount":"(\d+)"')
REPOST_SECONDS = 600
SAID_PER_LINE = 2

_recent = {}


def video_id(text):
    m = YT_RE.search(text)
    return m and (m.group('short') or m.group('watch') or m.group('path'))


def number(n):
    """1836175875 as 1 836 175 875, the Finnish way."""
    return '{:,}'.format(int(n)).replace(',', ' ')


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


def player_of(page):
    start = page.find(PLAYER_MARK)
    if start == -1:
        return None
    player, _ = json.JSONDecoder().raw_decode(page, start + len(PLAYER_MARK))
    return player


def oembed_line(vid):
    """Title and uploader only, when the page itself gives nothing."""
    r = requests.get('https://www.youtube.com/oembed',
                     params={'url': 'https://www.youtube.com/watch?v=%s' % vid, 'format': 'json'},
                     headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    o = r.json()
    return '%s · lataaja: %s · YouTube' % (o['title'], o['author_name'])


def describe(vid):
    page = fetch_page(vid)
    player = player_of(page)
    details = (player or {}).get('videoDetails')
    if not details:
        status = ((player or {}).get('playabilityStatus') or {}).get('status')
        if status in ('ERROR', 'LOGIN_REQUIRED', 'UNPLAYABLE'):
            return 'Yksityinen tai poistettu video · YouTube'
        return oembed_line(vid)

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


@sopel.module.rule(r'(?u).*(?:youtube\.com|youtu\.be)/\S+')
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
        if len(seen) >= SAID_PER_LINE:
            break


if __name__ == '__main__':
    assert video_id('katso https://youtu.be/dQw4w9WgXcQ?si=x') == 'dQw4w9WgXcQ'
    assert video_id('youtube.com/shorts/ZUcoknZFUPg toimiiko') == 'ZUcoknZFUPg'
    assert video_id('https://m.youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=4') == 'dQw4w9WgXcQ'
    assert video_id('https://notyoutube.com/watch?v=dQw4w9WgXcQ') is None
    assert number(1836175875) == '1 836 175 875'
    assert clock(213) == '3:33' and clock(3700) == '1:01:40'
    print('ok')
