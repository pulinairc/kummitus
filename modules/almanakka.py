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

names_file = '/home/rolle/.sopel/modules/nimipaivat.json'

def scheduled_message(bot):
    now = datetime.datetime.now()
    day = now.strftime("%d")
    month = now.strftime("%m")

    if os.path.exists(names_file):
      filehandle = open(names_file, 'r')
      data_json = json.loads(filehandle.read())
      filehandle.close()

      namedaynames_raw = data_json['%s-%s' % (month, day)]
      namedaynames_commalist = str(namedaynames_raw).strip('[]').replace('\'', '')

    findate = format_date(now, format='full', locale='fi_FI')

    bot.say('Päivä vaihtui!Tänään on \x02%s\x0F. Nimipäiviään viettävät: %s.' % (findate, namedaynames_commalist), '#pulina')

def scheduled_message_morning(bot):
    now = datetime.datetime.now()
    day = now.strftime("%d")
    month = now.strftime("%m")

    if os.path.exists(names_file):
      filehandle = open(names_file, 'r')
      data_json = json.loads(filehandle.read())
      filehandle.close()

      namedaynames_raw = data_json['%s-%s' % (month, day)]
      namedaynames_commalist = str(namedaynames_raw).strip('[]').replace('\'', '')

    findate = format_date(now, format='full', locale='fi_FI')

    bot.say('Huomenta aamuvirkut! Tänään on \x02%s\x0F. Nimipäiviään viettävät: %s.' % (findate, namedaynames_commalist), '#pulina')

def setup(bot):
    schedule.every().day.at('00:00').do(scheduled_message, bot=bot)
    schedule.every().day.at('06:00').do(scheduled_message_morning, bot=bot)

@sopel.module.interval(60)
def run_schedule(bot):
    schedule.run_pending()
    
@commands(u'almanakka', u'tänään', u'nimipäivät', 'pvm')
def almanakka(bot, trigger):
    
    now = datetime.datetime.now()
    day = now.strftime("%d")
    month = now.strftime("%m")

    if os.path.exists(names_file):
      filehandle = open(names_file, 'r')
      data_json = json.loads(filehandle.read())
      filehandle.close()

      namedaynames_raw = data_json['%s-%s' % (month, day)]
      namedaynames_commalist = str(namedaynames_raw).strip('[]').replace('\'', '')

    findate = format_date(now, format='full', locale='fi_FI')

    bot.say('Tänään on \x02%s\x0F. Nimipäiviään viettävät: %s.' % (findate, namedaynames_commalist))
