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
API_MODEL = "google/gemini-2.5-flash-lite"

# Cache for holidays
_holidays_cache = {}
_holidays_cache_year = None

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

# Define base paths
log_base_path = "/home/rolle/pulina.fi/pulina-days"
save_path = f"/home/rolle/summaries/{datetime.now().strftime('%Y/%m/%d')}.md"
names_file = '/home/rolle/.sopel/modules/nimipaivat.json'


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
        "IRC-keskustelu: \n\n"
        f"{log_content}\n\n"
        "Ole hyvä ja tiivistä keskustelu mahdollisimman kattavasti niin, että ulkopuolinen saa hyvän kuvan siitä mitä päivän aikana on tapahtunut. Tiivistelmä markdown-muodossa selkeästi jäsenneltynä ja tarvittaessa otsikoituna. Otsikoiden jälkeen tyhjä rivi ja vain ensimmäinen kirjain isolla."
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
        "Summarize this IRC chat log. Write in Finnish. Plain text only, no markdown, no backticks, no formatting. "
        "CRITICAL: Response MUST be under 200 characters due to IRC message limit. "
        "Anything over 200 characters will be cut off and lost.\n\n"
        f"{log_content}"
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
    """Posts a short summary to the IRC channel at midnight."""
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
                # Get yesterday's log and create summaries
                log_content, log_date = get_yesterday_log()
                if log_content:
                    summary = create_summary_with_gpt(log_content)
                    short_summary = create_short_summary_with_gpt(log_content)
                    if summary:
                        save_summary_to_file(summary, log_date)
                    if short_summary:
                        bot.say(f"Eilen kanavalla keskusteltua: {short_summary}", '#pulina')

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
                if holiday:
                    bot.say(f'Päivä vaihtui! Tänään on \x02{holiday}\x0F, {findate}. Nimipäiviään viettävät: {namedaynames_commalist}.', '#pulina')
                else:
                    bot.say(f'Päivä vaihtui! Tänään on \x02{findate}\x0F. Nimipäiviään viettävät: {namedaynames_commalist}.', '#pulina')

                global_vars['last_midnight_run'] = current_day
                LOGGER.info("Midnight message sent successfully")

        # Morning message (06:00)
        if now.hour == 6 and 0 <= now.minute < 1:
            LOGGER.debug("Morning time window active")
            if global_vars['last_morning_run'] != current_day:
                LOGGER.info(f"Sending morning message for {current_day}")

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
