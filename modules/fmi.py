# -*- coding: utf-8 -*-
"""
fmi.py
Made by rolle
"""
import sopel.module
from urllib.request import urlopen
import lxml.etree
from lxml import etree
import lxml.html
import requests
import datetime
import os
import json

# paikkojen tiedosto
places_file = '/home/rolle/.sopel/modules/paikat.json' 
# nimimerkkien paikat muistissa
places_cfg = {}

# Ladataan tiedostosta tallennetut paikat
def load_cfg():
  # NOTE: menis nätimmin class propertyillä tmv. toki
  global places_file
  global places_cfg 

  if os.path.exists(places_file):
    filehandle = open(places_file, 'r')
    places_cfg = json.loads(filehandle.read())
    filehandle.close()

# Asetetaan paikka nimimerkille ja tallennetaan tiedostoon
def set_place(nick, place):
  # NOTE: menis nätimmin class propertyillä tmv. toki
  global places_file
  global places_cfg

  # asetetaan paikka muistiin
  places_cfg[nick] = place

  # tallennetaan tiedostoon
  filehandle = open(places_file, 'w+')
  filehandle.write(json.dumps(places_cfg))
  filehandle.close()

# ladataan paikat heti muistiin
load_cfg()

@sopel.module.commands('asetasää', 'asetakeli')
def asetasaa(bot, trigger):
  if not trigger.group(2):
    bot.say("!asetasää <kaupunki> - Esim. !asetasää Jyväskylä asettaa nimimerkillesi oletuspaikaksi Jyväskylän. Tämän jälkeen pelkkä !sää hakee asetetusta paikasta säätiedot.") #FIXME
    return

  set_place(trigger.nick, trigger.group(2).strip())
  bot.say("Paikka '" + trigger.group(2).strip() + "' asetettu nimimerkin " + trigger.nick +
    " oletuspaikaksi")

@sopel.module.commands('sää', 'keli')

