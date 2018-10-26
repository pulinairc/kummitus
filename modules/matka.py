"""
    Made by Sikanaama
"""

import sopel.module
import math
import urllib
from bs4 import BeautifulSoup as BS

URL = 'https://www.etaisyys.com/etaisyys/%s/%s/'

@sopel.module.rule(r'^.matka (\w+) (\w+)(?: (\d+))?')
@sopel.module.example('!matka Helsinki Riihimäki 100')
def module(bot, trigger):
    start = trigger.group(1)
    end = trigger.group(2)
    speed = float(trigger.group(3) or 80)

    if not start or not end:
        bot.reply('Tarvitaan lähtö- ja saapumispaikat')
    
    try:
        response = urllib.request.urlopen(URL % (start, end))
        dom = BS(response.read(), 'html.parser')
        map = int(dom.find(id='totaldistancekm').get('value'), 10)
        road = int(dom.find(id='distance').get('value'), 10)
        
        if map == 0 or road == 0:
            bot.reply('Eipä löytyny')
            return
        
        time = road / speed
        hours = math.floor(time)
        minutes = math.floor((time - hours) * 60)
        bot.reply('Välimatka %s - %s: %d km linnuntietä, %d km tietä pitkin (%d h %d min nopeudella %d km/h)' % (
            start,
            end,
            map,
            road,
            hours,
            minutes,
            speed,
        ))
    except Exception as e:
        bot.reply('En nyt saanut vastausta' % (e))
        raise e
