#encoding: utf-8

import sopel
from random import choice
import datetime
import requests
import re

@sopel.module.commands('nfact')
def nfact(bot, trigger):
   bot.say(requests.get("http://numbersapi.com/random").text)