def saa(bot, trigger):

  # vältetään konfliktit asettamalla muuttuja 'paikka' epätodeksi
  place = False

  if not trigger.group(2):

    # tarkistetaan löytyykö nickiltä asetettua paikkaa
    if trigger.nick in places_cfg:
      place = places_cfg[trigger.nick]

    else:
      bot.say("!sää <kaupunki> - Esim. !sää jyväskylä kertoo Jyväskylän sään. Hakee säätiedot Ilmatieteen laitokselta. !asetasää <kaupunki> asettaa oletuspaikan nimimerkillesi jonka jälkeen pelkkä !sää hakee asetetun paikan säätiedot.")
      return

  if not place:
    place = trigger.group(2).strip()
  api_key = '0218711b-a299-44b2-a0b0-a4efc34b6160'
  endtime_utc = datetime.datetime.utcnow().replace(microsecond=0)
  starttime_utc = endtime_utc - datetime.timedelta(minutes=20) 
  request = 'getFeature'
  storedquery_id = 'fmi::observations::weather::simple'
  endtime = endtime_utc.isoformat() + 'Z'
  starttime = starttime_utc.isoformat() + 'Z'
  timezone = 'Europe/Helsinki'

  url = "https://ilmatieteenlaitos.fi/saa/%s" % place    
  api_call = "http://opendata.fmi.fi/wfs?request=%s&storedquery_id=%s&place=%s&timezone=%s&starttime=%s&endtime=%s" % (request, storedquery_id, place, timezone, starttime, endtime)

  # LXML Xpath based scraping
  r = requests.get(url)
  root = lxml.html.fromstring(r.content)
  rapi = requests.get(api_call)
  apiroot = lxml.html.fromstring(rapi.content)

  if place == 'jyväskylä':
      url_jkl = "http://weather.jyu.fi"
      r_jkl = requests.get(url_jkl)
      root_jkl = lxml.html.fromstring(r_jkl.content)

      try:
          # Lähipäivät, kello 15 kohdalla olevan lämpötiladivin XPath
          temperature_nextday_get = root.xpath('//*[@id="__BVID__157"]/tbody/tr[2]/td[9]/span')

          # "Auringonnousu tänään" div XPath
          sunrise_today_get = root.xpath('//*[@id="main-content"]/div[5]/div/div/div/div/div[2]/div[1]')

          # "Auringonlasku tänään" div XPath
          sunset_today_get = root.xpath('//*[@id="main-content"]/div[5]/div/div/div/div/div[2]/div[2]')

          # "Päivän pituus tänään" div XPath
          day_lenght_today_get = root.xpath('//*[@id="main-content"]/div[5]/div/div/div/div/div[2]/div[3]')

          # Sateen todennäköisyys ja määrä, ensimmäinen prosenttisarake (ei toimi kovin luotettavasti)
          # "Sateen todennäköisyys ja määrä" ekan palstan divin XPath, jossa jotain kuten "<10%"
          rain_probability_get = root.xpath('//*[@id="__BVID__157"]/tbody/tr[9]/td[1]/span')
          
          # Lähipäivät, klo 15 sarakkeen kuva ja /@title perään
          nextday_text_get = root.xpath('//*[@id="__BVID__157"]/tbody/tr[1]/td[5]/img/@title')

          # "Havaintoasema:" jälkeinen kaupunki, esim. "Jyväskylä lentoasema" ja sen XPath
          city_get = root_jkl.xpath('//*[@id="__BVID__140"]')

          # "Viimeisin säähavainto" ajan kohdan spanin XPath ja /text() perään
          time_get = root_jkl.xpath('//*[@id="main-content"]/div[7]/div/div/div/div[3]/span[2]/text()')

          # "Lämpötila" jälkeen lämpötilan XPath
          temperature_get = root_jkl.xpath('//*[@id="main-content"]/div[7]/div/div/div/div[4]/div[1]/div/span[2]')

          # Nykyisen päivän ensimmäisen sarakkeen kuvan XPath ja /@title perään
          textweather_get = root.xpath('//*[@id="__BVID__157"]/tbody/tr[1]/td[1]/img/@title')

          # Lähitunnit, tuntuu kuin div
          #feelslike_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[1]/table/tbody/tr[5]/td[1]/div')

          # Sademäärä-ennuste (ei toimi kovin luotettavasti joten toistaiseksi disabloitu)
          #precipitation_amount_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/div[1]/div/div[1]/table/tbody/tr[9]/td[1]/span/@title')

          temperature_nextday = temperature_nextday_get[0].text.strip()
          sunrise_today = sunrise_today_get[0].text.strip()
          sunset_today = sunset_today_get[0].text.strip()
          day_lenght_today = day_lenght_today_get[0].text.strip()
          #rain_probability = rain_probability_get[0].text.strip()
          nextday_text = nextday_text_get[0].strip()
          city = city_get[0].text.strip()
          time = time_get[0].strip()
          temperature = temperature_get[0].text.strip()
          textweather = textweather_get[0].strip()
          #feelslike = feelslike_get[0].strip()

          # Sademäärä-ennuste, hakeminen (ei toimi kovin luotettavasti joten toistaiseksi disabloitu)
          #precipitation_amount = precipitation_amount_get[0].strip()

          bot.say('\x02Jyväskylä, ' + city + '\x0F ' + temperature + ' (' + textweather + '), mitattu ' + time + '. Auringonnousu tänään ' + sunrise_today + ', auringonlasku tänään ' + sunset_today + '. Päivän pituus on ' + day_lenght_today + '. Huomispäiväksi luvattu ' + temperature_nextday + ' (' + nextday_text + ').')

      except:
          bot.say('Koitapa uudestaan. Joko \x02' + place + '\x0F ei ole oikea paikka tai Ilmatieteenlaitos on hetkellisesti alhaalla.')

  else:

      try:
          # Lähipäivät, kello 15 kohdalla olevan lämpötiladivin XPath
          #temperature_nextday_get = root.xpath('//*[@id="__BVID__157"]/tbody/tr[2]/td[9]/span')

          # "Auringonnousu tänään" div XPath
          #sunrise_today_get = root.xpath('//*[@id="main-content"]/div[5]/div/div/div/div/div[2]/div[1]')

          # "Auringonlasku tänään" div XPath
          #sunset_today_get = root.xpath('//*[@id="main-content"]/div[5]/div/div/div/div/div[2]/div[2]')

          # "Päivän pituus tänään" div XPath
          #day_lenght_today_get = root.xpath('//*[@id="main-content"]/div[5]/div/div/div/div/div[2]/div[3]')

          # Sateen todennäköisyys ja määrä, ensimmäinen prosenttisarake (ei toimi kovin luotettavasti)
          # "Sateen todennäköisyys ja määrä" ekan palstan divin XPath, jossa jotain kuten "<10%"
          #rain_probability_get = root.xpath('//*[@id="__BVID__157"]/tbody/tr[9]/td[1]/span')
          
          # Lähipäivät, klo 15 sarakkeen kuva ja /@title perään
          #nextday_text_get = root.xpath('//*[@id="__BVID__157"]/tbody/tr[1]/td[5]/img/@title')

          # "Havaintoasema:" jälkeinen kaupunki, esim. "Jyväskylä lentoasema" ja sen XPath
          city_get = root.xpath('//*[@id="__BVID__140"]')

          # "Viimeisin säähavainto" ajan kohdan spanin XPath ja /text() perään
          #time_get = root.xpath('//*[@id="main-content"]/div[7]/div/div/div/div[3]/span[2]/text()')

          # "Lämpötila" jälkeen lämpötilan XPath
          temperature_get = root.xpath('//*[@id="main-content"]/div[4]/div/div/div/div/div[2]/div[1]')

          # Lähitunnit, tuntuu kuin div
          #feelslike_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[1]/table/tbody/tr[5]/td[1]/div')

          # Sademäärä-ennuste (ei toimi kovin luotettavasti joten toistaiseksi disabloitu)
          #precipitation_amount_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/div[1]/div/div[1]/table/tbody/tr[9]/td[1]/span/@title')

          #temperature_nextday = temperature_nextday_get[0].text.strip()
          #sunrise_today = sunrise_today_get[0].text.strip()
          #sunset_today = sunset_today_get[0].text.strip()
          #day_lenght_today = day_lenght_today_get[0].text.strip()
          #rain_probability = rain_probability_get[0].text.strip()
          #nextday_text = nextday_text_get[0].strip()
          city = city_get[0].text.strip()
          temperature = temperature_get[0].text.strip()
          #textweather = textweather_get[0].strip()
          #feelslike = feelslike_get[0].strip()

          # Sademäärä-ennuste, hakeminen (ei toimi kovin luotettavasti joten toistaiseksi disabloitu)
          #precipitation_amount = precipitation_amount_get[0].strip()

          #bot.say('\x02' + city + '\x0F ' + temperature + ' (' + textweather + '). Auringonnousu tänään ' + sunrise_today + ', auringonlasku tänään ' + sunset_today + '. Päivän pituus on ' + day_lenght_today + '. Huomispäiväksi luvattu ' + temperature_nextday + ' (' + nextday_text + ').')
          bot.say('' + starttime + '')

      except:
            bot.say('Koitapa uudestaan. Joko \x02' + place + '\x0F ei ole oikea paikka, Ilmatieteenlaitos on hetkellisesti alhaalla tai jokin on oleellisesti muuttunut ja sääscripti bugaa.')
