# encoding=utf-8
"""
fmi.py
Made by Roni Laukkarinen
"""
import sopel.module

@sopel.module.commands('sää', 'keli')

def saa(bot, trigger):

  if not trigger.group(2):
    bot.say("!sää <kaupunki> - Esim. !sää jyväskylä kertoo Jyväskylän sään. Hakee säätiedot Ilmatieteen laitokselta.")
    return
  else:

    import datetime
    import pprint
    import fmiapi
    import json

    query = trigger.group(2).strip()
    endtime = datetime.datetime.utcnow().replace(microsecond=0)
    starttime = endtime - datetime.timedelta(minutes=20) 
    api_key = '0218711b-a299-44b2-a0b0-a4efc34b6160'
    timesteps = 1

    params = {
            'request' : 'getFeature',
            'storedquery_id' : 'fmi::observations::weather::simple',
            'place' : query,
            'timesteps' : timesteps,
            'endtime' : endtime.isoformat() + 'Z',
            'starttime' : starttime.isoformat() + 'Z'
    }

    results = fmiapi.fmi_observations_weather_simple(api_key, params)
    if results:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(results)

    #bot.say('\x02' + city + '\x0F ' + temperature + ' (' + textweather + ', päivän pituus: ' + sun + ')')


