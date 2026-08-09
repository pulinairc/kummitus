"""
almanakka.py - Sopel Almanakka Module
Copyright 2020, Roni "rolle" Laukkarinen <roni@dude.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""
import schedule
import sopel.module
from sopel.module import commands
from bs4 import BeautifulSoup
import requests
import datetime
import os
import re
import json
from babel.dates import format_date, format_datetime, format_time
from sopel import logger
from dotenv import load_dotenv
from datetime import datetime, timedelta

LOGGER = logger.get_logger(__name__)

# Load environment variables
load_dotenv()

# API Configuration
API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")
API_MODEL = "google/gemini-3.1-flash-lite-preview"

# Cache for holidays
_holidays_cache = {}
_holidays_cache_year = None

# Flag day source. There is no government API, so the Sisäministeriö-sourced
# Wikipedia list is parsed and cached instead of hardcoding dates.
FLAG_DAYS_API = "https://fi.wikipedia.org/w/api.php"
FLAG_DAYS_UA = "kummitus-ircbot/1.0 (https://github.com/pulinairc/kummitus; roni@dude.fi)"
FLAG_DAYS_TTL_DAYS = 30

FINNISH_MONTHS = {
    'tammikuuta': 1, 'helmikuuta': 2, 'maaliskuuta': 3, 'huhtikuuta': 4,
    'toukokuuta': 5, 'kesäkuuta': 6, 'heinäkuuta': 7, 'elokuuta': 8,
    'syyskuuta': 9, 'lokakuuta': 10, 'marraskuuta': 11, 'joulukuuta': 12,
}

FLAG_DAY_TIERS = {
    'Viralliset liputuspäivät': 'virallinen',
    'Vakiintuneet liputuspäivät': 'vakiintunut',
    'Suositellut liputuspäivät': 'suositeltu',
}

FLAG_DAY_RANK = {'suositeltu': 1, 'vakiintunut': 2, 'virallinen': 3}

FLAG_DAY_PHRASE = {
    'virallinen': 'Tänään liputetaan',
    'vakiintunut': 'Tänään liputetaan vakiintuneen tavan mukaan',
    'suositeltu': 'Tänään liputetaan suosituksen mukaan',
}

def get_finnish_holidays(year=None):
    """Fetch Finnish public holidays from Nager.Date API"""
    global _holidays_cache, _holidays_cache_year

    if year is None:
        year = datetime.now().year

    # Return cached if same year
    if _holidays_cache_year == year and _holidays_cache:
        return _holidays_cache

    try:
        response = requests.get(
            f"https://date.nager.at/api/v3/PublicHolidays/{year}/FI",
            timeout=10
        )
        if response.status_code == 200:
            holidays = response.json()
            # Convert to dict with date as key
            _holidays_cache = {h['date']: h['localName'] for h in holidays}
            _holidays_cache_year = year
            LOGGER.info(f"Loaded {len(_holidays_cache)} Finnish holidays for {year}")
            return _holidays_cache
    except Exception as e:
        LOGGER.error(f"Failed to fetch holidays: {e}")

    return {}

def get_today_holiday():
    """Check if today is a Finnish public holiday"""
    today = datetime.now().strftime("%Y-%m-%d")
    holidays = get_finnish_holidays()
    return holidays.get(today)

def nth_weekday(year, month, weekday, n):
    """Date of the nth given weekday in a month (Mon=0 ... Sun=6)"""
    first = datetime(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))

def last_weekday(year, month, weekday):
    """Date of the last given weekday in a month"""
    nxt = datetime(year + (month == 12), (month % 12) + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)

def get_movable_flag_day(now):
    """Flag days defined by weekday rather than date. These are set by statute,
    so they are computed instead of fetched.
    """
    # Äitienpäivä, toukokuun toinen sunnuntai
    if now.month == 5 and now.day == nth_weekday(now.year, 5, 6, 2).day:
        return ['äitienpäivä'], 'virallinen'

    # Kaatuneitten muistopäivä, toukokuun kolmas sunnuntai
    if now.month == 5 and now.day == nth_weekday(now.year, 5, 6, 3).day:
        return ['kaatuneitten muistopäivä'], 'virallinen'

    # Suomen lipun päivä, juhannuspäivä eli 20.-26.6. välinen lauantai
    if now.month == 6 and 20 <= now.day <= 26 and now.weekday() == 5:
        return ['Suomen lipun päivä', 'juhannuspäivä'], 'virallinen'

    # Suomen luonnon päivä, elokuun viimeinen lauantai
    if now.month == 8 and now.day == last_weekday(now.year, 8, 5).day:
        return ['Suomen luonnon päivä'], 'vakiintunut'

    # Isänpäivä, marraskuun toinen sunnuntai
    if now.month == 11 and now.day == nth_weekday(now.year, 11, 6, 2).day:
        return ['isänpäivä'], 'virallinen'

    return [], None

def _strip_markup(line):
    """Reduce a wikitext bullet to plain text"""
    line = re.sub(r'<ref[^>]*/>', '', line)
    line = re.sub(r'<ref.*?</ref>', '', line, flags=re.S)
    line = re.sub(r'<[^>]+>', '', line)
    line = re.sub(r'\{\{.*?\}\}', '', line, flags=re.S)
    line = re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', line)
    line = re.sub(r'\[\[([^\]]*)\]\]', r'\1', line)
    return line.replace("\'\'\'", '').replace("\'\'", '')

def _normalise_name(name):
    """Trim and convert essive case, "Kalevalan päivänä" -> "Kalevalan päivä" """
    name = re.sub(r'\s+', ' ', name).strip(' ,.;:*')
    name = re.sub(r'päivänä\b', 'päivä', name)
    name = re.sub(r'\bvappuna\b', 'vappu', name)
    return name.strip(' ,.;:')

def parse_flag_days(wikitext):
    """Parse the Sisäministeriö-sourced list into {"MM-DD": {names, tier}}"""
    days, tier, finnish_flag = {}, None, False

    for raw in wikitext.split('\n'):
        h2 = re.match(r'^==\s*([^=].*?)\s*==\s*$', raw)
        if h2:
            # Later sections list Ahvenanmaa and Sami flag days, which are not ours
            finnish_flag = 'Suomen lipulla' in h2.group(1)
            tier = None
            continue

        h3 = re.match(r'^===\s*(.*?)\s*===\s*$', raw)
        if h3:
            tier = FLAG_DAY_TIERS.get(h3.group(1))
            continue

        if not (finnish_flag and tier) or not raw.startswith('*') or raw.startswith('**'):
            continue

        line = _strip_markup(raw.lstrip('*').strip())

        # "viimeksi 1. maaliskuuta 2024" is a past occurrence, not a recurring date
        if 'viimeksi' in line:
            continue
        # Weekday-defined days are computed by get_movable_flag_day instead
        if re.search(r'(toisena|kolmantena|viimeisenä|lauantaina|sunnuntaina)', line):
            continue

        match = re.search(r'(\d{1,2})\.\s*(' + '|'.join(FINNISH_MONTHS) + r')', line)
        if not match:
            continue
        day, month = int(match.group(1)), FINNISH_MONTHS[match.group(2)]

        text = line[:match.start()] + ' ' + line[match.end():]
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d{1,2}\.\s*[\u2013-]\s*', '', text)

        names = [_normalise_name(part) for part in text.split(',')]
        names = [n for n in names
                 if len(n) > 3
                 and 'syntymäpäivä' not in n
                 and not re.match(r'^[\d\s.\u2013-]*$', n)]

        if names:
            days['%02d-%02d' % (month, day)] = {'names': names, 'tier': tier}

    return days

def fetch_flag_days():
    """Fetch and parse the flag day list from Wikipedia"""
    response = requests.get(
        FLAG_DAYS_API,
        params={
            'action': 'parse',
            'page': 'Luettelo Suomen liputuspäivistä',
            'prop': 'wikitext',
            'format': 'json',
            'formatversion': '2',
        },
        headers={'User-Agent': FLAG_DAYS_UA},
        timeout=20,
    )
    response.raise_for_status()
    days = parse_flag_days(response.json()['parse']['wikitext'])

    # A structural change upstream would silently empty the list, so sanity check
    if len(days) < 15:
        raise ValueError('parsed only %d flag days, expected at least 15' % len(days))

    return days

def load_flag_days():
    """Flag days from cache, refreshed from Wikipedia when stale.
    Falls back to the last good cache so a failed fetch never drops a flag day.
    """
    cache, cached_at = None, None
    if os.path.exists(flag_days_cache):
        try:
            with open(flag_days_cache, 'r') as filehandle:
                blob = json.loads(filehandle.read())
            cache = blob['days']
            cached_at = datetime.strptime(blob['fetched'], '%Y-%m-%d')
        except Exception as e:
            LOGGER.error('Flag day cache unreadable: %s' % e)

    if cache and cached_at and (datetime.now() - cached_at).days < FLAG_DAYS_TTL_DAYS:
        return cache

    try:
        days = fetch_flag_days()
        with open(flag_days_cache, 'w') as filehandle:
            filehandle.write(json.dumps(
                {'fetched': datetime.now().strftime('%Y-%m-%d'), 'days': days},
                ensure_ascii=False, indent=2))
        LOGGER.info('Refreshed %d flag days from Wikipedia' % len(days))
        return days
    except Exception as e:
        LOGGER.error('Flag day fetch failed: %s' % e)

    if cache:
        LOGGER.warning('Using stale flag day cache from %s' % cached_at)
        return cache

    LOGGER.warning('No flag day data available, omitting from announcement')
    return {}

def get_today_flag_day(now=None):
    """Today's flag day names plus its tier.
    A movable and a fixed flag day can land on the same date, so both are merged.
    """
    if now is None:
        now = datetime.now()

    names, tier = get_movable_flag_day(now)
    names = list(names)

    entry = load_flag_days().get(now.strftime('%m-%d'))
    if entry:
        names += [n for n in entry['names'] if n not in names]
        # The stronger obligation wins when two flag days share a date
        if tier is None or FLAG_DAY_RANK.get(entry['tier'], 0) > FLAG_DAY_RANK.get(tier, 0):
            tier = entry['tier']

    return names, tier

def build_flag_day_sentence(now, holiday):
    """Flag day sentence, or empty when today is not one.
    Names already covered by the holiday name are dropped to avoid repeating it.
    """
    names, tier = get_today_flag_day(now)
    if not names:
        return ''

    if holiday:
        holiday_lower = holiday.lower()
        names = [n for n in names if n.lower() not in holiday_lower]

    liputetaan = FLAG_DAY_PHRASE.get(tier, FLAG_DAY_PHRASE['vakiintunut'])
    if not names:
        return ' %s!' % liputetaan

    # "sekä" avoids a second "ja" when a name already contains one
    conjunction = ' sekä ' if any(' ja ' in n for n in names) else ' ja '
    reason = names[0] if len(names) == 1 else conjunction.join([', '.join(names[:-1]), names[-1]])
    return ' %s, koska on %s.' % (liputetaan, reason)

# Define base paths
log_base_path = "/home/rolle/pulina.fi/pulina-days"
save_path = f"/home/rolle/summaries/{datetime.now().strftime('%Y/%m/%d')}.md"
names_file = '/home/rolle/.sopel/modules/nimipaivat.json'
flag_days_cache = '/home/rolle/.sopel/modules/liputuspaivat_cache.json'


# Initialize global vars with yesterday's date to ensure first run works
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
global_vars = {
    'last_midnight_run': yesterday,
    'last_morning_run': yesterday
}

def get_yesterday_log():
    """Fetches the log from the local path for yesterday's date.
    Filters out bot's own messages to prevent feedback loops in summaries."""
    yesterday = datetime.now() - timedelta(days=1)
    log_date = yesterday.strftime("%Y-%m-%d")
    log_path = os.path.join(log_base_path, f"pul-{log_date}.log")

    LOGGER.debug(f"Attempting to read log from: {log_path}")

    try:
        with open(log_path, 'r') as log_file:
            lines = log_file.readlines()

        # Filter out bot's own messages to prevent summary feedback loop
        # Bot messages appear as <+kummitus>, <@kummitus>, or < kummitus>
        filtered_lines = [line for line in lines if '<+kummitus>' not in line
                          and '<@kummitus>' not in line
                          and '< kummitus>' not in line]

        log_content = ''.join(filtered_lines)
        LOGGER.debug(f"Read log file: {len(lines)} lines, {len(filtered_lines)} after filtering bot messages")
        return log_content, log_date
    except FileNotFoundError as e:
        LOGGER.error(f"Log file not found: {e}")
        return None, log_date
    except Exception as e:
        LOGGER.error(f"Failed to read the log file: {e}")
        return None, log_date

