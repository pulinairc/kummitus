# encoding=utf-8
"""
saa-scrape.py
Made by Roni Laukkarinen
"""
import sopel.module

@sopel.module.commands('sää', 'keli')

def saa(bot, trigger):

  from urllib.request import urlopen
  from urllib.error import HTTPError
  from urllib.error import URLError
  from bs4 import BeautifulSoup
  import lxml.html
  from lxml.cssselect import CSSSelector
  import requests

  if not trigger.group(2):
    bot.say("!sää <kaupunki> - Esim. !sää jyväskylä kertoo Jyväskylän sään. Hakee säätiedot Ilmatieteen laitokselta.")
    return
  else:

    query = trigger.group(2).strip()
 
    url = "https://ilmatieteenlaitos.fi/saa/%s" % query
    api = "http://data.fmi.fi/fmi-apikey/0218711b-a299-44b2-a0b0-a4efc34b6160/wfs?request=getFeature&storedquery_id=fmi::observations::weather::timevaluepair&place=%s&timezone=Europe/Helsinki" % query

    source = urlopen(url)
    res = BeautifulSoup(source.read(), "html5lib")
    city = res.find("select", {"id": "observation-station-menu"}).select("option")[0].getText()
    temperature = res.find("tr", {"class": "meteogram-temperatures"}).select("div")[0].getText()
    textweather = res.find("tr", {"class": "meteogram-weather-symbols"}).select("div")[0]['title']
    temperature = res.find("tr", {"class": "meteogram-temperatures"}).select("div")[0].getText()
    sun = res.find("div", {"class": "celestial-status-text"}).getText()

    bot.say('\x02' + city + '\x0F ' + temperature + ' (' + textweather + ', päivän pituus: ' + sun + ')')