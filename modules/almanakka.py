"""
almanakka.py - Sopel Almanakka Module
Copyright 2020, Roni "rolle" Laukkarinen <roni@dude.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""
import sopel.module
from sopel.module import commands
from urllib.request import urlopen
import lxml.etree
from lxml import etree
import lxml.html
import requests
from bs4 import BeautifulSoup as BS4

@commands(u'almanakka', u'tänään', u'nimipäivät', 'pvm')
def almanakka(bot, trigger):
    url = "http://almanakka.helsinki.fi/fi/"

    # LXML Xpath based scraping
    r = requests.get(url)
    root = lxml.html.fromstring(r.content)
    paiva_get = root.xpath('//*[@id="rt-sidebar-a"]/div[2]/div/div/h2')
    nimet_get = root.xpath('//*[@id="rt-sidebar-a"]/div[2]/div/div/p[2]/text()')
    erikoispaiva_get = root.xpath('//*[@id="rt-sidebar-a"]/div[2]/div/div/p[1]')
    nimet = "".join(nimet_get)
    paiva = paiva_get[0].text.strip()
    erikoispaiva = erikoispaiva_get[0].text.strip()

    bot.say('\x02' + paiva + '\x0F:' + erikoispaiva + '. ' + nimet + '')