def create_summary_with_gpt(log_content):
    prompt = (
        "Alla on IRC-kanavan keskusteluloki yhdeltä päivältä. "
        "Lokin muoto on: HH:MM <nick> viesti — jokainen <nick> on eri henkilö.\n\n"
        f"{log_content}\n\n"
        "Tiivistä keskustelu mahdollisimman kattavasti niin, että ulkopuolinen saa hyvän kuvan päivän tapahtumista. "
        "Ryhmittele aihepiireittäin ja mainitse kunkin aiheen kohdalla ketkä nickit osallistuivat keskusteluun ja kuka sanoi mitäkin. "
        "Älä sekoita nickejä keskenään — varmista että attribuoit mielipiteet ja aiheet oikeille henkilöille. "
        "Tiivistelmä markdown-muodossa selkeästi jäsenneltynä ja tarvittaessa otsikoituna. Otsikoiden jälkeen tyhjä rivi ja vain ensimmäinen kirjain isolla."
    )

    try:
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
                "HTTP-Referer": "https://github.com/pulinairc/kummitus",
                "X-Title": "kummitus"
            },
            json={
                "model": API_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 5000
            },
            timeout=120
        )
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
        LOGGER.error(f"API error: {response.status_code}")
        return "Summary could not be generated."
    except Exception as e:
        LOGGER.error(f"Failed to generate summary: {e}")
        return "Summary could not be generated."

