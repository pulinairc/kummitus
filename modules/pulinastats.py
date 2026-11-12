"""
pulinastats.py - #pulina's numbers for pulina.fi: who is here, the record crowd and today's top talkers.
Replaces statbot's html2.tcl, peak.tcl and toptod.tcl, writing the same files in the same formats,
because the pulina.fi front page and aibot.py read them.
Copyright 2026, Rolle Laukkarinen
Licensed under the Eiffel Forum License 2.
"""
import json
import os
import time
from datetime import datetime

import sopel.plugin
from sopel.tools import get_logger

LOGGER = get_logger(__name__)

CHANNEL = '#pulina'
WEB_DIR = '/var/www/botit.pulina.fi/public_html/'
PRESENT_FILE = WEB_DIR + 'pulina.html'
PEAK_FILE = WEB_DIR + 'peak.db'
TOPTOD_HTML = WEB_DIR + 'toptod.html'
TOPTOD_STATE = WEB_DIR + 'toptod.json'
# What toptod.tcl kept: the date, "#chan:nick ..." and "words.index ..." lines.
TOPTOD_OLD_STATE = WEB_DIR + 'toptod.save'
TOPTOD_HISTORY = WEB_DIR + 'toptodhistory.save'
TOP_SHOWN = 10
# pulina.html lists idle time in minutes; the old bot topped out at this when it knew nothing.
IDLE_UNKNOWN_MIN = 6015
OP, VOICE = sopel.plugin.OP, sopel.plugin.VOICE

_last_seen = {}
_tod = {'date': '', 'words': {}, 'last': {}}


def today():
    return datetime.now().strftime('%d-%m-%Y')


def write(path, text):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


# Today's top talkers: words per nick, the same line twice in a row counted once.

def roll_day(date):
    if _tod['date'] != date:
        archive_day()
        _tod.update(date=date, words={}, last={})


def count_words(nick, text, date):
    roll_day(date)
    if _tod['last'].get(nick) == text:
        return
    _tod['last'][nick] = text
    _tod['words'][nick] = _tod['words'].get(nick, 0) + len(text.split())


def ranking(start=1, count=TOP_SHOWN):
    ranked = sorted(_tod['words'].items(), key=lambda kv: -kv[1])
    return ' '.join('%d. %s(%d)' % (i, nick, words) for i, (nick, words) in enumerate(ranked, 1) if start <= i < start + count)


def archive_day():
    """The finished day onto toptodhistory.save, three lines a day like toptod.tcl wrote them."""
    if not _tod['date'] or not _tod['words']:
        return
    nicks = list(_tod['words'])
    with open(TOPTOD_HISTORY, 'a', encoding='utf-8') as f:
        f.write('%s\n%s\n%s\n' % (_tod['date'], ' '.join('%s:%s' % (CHANNEL, n) for n in nicks),
                                  ' '.join('%d.%d' % (_tod['words'][n], i) for i, n in enumerate(nicks))))


def save_toptod():
    write(TOPTOD_STATE, json.dumps(_tod, ensure_ascii=False))
    # toptod-content-annastiina.php reads "nick(words)" pairs from this.
    write(TOPTOD_HTML, '\n\t%s \n\t\n' % ranking())


def load_toptod():
    try:
        with open(TOPTOD_STATE, encoding='utf-8') as f:
            _tod.update(json.load(f))
        return
    except (OSError, ValueError):
        pass
    # First start after statbot: carry on from its count for today.
    try:
        with open(TOPTOD_OLD_STATE, encoding='utf-8') as f:
            date, nicks, counts = (f.readline().strip() for _ in range(3))
    except OSError:
        return
    names = [n.strip('{}').split(':', 1)[-1] for n in nicks.split()]
    words = [int(c.strip('{}').split('.')[0]) for c in counts.split()]
    _tod.update(date=date, words=dict(zip(names, words)), last={})


# The record crowd: peak.db as peak.tcl kept it, "%!%#pulina!!!132@09/24/2021@10:51@PM".

def read_peak():
    try:
        with open(PEAK_FILE, encoding='utf-8') as f:
            record = f.read().split('!!!', 1)[1].split('@')
        return int(record[0]), '@'.join(record[1:]).strip()
    except (OSError, IndexError, ValueError):
        return 0, ''


def note_peak(count, now):
    best, _ = read_peak()
    if count <= best:
        return
    write(PEAK_FILE, '%%!%%%s!!!%d@%s\n' % (CHANNEL, count, now.strftime('%m/%d/%Y@%I:%M@%p')))


