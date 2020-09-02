#encoding: utf-8

import sopel
from random import choice
import datetime
import requests
import re

@sopel.module.commands('tfact')
def today(bot, trigger):
   month = datetime.datetime.now().month
   day = datetime.datetime.now().day
   bot.say(requests.get("http://numbersapi.com/%s/%s/date" % (month, day)).text)