def create_summary(log_content):
    """Creates a summary from the log content."""
    lines = log_content.splitlines()
    relevant_lines = [line for line in lines if not line.startswith('---')]
    summary = " ".join(relevant_lines[:10])
    return summary

def save_summary_to_file(summary, log_date):
    """Saves the summary to a markdown file with the given date."""
    # Create the directory path
    dir_path = f"/home/rolle/summaries/{datetime.now().strftime('%Y/%m/%d')}"
    os.makedirs(dir_path, exist_ok=True)

    # Create the full file path
    file_path = os.path.join(dir_path, f"{log_date}.md")

    with open(file_path, 'w') as file:
        file.write(f"# Summary for {log_date}\n\n")
        file.write(summary)

    LOGGER.info(f"Summary saved to {file_path}")

def create_short_summary_with_gpt(log_content):
    """Generates a short summary (max 200 characters)."""
    prompt = (
        "Below is an IRC chat log. Format: HH:MM <nick> message — each <nick> is a different person.\n\n"
        f"{log_content}\n\n"
        "Summarize in one sentence in Finnish. Focus on the main topics discussed, only mention nicks when particularly relevant. "
        "Plain text only, no markdown, no backticks, no formatting. "
        "CRITICAL: Response MUST be under 200 characters due to IRC message limit. "
        "Anything over 200 characters will be cut off and lost."
    )

    retry_delays = [5, 10]
    for attempt in range(len(retry_delays) + 1):
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}",
                    "HTTP-Referer": "https://github.com/pulinairc/kummitus",
                    "X-Title": "kummitus"
                },
                json={
                    "model": API_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150
                },
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"].strip()
                    if content:
                        return content
            LOGGER.error(f"[SUMMARY] API error (attempt {attempt+1}): {response.status_code} {response.text[:200]}")
            if attempt < len(retry_delays):
                import time
                time.sleep(retry_delays[attempt])
                continue
        except Exception as e:
            LOGGER.error(f"[SUMMARY] Exception (attempt {attempt+1}): {e}")
            if attempt < len(retry_delays):
                import time
                time.sleep(retry_delays[attempt])
                continue
    return None

