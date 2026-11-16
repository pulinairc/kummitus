"""
logindex.py - Full-text index of #pulina daily logs since 2008

Not a plugin: aibot loads it by path. Run directly to build or refresh the index:
    python3 logindex.py
"""
import datetime
import glob
import os
import random
import re
import sqlite3
import threading

LOG_DIR = '/home/rolle/pulina.fi/pulina-days'
DB_FILE = '/home/rolle/.sopel/logindex.db'

MESSAGE = re.compile(r'^(\d\d:\d\d)(?::\d\d)?\s*<\s*[@+%~&]?\s*([^>\s]+)\s*>\s?(.*)$')
ACTION = re.compile(r'^(\d\d:\d\d)(?::\d\d)?\s+\*\s+(\S+)\s+(.*)$')
FILE_DAY = re.compile(r'pul-(\d{4}-\d\d-\d\d)\.log$')

MAX_HITS = 8
CONTEXT = 4
MAX_TERMS = 8

_lock = threading.Lock()


def connect():
    db = sqlite3.connect(DB_FILE, timeout=30)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS files (name TEXT PRIMARY KEY, size INTEGER, mtime REAL);
        CREATE TABLE IF NOT EXISTS lines (
            id INTEGER PRIMARY KEY, day TEXT, time TEXT, nick TEXT, text TEXT);
        CREATE INDEX IF NOT EXISTS lines_day ON lines(day);
        CREATE INDEX IF NOT EXISTS lines_nick ON lines(nick COLLATE NOCASE);
        CREATE VIRTUAL TABLE IF NOT EXISTS lines_fts USING fts5(
            nick, text, content='lines', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2');
    ''')
    return db


def parse(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        for raw in handle:
            line = raw.rstrip('\r\n')
            match = MESSAGE.match(line) or ACTION.match(line)
            if match and match.group(3).strip():
                yield match.group(1), match.group(2), match.group(3).strip()


def _drop_day(db, day):
    rows = db.execute('SELECT id, nick, text FROM lines WHERE day = ?', (day,)).fetchall()
    db.executemany("INSERT INTO lines_fts(lines_fts, rowid, nick, text) VALUES('delete', ?, ?, ?)", rows)
    db.execute('DELETE FROM lines WHERE day = ?', (day,))


def update(verbose=False):
    """Index new or changed daily logs. Old days never change, so a refresh only
    touches today's file and returns in milliseconds."""
    with _lock:
        db = connect()
        known = {name: (size, mtime) for name, size, mtime in db.execute('SELECT * FROM files')}
        latest = max(known) if known else ''
        changed = 0
        for path in sorted(glob.glob(os.path.join(LOG_DIR, 'pul-*.log'))):
            name = os.path.basename(path)
            day = FILE_DAY.search(name)
            # Logs live on an sshfs mount, so skip stat for finished days
            if not day or (name in known and name < latest):
                continue
            stat = os.stat(path)
            if known.get(name) == (stat.st_size, stat.st_mtime):
                continue
            day = day.group(1)
            if name in known:
                _drop_day(db, day)
            for time_, nick, text in parse(path):
                cur = db.execute('INSERT INTO lines(day, time, nick, text) VALUES (?, ?, ?, ?)',
                                 (day, time_, nick, text))
                db.execute('INSERT INTO lines_fts(rowid, nick, text) VALUES (?, ?, ?)',
                           (cur.lastrowid, nick, text))
            db.execute('INSERT OR REPLACE INTO files VALUES (?, ?, ?)', (name, stat.st_size, stat.st_mtime))
            changed += 1
            if verbose and changed % 200 == 0:
                print(f'{changed} files, at {day}', flush=True)
                db.commit()
        db.commit()
        db.close()
        return changed


def fts_query(terms):
    """Each term is a word or phrase, '*' allowed at the end of a word for a prefix.
    Terms are ORed so BM25 ranks lines matching more of them first."""
    parts = []
    for term in terms[:MAX_TERMS]:
        words = re.findall(r'[\w\-]+\*?', str(term))
        tokens = []
        for word in words:
            prefix = word.endswith('*')
            word = word.rstrip('*').strip('-')
            if len(word) < 2:
                continue
            tokens.append('"%s"%s' % (word.replace('"', ''), '*' if prefix else ''))
        if len(tokens) == 1:
            parts.append(tokens[0])
        elif tokens:
            parts.append('(' + ' AND '.join(tokens) + ')')
    return ' OR '.join(parts)


def _context(db, row_id, day):
    return db.execute(
        'SELECT id, time, nick, text FROM lines WHERE day = ? AND id BETWEEN ? AND ? ORDER BY id',
        (day, row_id - CONTEXT, row_id + CONTEXT)).fetchall()


def _fmt_day(day):
    y, m, d = day.split('-')
    label = '%d.%d.%s' % (int(d), int(m), y)
    today = datetime.date.today()
    if day == today.isoformat():
        return label + ', tänään'
    if day == (today - datetime.timedelta(days=1)).isoformat():
        return label + ', eilen'
    return label


def _windows(db, hits):
    """Merge hits on nearby lines into one excerpt each."""
    excerpts, seen = [], set()
    for row_id, day in hits:
        if row_id in seen:
            continue
        rows = _context(db, row_id, day)
        seen.update(r[0] for r in rows)
        excerpts.append('[%s]\n%s' % (_fmt_day(day), '\n'.join(
            '%s <%s> %s' % (r[1], r[2], r[3][:300]) for r in rows)))
        if len(excerpts) >= MAX_HITS:
            break
    return excerpts


def search(terms=None, nick=None, date_from=None, date_to=None, order='relevance'):
    """Return a plain text block of dated log excerpts for the model to read."""
    db = connect()
    try:
        where, args = [], []
        if nick:
            where.append('l.nick = ? COLLATE NOCASE')
            args.append(nick.strip().lstrip('@+'))
        if date_from:
            where.append('l.day >= ?')
            args.append(date_from)
        if date_to:
            where.append('l.day <= ?')
            args.append(date_to)

        query = fts_query(terms or [])
        if query:
            sql = ('SELECT l.id, l.day FROM lines_fts f CROSS JOIN lines l ON l.id = f.rowid '
                   'WHERE lines_fts MATCH ?' + ''.join(' AND ' + w for w in where))
            sql += {'oldest': ' ORDER BY l.id', 'newest': ' ORDER BY l.id DESC'}.get(order, ' ORDER BY f.rank')
            total = db.execute('SELECT count(*) FROM lines_fts f CROSS JOIN lines l ON l.id = f.rowid '
                               'WHERE lines_fts MATCH ?' + ''.join(' AND ' + w for w in where),
                               [query] + args).fetchone()[0]
            hits = db.execute(sql + ' LIMIT 60', [query] + args).fetchall()
        else:
            # No search words: browse the period itself
            base = 'SELECT l.id, l.day FROM lines l' + (' WHERE ' + ' AND '.join(where) if where else '')
            total = db.execute('SELECT count(*) FROM (%s)' % base, args).fetchone()[0]
            if order == 'oldest':
                hits = db.execute(base + ' ORDER BY l.id LIMIT 1', args).fetchall()
            elif order == 'newest':
                hits = db.execute(base + ' ORDER BY l.id DESC LIMIT 1', args).fetchall()
            else:
                hits = db.execute(base + ' ORDER BY random() LIMIT %d' % MAX_HITS, args).fetchall()

        if not hits:
            return 'Ei osumia lokeista (haku: %s).' % (query or 'aikaväli')
        excerpts = _windows(db, hits)
        return 'Osumia yhteensä %d, näytetään %d otetta:\n\n%s' % (total, len(excerpts), '\n\n'.join(excerpts))
    except sqlite3.OperationalError as e:
        return 'Lokihaku epäonnistui: %s' % e
    finally:
        db.close()


def coverage():
    db = connect()
    try:
        first, last = db.execute('SELECT min(day), max(day) FROM lines').fetchone()
        return first, last
    finally:
        db.close()


if __name__ == '__main__':
    print('indexed', update(verbose=True), 'files')
    print('coverage', coverage())
