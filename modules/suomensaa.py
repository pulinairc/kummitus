"""
suomensaa.py
Made by rolle
Updated 2023-05-19
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
from pprint import pprint

# Paikkojen tiedosto
places_file = '/home/rolle/.sopel/modules/paikat.json'
# Nimimerkkien paikat muistissa
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
  global places_file
  global places_cfg

  # asetetaan paikka muistiin
  places_cfg[nick] = place

  # tallennetaan tiedostoon
  filehandle = open(places_file, 'w+')
  filehandle.write(json.dumps(places_cfg))
  filehandle.close()

# Save places
load_cfg()

@sopel.module.commands('asetasää', 'asetakeli')

def asetasaa(bot, trigger):
  if not trigger.group(2):
    bot.say("!asetasää <kaupunki> - Esim. !asetasää Jyväskylä asettaa nimimerkillesi oletuspaikaksi Jyväskylän. Tämän jälkeen pelkkä !sää hakee asetetusta paikasta säätiedot.")
    return

  set_place(trigger.nick, trigger.group(2).strip())
  bot.say("Paikka '" + trigger.group(2).strip() + "' asetettu nimimerkin " + trigger.nick +
    " oletuspaikaksi")

@sopel.module.commands('sää', 'keli')

def saa(bot, trigger):

  # No conflicts mode (no place set for nick)
  place = False

  if not trigger.group(2):

    # Checking if there is a place for the nick
    if trigger.nick in places_cfg:
      place = places_cfg[trigger.nick]

    else:
      bot.say("!sää <kaupunki> - Esim. !sää jyväskylä kertoo Jyväskylän sään. Hakee säätiedot Forecalta. !asetasää <kaupunki> asettaa oletuspaikan nimimerkillesi jonka jälkeen pelkkä !sää hakee asetetun paikan säätiedot.")
      return

  if not place:
    place = trigger.group(2).strip()

  # Readable version of the place
  place_readable = place

  # Change ä to a and ö to o
  place = place.replace('ä', 'a')
  place = place.replace('ö', 'o')

  url_ampparit = "https://www.ampparit.com/saa/%s" % place
  url_foreca = "https://www.foreca.fi/Finland/%s" % place
  url_moisio = "http://www.moisio.fi/taivas/aurinko.php?paikka=%s" % place

  # LXML Xpath based scraping
  r = requests.get(url_ampparit, headers={'Accept-Language': 'fi-FI', 'Content-type': 'text/html;charset=UTF-8', "accept-encoding": "gzip, deflate"})
  r.encoding == 'ISO-8859-1' and not 'ISO-8859-1' in r.headers.get('Content-Type', '')
  ampparit = lxml.html.fromstring(r.content)

  # Get for textdata
  r_textdata = requests.get(url_foreca, headers={'Accept-Language': 'fi-FI', 'Content-type': 'text/html;charset=UTF-8', "accept-encoding": "gzip, deflate"})
  r_textdata.encoding == 'ISO-8859-1' and not 'ISO-8859-1' in r_textdata.headers.get('Content-Type', '')
  foreca = lxml.html.fromstring(r_textdata.content)

  # Get for sunsetsunrise
  r_sunsetsunrise = requests.get(url_moisio, headers={'Accept-Language': 'fi-FI', 'Content-type': 'text/html;charset=UTF-8', "accept-encoding": "gzip, deflate"})
  r_sunsetsunrise.encoding == 'ISO-8859-1' and not 'ISO-8859-1' in r_sunsetsunrise.headers.get('Content-Type', '')
  moisio = lxml.html.fromstring(r_sunsetsunrise.content)

  if place == 'rolle':

    url_rolle = "https://c.rolle.wtf/raw.php"
    temps = urlopen(url_rolle).read().decode("utf-8")
    bot.say('\x02Jyväskylä, Rollen ja mustikkasopan koti\x0F: ' + temps + '')

  else:

    try:
      # NB! First, disable JS
      # If JS is disabled and nothing is found, they have changed it and it won't work. You'll have to find another page.

      # Main title: "Sää Helsinki | 10 vrk sää"
      city_get = ampparit.xpath('//*[@id="content"]/div[1]/h1')

      # Split the city name from title
      city = city_get[0].text.strip().split('|')[0].replace('Sää ', '')

      # In the "Klo" column, first number, weather-time class, custom built XPath for reliability
      time_get = ampparit.xpath('//*[@class="weather-hour"]/div[@class="weather-time"]/time')
      time = time_get[0].text.strip()

      # Temperature, class weather-temperature under the symbol
      temperature_get = ampparit.xpath('//*[@id="content"]/div[2]/div[2]/div/div/div[1]/div[2]')
      temperature = temperature_get[0].text.strip()

      # Max temperature, red number under "Ylin:"
      temperature_max_get = foreca.xpath('//*[@id="dailybox"]/div[1]/a/div/p[2]/abbr')
      temperature_max = temperature_max_get[0].text.strip()

      # Min temperature, class weather-min-temperature under the symbol
      temperature_min_get = ampparit.xpath('//*[@id="content"]/div[2]/div[2]/div/div/div[1]/div[3]')
      temperature_min = temperature_min_get[0].text.strip().replace('Alin: ', '')

      # Text version of the weather today
      text_weather_today_get = foreca.xpath('//*[@class="txt"]')
      text_weather_today = text_weather_today_get[0].text.strip().split('.')[0]

      # Feels like, class weather-temperature-feelslike in the "Lämpö (Tuntuu)" column, first row
      feelslike_get = ampparit.xpath('//*[@id="content"]/div[3]/div[1]/div/div/div[2]/div[3]/span[2]')
      feelslike = feelslike_get[0].text.strip().replace('(', '').replace(')', '')

      # Rain
      rain_get = ampparit.xpath('//*[@id="content"]/div[2]/div[2]/div/div/div[1]/div[4]/text()')
      rain = rain_get[0]

      # Sun rises
      sun_rises_get = moisio.xpath('//td[@class="tbl0"][4]')
      sun_rises = sun_rises_get[0].text.strip()

      # Sun sets
      sun_sets_get = moisio.xpath('//td[@class="tbl0"][5]')
      sun_sets = sun_sets_get[0].text.strip()

      # Day lenght
      day_length_get = moisio.xpath('//td[@class="tbl0"][6]')
      day_length = day_length_get[0].text.strip()

      # Text version of the weather today
      text_weather_tomorrow_title_get = foreca.xpath('//*[@class="txt"]')
      text_tomorrow_today = text_weather_tomorrow_title_get[1].text.strip().split('.')[0]

      # Temperature for tomorrow
      temperature_tomorrow_get = ampparit.xpath('//*[@class="weather-temperature"]')
      temperature_tomorrow = temperature_tomorrow_get[1].text.strip()

      # Min temperature in the "Huomenna" column, celsius under the symbol
      temperature_nextday_min_get = ampparit.xpath('//*[@id="content"]/div[2]/div[2]/div/div/div[2]/div[3]')
      temperature_nextday_min = temperature_nextday_min_get[0].text.strip().replace('Alin: ', '')

      # Say it all out loud
      bot.say('\x02' + city.capitalize() + '\x0Fklo ' + time + ':00: \x02' + temperature + ', ' + text_weather_today.lower() + '\x0F (tuntuu kuin: ' + feelslike + '). Sadetta mahdollisesti\x02' + rain + '\x0F. Kuluvan päivän ylin lämpötila: \x02' + temperature_max + '\x0F, alin: \x02' + temperature_min + '\x0F. Aurinko nousee klo \x02' + sun_rises + '\x02 ja laskee klo \x02' + sun_sets + '\x02. Päivän pituus on \x02' + day_length + '\x02. Huomiseksi luvassa on \x02' + temperature_tomorrow + ', ' + text_tomorrow_today.lower() + '\x02 (kylmin lämpötila huomenna: \x02' + temperature_nextday_min + '\x0F).')

    except:
      bot.say('Error, tilt, nyt bugaa! Sijainnin \x02' + place_readable.capitalize() + '\x0F säätä ei saatu haettua. Heitä ihmeessä pull requestia, jos tiedät miten tämä korjataan. Sään tarjoilee: https://github.com/pulinairc/kummitus/blob/master/modules/suomensaa.py')