# Who is here: pulina.html as html2.tcl wrote it, ops first, then everyone else, then the voiced.

def person(name, userhost, idle_min, mark):
    marked = '<span class="%s">%s</span>' % ('opmark' if mark == '@' else 'voicemark', mark) if mark else ''
    return '<span class="irkkaaja" title="%s, idle %d min">%s%s</span> \n' % (userhost, idle_min, marked, name)


def present_page(people, now):
    """`people` is (nick, user@host, privilege, last seen or None)."""
    def idle(seen):
        return int((now - seen) // 60) if seen else IDLE_UNKNOWN_MIN

    groups = [[], [], []]
    for nick, userhost, level, seen in sorted(people, key=lambda p: p[0]):
        if level >= OP:
            groups[0].append(person(nick, userhost, idle(seen), '@'))
        elif level >= VOICE:
            groups[2].append(person(nick, userhost, idle(seen), '+'))
        else:
            groups[1].append(person(nick, userhost, idle(seen), ''))
    return '<b class="paikalla">%d</b><br />\n%s' % (len(people), ''.join(groups[0] + groups[1] + groups[2]))


def setup(bot):
    load_toptod()


@sopel.plugin.rule('.*')
@sopel.plugin.require_chanmsg
@sopel.plugin.unblockable
def on_line(bot, trigger):
    if trigger.sender.lower() != CHANNEL:
        return
    _last_seen[trigger.nick.lower()] = time.time()
    count_words(str(trigger.nick), trigger.plain.strip(), today())


@sopel.plugin.event('JOIN')
@sopel.plugin.rule('.*')
@sopel.plugin.unblockable
def on_join(bot, trigger):
    if trigger.sender.lower() == CHANNEL:
        _last_seen[trigger.nick.lower()] = time.time()


@sopel.plugin.interval(60)
def update_pages(bot):
    chan = bot.channels.get(CHANNEL)
    if not chan:
        return
    now = time.time()
    people = []
    for nick, user in chan.users.items():
        userhost = '%s@%s' % (user.user or '?', user.host or '?')
        people.append((str(nick), userhost, chan.privileges.get(nick, 0), _last_seen.get(str(nick).lower())))
    try:
        write(PRESENT_FILE, present_page(people, now))
        note_peak(len(people), datetime.now())
        roll_day(today())
        save_toptod()
    except OSError as e:
        LOGGER.error('[PULINASTATS] cannot write: %s', e)


@sopel.plugin.commands('toptod', 'top', 'pojot')
def toptod(bot, trigger):
    """Today's top talkers. "!toptod 20" shows places 11-20."""
    arg = (trigger.group(2) or '').strip()
    end = int(arg) if arg.isdigit() else TOP_SHOWN
    text = ranking(max(1, end - TOP_SHOWN + 1), TOP_SHOWN) or 'Kukaan ei ole vielä puhunut tänään.'
    bot.notice(text, trigger.nick)


@sopel.plugin.commands('peak')
def peak(bot, trigger):
    best, when = read_peak()
    if not best:
        bot.notice('Ennätystä ei ole vielä kirjattu.', trigger.nick)
        return
    date, clock, half = (when.split('@') + ['', ''])[:3]
    bot.notice('%s ennätys: %d ihmistä (%s %s %s)' % (CHANNEL, best, date, clock, half), trigger.nick)


if __name__ == '__main__':
    _tod.update(date='', words={}, last={})
    count_words('rolle', 'yksi kaksi kolme', '13-11-2026')
    count_words('rolle', 'yksi kaksi kolme', '13-11-2026')
    count_words('mann', 'moi', '13-11-2026')
    assert _tod['words'] == {'rolle': 3, 'mann': 1}
    assert ranking() == '1. rolle(3) 2. mann(1)'
    assert ranking(2, 10) == '2. mann(1)'
    page = present_page([('mann', 'manni@kapsi.fi', OP, None), ('aztec', '~a@h', 0, time.time() - 120),
                         ('BuddhaD', 'b@h', VOICE, None)], time.time())
    assert page.startswith('<b class="paikalla">3</b><br />\n<span class="irkkaaja" title="manni@kapsi.fi, idle 6015 min"><span class="opmark">@</span>mann')
    assert page.index('aztec') < page.index('BuddhaD') and 'idle 2 min">aztec' in page
    print('ok')
