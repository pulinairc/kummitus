"""
suomensaa.py
Made by rolle
Updated 20200628
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

  url = "https://yle.fi/saa/suomi/%s" % place    
  url_sunsetsunrise = "http://www.moisio.fi/taivas/aurinko.php?paikka=%s" % place    

  # LXML Xpath based scraping
  r = requests.get(url, headers={'Accept-Language': 'fi-FI', 'Content-type': 'text/html;charset=UTF-8', "accept-encoding": "gzip, deflate"})
  r.encoding == 'ISO-8859-1' and not 'ISO-8859-1' in r.headers.get('Content-Type', '')
  root = lxml.html.fromstring(r.content)

  if place == 'jyväskylä':
    url_jkl = "http://weather.jyu.fi"
    r_jkl = requests.get(url_jkl)
    root_jkl = lxml.html.fromstring(r_jkl.content)

    #try:

    # http://weather.jyu.fi/
    place_exact_get = root_jkl.xpath('//*[@id="content"]/fieldset/legend')
    place_exact = place_exact_get[0].text.strip()
    temperature_get = root_jkl.xpath('//*[@id="table-a"]/tbody/tr[1]/td[2]')
    temperature = temperature_get[0].text.strip()
    time_get = root_jkl.xpath('//*[@id="c2"]/text()')

    # Nämä samat kuin elsen jälkeen
    rain_probability_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[2]/div[1]/span/span[1]/span[3]')
    temperature_nextday_get = root.xpath('//*[@id="dailydata"]/li[1]/span[2]/span[5]/span[3]/span[1]/span[2]')
    textweather_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[1]/div[1]/span/span')
    textweather = textweather_get[0].text.strip().encode('latin-1').decode(encoding='utf-8',errors='strict')
    nextday_text_get = root.xpath('//*[@id="dailydata"]/li[1]/span[2]/span[5]/span[2]/span/span')
    feelslike_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[1]/div[2]/span/text()')
    precipitation_amount_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[2]/div[1]/span/span[1]/span[5]/strong')
    temperature_nextday = temperature_nextday_get[0].text.strip()
    rain_probability = rain_probability_get[0].text.strip()
    nextday_text = nextday_text_get[0].text.strip().encode('latin-1').decode(encoding='utf-8',errors='strict')
    textweather = textweather_get[0].text.strip().encode('latin-1').decode(encoding='utf-8',errors='strict')
    time = time_get[0]
    feelslike = feelslike_get[0]
    precipitation_amount = precipitation_amount_get[0].text.strip()

    bot.say('\x02Jyväskylä, ' + place_exact + '\x0F: ' + temperature + ' (' + textweather + ', ' + feelslike + '), mitattu ' + time + '. Sateen todennäköisyys: ' + rain_probability + '%, määrä: ' + precipitation_amount + '. Huomispäiväksi luvattu ' + temperature_nextday + ' (' + nextday_text + ').')

    #except:
      #bot.say('Error, tilt, nyt bugaa! Sijainnin \x02' + place.capitalize() + '\x0F säätä ei saatu haettua. Heitä ihmeessä pull requestia, jos tiedät miten tämä korjataan. Sään tarjoilee: https://github.com/pulinairc/kummitus/blob/master/modules/suomensaa.py')

  elif place == 'rolle':

    url_rolle = "https://ruuviraw.peikko.us/tags"
    temps = urlopen(url_rolle).read().decode("utf-8")
    bot.say('\x02Jyväskylä, Rollen ja mustikkasopan koti\x0F: ' + temps + '')

  else:

    try:
      # Pääinputin value
      city = root.xpath('//*[@id="searchField"]/@value')[0].encode('latin-1').decode(encoding='utf-8',errors='strict')

      # "Säätila tänään klo XX:XX" XPath
      time_get = root.xpath('//*[@id="pointdata-container"]/div[1]/h3')

      # "Sää tulevina päivinä", seuraavan päivän kello 16 kohdalla olevan lämpötiladivin XPath
      temperature_nextday_get = root.xpath('//*[@id="dailydata"]/li[1]/span[2]/span[5]/span[3]/span[1]/span[2]')

      # Sateen todennäköisyys
      rain_probability_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[2]/div[1]/span/span[1]/span[3]')

      # "Sää tulevina päivinä", seuraavan päivän kello 16 kohdalla olevan kuvan sisällä olevan spanin XPath
      nextday_text_get = root.xpath('//*[@id="dailydata"]/li[1]/span[2]/span[5]/span[2]/span/span')

      # XPath: https://dsh.re/accc8
      temperature_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[1]/div[2]/div/span[2]')

      # XPath: https://dsh.re/82f509
      feelslike_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[1]/div[2]/span/text()')

      # XPath: https://dsh.re/0c95b
      textweather_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[1]/div[1]/span/span')

      # Sademäärä-ennuste
      precipitation_amount_get = root.xpath('//*[@id="pointdata-container"]/div[2]/div[2]/div[1]/span/span[1]/span[5]/strong')

      temperature_nextday = temperature_nextday_get[0].text.strip()
      rain_probability = rain_probability_get[0].text.strip()
      nextday_text = nextday_text_get[0].text.strip().encode('latin-1').decode(encoding='utf-8',errors='strict')
      temperature = temperature_get[0].text.strip()
      textweather = textweather_get[0].text.strip().encode('latin-1').decode(encoding='utf-8',errors='strict')
      time = time_get[0].text.strip().encode('latin-1').decode(encoding='utf-8',errors='strict')
      feelslike = feelslike_get[0]
      precipitation_amount = precipitation_amount_get[0].text.strip()

      bot.say('\x02' + city.capitalize() + '\x0F - ' + time + ': ' + temperature + ' (' + textweather + ', ' + feelslike + '). Sateen todennäköisyys: ' + rain_probability + '%, määrä: ' + precipitation_amount + '. Huomispäiväksi luvattu ' + temperature_nextday + ' (' + nextday_text + ').')

    except:
      bot.say('Error, tilt, nyt bugaa! Sijainnin \x02' + place.capitalize() + '\x0F säätä ei saatu haettua. Heitä ihmeessä pull requestia, jos tiedät miten tämä korjataan. Sään tarjoilee: https://github.com/pulinairc/kummitus/blob/master/modules/suomensaa.py')