def post_summary_to_channel(bot, short_summary):
    """Posts a short summary to the IRC channel in the morning."""
    message = f"Eilen kanavalla keskusteltua: {short_summary}"
    bot.say(message, '#pulina')
    LOGGER.info(f"Posted short summary to #pulina: {message}")

def should_run_midnight():
    """Check if midnight message should run based on current time"""
    now = datetime.now()
    # Allow a 30-second window for the midnight check
    return now.hour == 0 and now.minute == 0 and now.second < 30

def should_run_morning():
    """Check if morning message should run based on current time"""
    now = datetime.now()
    return now.hour == 6 and now.minute == 0 and now.second < 30

def scheduled_message(bot):
    now = datetime.now()
    current_day = now.strftime("%Y-%m-%d")

    LOGGER.debug(f"Checking midnight message - Current time: {now}, Last run: {global_vars['last_midnight_run']}")

    if now.hour == 0 and 0 <= now.minute < 1:
        LOGGER.debug("Time condition met for midnight message")
        if global_vars['last_midnight_run'] != current_day:
            LOGGER.info(f"Running midnight message for {current_day}")
            # Fetch yesterday's log and generate summaries
            log_content, log_date = get_yesterday_log()
            if log_content:
                summary = create_summary_with_gpt(log_content)
                short_summary = create_short_summary_with_gpt(log_content)
                save_summary_to_file(summary, log_date)
                # Post the short summary to the IRC channel
                bot.say(f"Eilen kanavalla keskusteltua: {short_summary}", '#pulina')

            day = now.strftime("%d")
            month = now.strftime("%m")

            if os.path.exists(names_file):
                with open(names_file, 'r') as filehandle:
                    data_json = json.loads(filehandle.read())

                namedaynames_raw = data_json['%s-%s' % (month, day)]
                namedaynames_commalist = str(namedaynames_raw).strip('[]').replace('\'', '')

            findate = format_date(now, format='full', locale='fi_FI')

            # Send the message
            bot.say('Päivä vaihtui! Tänään on \x02%s\x0F. Nimipäiviään viettävät: %s.' % (findate, namedaynames_commalist), '#pulina')

            # Update using the global vars
            global_vars['last_midnight_run'] = current_day
            LOGGER.info(f"Scheduled message sent at {now}")

