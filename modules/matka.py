"""
matka.py
Made by rolle
"""
import sopel.module
from urllib.request import urlopen
import urllib.parse
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
        # URL encode
        start = urllib.parse.quote(start)
        end = urllib.parse.quote(end)

        response = urlopen(url % (start.strip(), end.strip()))
        data_json = json.loads(response.read())
        distance = data_json["distance"]
        unit = 'km'
        bot.reply('%s %s' % (
            distance,
            unit,
        ))

