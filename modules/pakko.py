# coding=utf-8
"""
pakko.py
by lapyo
"""
import sopel.module
import datetime

# "constant"
WEEKDAYS = ['maanantai', 'tiistai', 'keskiviikko', 'torstai', 'perjantai', 'lauantai', 'sunnuntai']

@sopel.module.commands('pakko')
def pakko(bot, trigger):
    bot.say(WEEKDAYS[datetime.datetime.today().weekday()].capitalize() + ' - pakko ottaa')