def get_daily_temperatures():
    """Fetches current, min and max temperatures for Jyväskylä from Open-Meteo API."""
    try:
        # Jyväskylä coordinates
        latitude = 62.2426
        longitude = 25.7473

        # Open-Meteo API URL for current and daily forecast
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m&daily=temperature_2m_max,temperature_2m_min&timezone=Europe/Helsinki&forecast_days=1"

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        temp_current = round(data['current']['temperature_2m'])
        temp_min = round(data['daily']['temperature_2m_min'][0])
        temp_max = round(data['daily']['temperature_2m_max'][0])

        return temp_current, temp_min, temp_max
    except Exception as e:
        LOGGER.error(f"Failed to fetch temperatures: {e}")
        return None, None, None

def scheduled_message_morning(bot):
    now = datetime.now()
    current_day = now.strftime("%Y-%m-%d")

    LOGGER.debug(f"Checking morning message - Current time: {now}, Last run: {global_vars['last_morning_run']}")

    if now.hour == 6 and 0 <= now.minute < 1:
        LOGGER.debug("Time condition met for morning message")
        if global_vars['last_morning_run'] != current_day:
            LOGGER.info(f"Running morning message for {current_day}")
            day = now.strftime("%d")
            month = now.strftime("%m")

            if os.path.exists(names_file):
                with open(names_file, 'r') as filehandle:
                    data_json = json.loads(filehandle.read())

                namedaynames_raw = data_json['%s-%s' % (month, day)]
                namedaynames_commalist = str(namedaynames_raw).strip('[]').replace('\'', '')

            findate = format_date(now, format='full', locale='fi_FI')

            # Get temperature data
            temp_current, temp_min, temp_max = get_daily_temperatures()

            # Build the message
            message = 'Huomenta aamuvirkut! Tänään on \x02%s\x0F. Nimipäiviään viettävät: %s.' % (findate, namedaynames_commalist)

            if temp_current is not None and temp_min is not None and temp_max is not None:
                message += f' Ulkona on nyt {temp_current}°C, tänään kylmimmillään {temp_min}°C ja lämpimimmillään {temp_max}°C. Kivaa päivää!'
            else:
                message += ' Kivaa päivää!'

            # Send the morning message
            bot.say(message, '#pulina')

            # Update using the global vars
            global_vars['last_morning_run'] = current_day
            LOGGER.info(f"Scheduled morning message sent at {now}")

