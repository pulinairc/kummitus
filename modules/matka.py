"""
matka.py
Made by rolle
"""
import sopel.module
from urllib.request import urlopen
from django.utils.encoding import smart_str, smart_unicode
import json

url = 'https://www.vaelimatka.org/route.json?stops=%s|%s'

@sopel.module.example('!matka Helsinki Riihimäki')
@sopel.module.commands('matka', 'välimatka', 'valimatka')
def module(bot, trigger):
    start = trigger.group(3)
    end = trigger.group(4)
    
    if not start or not end:
        bot.reply('Tarvitaan lähtö- ja saapumispaikat')
    else:
        response = urlopen(url % (smart_str(start), smart_str(end)))
        data_json = json.loads(response.read())
        bot.reply(data_json["distance"])
