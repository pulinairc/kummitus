# -*- coding: utf-8 -*-
"""
fmi.py
Made by rolle
"""
import sopel.module

@sopel.module.commands('sää', 'keli')

def saa(bot, trigger):

  from urllib.request import urlopen
  import lxml.etree
  from lxml import etree
  import lxml.html
  import requests
  import datetime

  if not trigger.group(2):
    bot.say("!sää <kaupunki> - Esim. !sää jyväskylä kertoo Jyväskylän sään. Hakee säätiedot Ilmatieteen laitokselta.")
    return
  else:

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
    api_call = "http://data.fmi.fi/fmi-apikey/%s/wfs?request=%s&storedquery_id=%s&place=%s&timezone=%s&starttime=%s&endtime=%s" % (api_key, request, storedquery_id, place, timezone, starttime, endtime)

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
            # Lähipäivät, kello 15 kohdalla oleva lämpötiladiv
            temperature_nextday_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[2]/table/tbody/tr[2]/td[8]/div')
            sunrise_today_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[7]/div[2]/strong[1]')
            sunset_today_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[7]/div[2]/strong[2]')
            day_lenght_today_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[7]/div[2]/strong[3]')

            # Sateen todennäköisyys ja määrä, ensimmäinen prosenttisarake (ei toimi kovin luotettavasti joten toistaiseksi disabloitu)
            #rain_probability_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[1]/table/tbody/tr[7]/td[1]/div/span')
            
            # Lähipäivät, klo 15 sarakkeen kuva ja /@title perään
            nextday_text_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[2]/table/tbody/tr[1]/td[8]/div/@title')
            city_get = root_jkl.xpath('//*[@id="content"]/fieldset/legend')
            time_get = root_jkl.xpath('//*[@id="c2"]/text()')
            temperature_get = root_jkl.xpath('//*[@id="table-a"]/tbody/tr[1]/td[2]')

            # Lähitunnit, ensimmäisen sarakkeen kuvan XPath ja /@title perään
            textweather_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[1]/table/tbody/tr[1]/td[1]/div/@title')

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
            # Lähipäivät, kello 15 kohdalla oleva lämpötiladiv
            temperature_nextday_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[2]/table/tbody/tr[2]/td[8]/div')
        except:
            bot.say('Koitapa uudestaan. Joko \x02' + place + '\x0F ei ole oikea paikka tai Ilmatieteenlaitos on hetkellisesti alhaalla.')

        try:
            # Lähipäivät, kello 15 kohdalla oleva lämpötiladiv
            temperature_nextday_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[2]/table/tbody/tr[2]/td[8]/div')
            sunrise_today_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[7]/div[2]/strong[1]')
            sunset_today_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[7]/div[2]/strong[2]')
            day_lenght_today_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[7]/div[2]/strong[3]')

            # Sateen todennäköisyys ja määrä, ensimmäinen prosenttisarake (ei toimi kovin luotettavasti joten toistaiseksi disabloitu)
            #rain_probability_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[1]/table/tbody/tr[7]/td[1]/div/span')
            
            # Lähipäivät, klo 15 sarakkeen kuva ja /@title perään
            nextday_text_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[2]/table/tbody/tr[1]/td[8]/div/@title')

            # Havaintoasema <select>:
            city_get = root.xpath('//*[@id="observation-station-menu"]/option[1]')

            # Lähitunnit, ensimmäisen sarakkeen lämpötila
            temperature_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[1]/table/tbody/tr[2]/td[1]/div')
            
            # Lähitunnit, ensimmäisen sarakkeen kuvan XPath ja /@title perään
            textweather_get = root.xpath('//*[@id="p_p_id_localweatherportlet_WAR_fmiwwwweatherportlets_"]/div/div/div/div[2]/div/section/div/div[1]/table/tbody/tr[1]/td[1]/div/@title')

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
            temperature = temperature_get[0].text.strip()
            textweather = textweather_get[0].strip()
            #feelslike = feelslike_get[0].strip()

            # Sademäärä-ennuste, hakeminen (ei toimi kovin luotettavasti joten toistaiseksi disabloitu)
            #precipitation_amount = precipitation_amount_get[0].strip()

            bot.say('\x02' + city + '\x0F ' + temperature + ' (' + textweather + '). Auringonnousu tänään ' + sunrise_today + ', auringonlasku tänään ' + sunset_today + '. Päivän pituus on ' + day_lenght_today + '. Huomispäiväksi luvattu ' + temperature_nextday + ' (' + nextday_text + ').')

        except:
            bot.say('Koitapa uudestaan. Joko \x02' + place + '\x0F ei ole oikea paikka tai Ilmatieteenlaitos on hetkellisesti alhaalla.')