@sopel.module.interval(30)  # Check every 30 seconds
def run_schedule(bot):
    try:
        now = datetime.now()
        current_day = now.strftime("%Y-%m-%d")

        LOGGER.debug(f"Schedule check - Current time: {now.strftime('%H:%M:%S')}")
        LOGGER.debug(f"Last midnight run: {global_vars['last_midnight_run']}, Last morning run: {global_vars['last_morning_run']}")

        # Midnight message (00:00)
        if now.hour == 0 and 0 <= now.minute < 1:
            LOGGER.debug("Midnight time window active")
            if global_vars['last_midnight_run'] != current_day:
                LOGGER.info(f"Sending midnight message for {current_day}")

                # Name day message
                day = now.strftime("%d")
                month = now.strftime("%m")

                if os.path.exists(names_file):
                    with open(names_file, 'r') as filehandle:
                        data_json = json.loads(filehandle.read())
                    namedaynames_raw = data_json['%s-%s' % (month, day)]
                    namedaynames_commalist = str(namedaynames_raw).strip('[]').replace('\'', '')

                findate = format_date(now, format='full', locale='fi_FI')

                # Check for holiday
                holiday = get_today_holiday()
                flag_day = build_flag_day_sentence(now, holiday)
                if holiday:
                    bot.say(f'Päivä vaihtui! Tänään on \x02{holiday}\x0F, {findate}. Nimipäiviään viettävät: {namedaynames_commalist}.{flag_day}', '#pulina')
                else:
                    bot.say(f'Päivä vaihtui! Tänään on \x02{findate}\x0F. Nimipäiviään viettävät: {namedaynames_commalist}.{flag_day}', '#pulina')

                global_vars['last_midnight_run'] = current_day
                LOGGER.info("Midnight message sent successfully")

        # Morning message (06:00)
        if now.hour == 6 and 0 <= now.minute < 1:
            LOGGER.debug("Morning time window active")
            if global_vars['last_morning_run'] != current_day:
                LOGGER.info(f"Sending morning message for {current_day}")

                # Generate and post yesterday's summary
                log_content, log_date = get_yesterday_log()
                if log_content:
                    summary = create_summary_with_gpt(log_content)
                    short_summary = create_short_summary_with_gpt(log_content)
                    if summary:
                        save_summary_to_file(summary, log_date)
                    if short_summary:
                        bot.say(f"Eilen kanavalla keskusteltua: {short_summary}", '#pulina')

                day = now.strftime("%d")
                month = now.strftime("%m")

                if os.path.exists(names_file):
                    with open(names_file, 'r') as filehandle:
                        data_json = json.loads(filehandle.read())
                    namedaynames_raw = data_json['%s-%s' % (month, day)]
                    namedaynames_commalist = str(namedaynames_raw).strip('[]').replace('\'', '')

                findate = format_date(now, format='full', locale='fi_FI')

                # Check for holiday
                holiday = get_today_holiday()

                # Get temperature data
                temp_current, temp_min, temp_max = get_daily_temperatures()

                # Build the message
                if holiday:
                    message = f'Huomenta aamuvirkut! Tänään on \x02{holiday}\x0F, {findate}. Nimipäiviään viettävät: {namedaynames_commalist}.'
                else:
                    message = f'Huomenta aamuvirkut! Tänään on \x02{findate}\x0F. Nimipäiviään viettävät: {namedaynames_commalist}.'

                message += build_flag_day_sentence(now, holiday)

                if temp_current is not None and temp_min is not None and temp_max is not None:
                    message += f' Ulkona on nyt {temp_current}°C, tänään kylmimmillään {temp_min}°C ja lämpimimmillään {temp_max}°C. Kivaa päivää!'
                else:
                    message += ' Kivaa päivää!'

                bot.say(message, '#pulina')

                global_vars['last_morning_run'] = current_day
                LOGGER.info("Morning message sent successfully")

    except Exception as e:
        LOGGER.error(f"Error in run_schedule: {e}")
        LOGGER.exception("Full traceback:")
