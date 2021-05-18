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
from babel.dates import format_date, format_datetime, format_time

def scheduled_message(bot):
    url = "https://almanakka.helsinki.fi/"
    now = datetime.datetime.now()

    # Get HTML page
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'
    headers = {"user-agent": user_agent}
    req = requests.get(url, headers=headers, verify=False)

    # Get stuff
    soup = BeautifulSoup(req.text, "html.parser")
    day = soup.select("#rt-sidebar-a > div.rt-block.nosto > div > div > h2")
    names = soup.select("#rt-sidebar-a > div.rt-block.nosto > div > div > p:nth-child(3)")
    findate = format_date(now, format='full', locale='fi_FI')

    bot.say('Tänään on \x02' + findate + '\x0F. ' + names[0].text.strip() + '', '#pulina')

def setup(bot):
    schedule.every().day.at('22:27').do(scheduled_message, bot=bot)

@sopel.module.interval(60)
def run_schedule(bot):
    schedule.run_pending()
    
@commands(u'almanakka', u'tänään', u'nimipäivät', 'pvm')
def almanakka(bot, trigger):
    
    url = "https://almanakka.helsinki.fi/"
    now = datetime.datetime.now()

    # Get HTML page
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'
    headers = {"user-agent": user_agent}
    req = requests.get(url, headers=headers, verify=False)

    # Get stuff
    soup = BeautifulSoup(req.text, "html.parser")
    day = soup.select("#rt-sidebar-a > div.rt-block.nosto > div > div > h2")
    names = soup.select("#rt-sidebar-a > div.rt-block.nosto > div > div > p:nth-child(3)")
    findate = format_date(now, format='full', locale='fi_FI')

    bot.say('Tänään on \x02' + findate + '\x0F. ' + names[0].text.strip() + '')
