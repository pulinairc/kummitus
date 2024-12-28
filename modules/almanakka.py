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
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta

LOGGER = logger.get_logger(__name__)

# Define base paths
log_base_path = "/home/rolle/pulina.fi/pulina-days"
save_path = f"/home/rolle/summaries/{datetime.now().strftime('%Y/%m/%d')}.md"
names_file = '/home/rolle/.sopel/modules/nimipaivat.json'

# Load environment variables from .env file
load_dotenv()

# Load OpenAI as client
client = OpenAI()

# Set OpenAI API key from dotenv or environment variable
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# Initialize global vars with yesterday's date to ensure first run works
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
global_vars = {
    'last_midnight_run': yesterday,
    'last_morning_run': yesterday
}

def get_yesterday_log():
    """Fetches the log from the local path for yesterday's date."""
    yesterday = datetime.now() - timedelta(days=1)
    log_date = yesterday.strftime("%Y-%m-%d")
    log_path = os.path.join(log_base_path, f"pul-{log_date}.log")

    LOGGER.debug(f"Attempting to read log from: {log_path}")

    try:
        with open(log_path, 'r') as log_file:
            log_content = log_file.read()
        LOGGER.debug(f"Successfully read log file with {len(log_content)} characters")
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
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5000
        )
        summary = response.choices[0].message.content.strip()
        return summary
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
    file_name = f"{log_date}.md"
    file_path = os.path.join(save_path, file_name)

    with open(file_path, 'w') as file:
        file.write(f"# Summary for {log_date}\n\n")
        file.write(summary)

    LOGGER.info(f"Summary saved to {file_path}")

def create_short_summary_with_gpt(log_content):
    """Generates a short summary (under 220 characters) using GPT-4o-mini."""
    prompt = (
        "Kirjoita alle 220 merkkiä lyhyt yhteenveto seuraavasta keskustelusta, tarvittaessa keskity vain kohokohtiin.\n\n"
        f"{log_content}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        short_summary = response.choices[0].message.content.strip()
        return short_summary

    except Exception as e:
        LOGGER.error(f"Failed to generate short summary: {e}")
        return "Short summary could not be generated."

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

            # Send the morning message
            bot.say('Huomenta aamuvirkut! Tänään on \x02%s\x0F. Nimipäiviään viettävät: %s.' % (findate, namedaynames_commalist), '#pulina')

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
                    save_summary_to_file(summary, log_date)
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
                bot.say(f'Huomenta aamuvirkut! Tänään on \x02{findate}\x0F. Nimipäiviään viettävät: {namedaynames_commalist}.', '#pulina')

                global_vars['last_morning_run'] = current_day
                LOGGER.info("Morning message sent successfully")

    except Exception as e:
        LOGGER.error(f"Error in run_schedule: {e}")
        LOGGER.exception("Full traceback:")
