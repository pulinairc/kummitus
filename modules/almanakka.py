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

LOGGER = logger.get_logger(__name__)  # Use Sopel logger for debugging
save_path = os.path.expanduser('~/chat.mementomori.social/Documents/Brain dump/Pulina/')
names_file = '/home/rolle/.sopel/modules/nimipaivat.json'
last_midnight_run = None
last_morning_run = None
log_base_path = os.path.expanduser('~/pulina.fi/pulina-days/')  # Base path for local logs

# Load environment variables from .env file
load_dotenv()

# Load OpenAI as client
client = OpenAI()

# Set OpenAI API key from dotenv or environment variable
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

def get_yesterday_log():
    """Fetches the log from the local path for yesterday's date."""
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    log_date = yesterday.strftime("%Y-%m-%d")
    log_path = os.path.join(log_base_path, f"pul-{log_date}.log")  # Local path to the log file

    try:
        with open(log_path, 'r') as log_file:
            log_content = log_file.read()
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
        "Ole hyvä ja tiivistä keskustelu mahdollisimman kattavasti niin, että ulkopuolinen saa hyvän kuvan siitä mitä päivän aikana on tapahtunut. Tiivistelmä markdown-muodossa selkeästi jäsenneltynä ja tarvittaessa otsikoituna."
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
    # Simple approach, replace with natural language processing for more accurate summaries if needed
    lines = log_content.splitlines()
    relevant_lines = [line for line in lines if not line.startswith('---')]  # Remove irrelevant lines
    summary = " ".join(relevant_lines[:10])  # Take first 10 relevant lines for a simple summary
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
    now = datetime.datetime.now()
    return now.hour == 0 and now.minute == 0

def should_run_morning():
    """Check if morning message should run based on current time"""
    now = datetime.datetime.now()
    return now.hour == 6 and now.minute == 0

def scheduled_message(bot):
    global last_midnight_run
    now = datetime.datetime.now()
    current_day = now.strftime("%Y-%m-%d")

    # Only proceed if we haven't run today and it's the right time
    if last_midnight_run != current_day and should_run_midnight():
        LOGGER.info("Running midnight message...")

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

        # Update the last midnight run date
        last_midnight_run = current_day
        LOGGER.info(f"Scheduled message sent at {now}")

def scheduled_message_morning(bot):
    global last_morning_run
    now = datetime.datetime.now()
    current_day = now.strftime("%Y-%m-%d")

    # Only proceed if we haven't run today and it's the right time
    if last_morning_run != current_day and should_run_morning():
        LOGGER.info("Running morning message...")

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

        # Update the last morning run date
        last_morning_run = current_day
        LOGGER.info(f"Scheduled morning message sent at {now}")

def setup(bot):
    LOGGER.info("Setting up almanakka module...")
    # Clear any existing jobs
    schedule.clear()
    # Schedule tasks to run at 00:00 and 06:00 precisely
    schedule.every().day.at('00:00').do(scheduled_message, bot=bot)
    schedule.every().day.at('06:00').do(scheduled_message_morning, bot=bot)
    LOGGER.info("Scheduled tasks set up successfully")

@sopel.module.interval(30)  # Run every 30 seconds instead of 60 for more precise timing
def run_schedule(bot):
    try:
        now = datetime.datetime.now()
        LOGGER.debug(f"Checking scheduled tasks at {now}")

        # Run both checks directly in addition to schedule
        scheduled_message(bot)
        scheduled_message_morning(bot)

        # Also run pending scheduled tasks
        schedule.run_pending()

        LOGGER.debug(f"Completed scheduled tasks check at {now}")
    except Exception as e:
        LOGGER.error(f"Error in run_schedule: {e}")
