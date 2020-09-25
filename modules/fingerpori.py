# coding=utf-8
"""
Antaa linkin uusimpaan hesarin fingerporiin
"""
import sopel.module
import requests
from xml.dom.minidom import parseString
from datetime import datetime

FEED_URL = 'https://darkball.net/fingerpori/'

@sopel.module.commands('fingerpori', 'fp')
def fingerpori(bot, trigger):
    r = requests.get(FEED_URL)

    if r.status_code != 200:
        bot.say("Virhe haettaessa fingerporeja")
        return

    xml_dom = parseString(r.text)

    first_item = xml_dom.getElementsByTagName('item')[0]

    title_tag = first_item.getElementsByTagName('title')[0].firstChild.nodeValue

    title, date = title_tag.split(' ', 2)
    title += ' ' + datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y") +  ' - '
    result = title + first_item.getElementsByTagName('guid')[0].firstChild.nodeValue

    bot.say(result)
