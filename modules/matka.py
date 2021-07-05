"""
matka.py
Made by rolle
"""
import sopel.module
from urllib.request import urlopen
from smartencoding import smart_unicode, smart_unicode_with_replace
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
        start = smart_unicode_with_replace(start)
        end = smart_unicode_with_replace(end)
        response = urlopen(url % (start, end))
        data_json = json.loads(response.read())
        bot.reply(data_json["distance"])
