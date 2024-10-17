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

LOGGER = logger.get_logger(__name__)  # Use Sopel logger for debugging

names_file = '/home/rolle/.sopel/modules/nimipaivat.json'
last_run_date = None  # This ensures the scheduled task runs only once per day

def scheduled_message(bot):
    global last_run_date
    now = datetime.datetime.now()
    current_day = now.strftime("%Y-%m-%d")  # Ensures the date comparison is exact

    # Check if the task has already run today
    if last_run_date == current_day:
        return  # If the message has already been sent today, do nothing

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

    # Update the last run date to today
    last_run_date = current_day
    LOGGER.info(f"Scheduled message sent at {now}")  # Logging the scheduled message

def scheduled_message_morning(bot):
    global last_run_date
    now = datetime.datetime.now()
    current_day = now.strftime("%Y-%m-%d")

    # Check if the morning message has already been sent today
    if last_run_date == current_day:
        return

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

    # Update the last run date to today
    last_run_date = current_day
    LOGGER.info(f"Scheduled morning message sent at {now}")  # Logging the morning message

def setup(bot):
    # Schedule tasks to run at 00:00 and 06:00 precisely
    schedule.every().day.at('00:00').do(scheduled_message, bot=bot)
    schedule.every().day.at('06:00').do(scheduled_message_morning, bot=bot)

@sopel.module.interval(60)
def run_schedule(bot):
    # Run all scheduled tasks
    schedule.run_pending()
    LOGGER.debug("Checked scheduled tasks")  # Logging each time the schedule is checked
