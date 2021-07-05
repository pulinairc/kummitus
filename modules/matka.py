"""
matka.py
Made by rolle
"""
from __future__ import unicode_literals
import sys
sys.setdefaultencoding('UTF8')
if sys.version_info[0] >= 3:
    unicode = str
import sopel.module
from urllib.request import urlopen
from smartencoding import smart_unicode, smart_unicode_with_replace
import json

@sopel.module.example('!matka Helsinki Riihimäki')
@sopel.module.commands('matka', 'välimatka', 'valimatka')
def module(bot, trigger):
    start = trigger.group(3)
    end = trigger.group(4)
    
    if not start or not end:
        bot.reply('Tarvitaan lähtö- ja saapumispaikat')
    else:
        url = 'https://www.vaelimatka.org/route.json?stops=%s|%s'
        start = unicode(start)
        end = unicode(end)
        response = urlopen(url % (start, end))
        data_json = json.loads(response.read())
        bot.reply(data_json["distance"] + ' km')
