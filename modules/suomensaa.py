"""
suomensaa.py
Made by rolle
"""
import sopel.module
import requests
import json
import os
from lxml import etree
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
places_file = '/home/rolle/.sopel/modules/paikat.json'
places_cfg = {}

# Read OpenWeatherMap API key from environment variables
owm_api_key = os.getenv("OWM_API_KEY")

# Load saved places from the file
def load_cfg():
    global places_file, places_cfg
    if os.path.exists(places_file):
        with open(places_file, 'r') as filehandle:
            places_cfg = json.loads(filehandle.read())

# Save the place for the nickname
def set_place(nick, place):
    global places_file, places_cfg
    places_cfg[nick] = place
    with open(places_file, 'w+') as filehandle:
        filehandle.write(json.dumps(places_cfg))

# Load places configuration
load_cfg()

# Command to set the location
@sopel.module.commands('asetasää', 'asetakeli')
def asetasaa(bot, trigger):
    if not trigger.group(2):
        bot.say("!asetasää <kaupunki> - Esim. !asetasää Jyväskylä asettaa nimimerkillesi oletuspaikaksi Jyväskylän.")
        return
    set_place(trigger.nick, trigger.group(2).strip())
    bot.say(f"Paikka '{trigger.group(2).strip()}' asetettu nimimerkin {trigger.nick} oletuspaikaksi.")

# Command to get the weather
@sopel.module.commands('sää', 'keli')
def saa(bot, trigger):
    # Check for the user's saved location or use the given parameter
    place = places_cfg.get(trigger.nick, trigger.group(2).strip()) if trigger.group(2) else places_cfg.get(trigger.nick)

    if not place:
        bot.say("!sää <kaupunki> - Esim. !sää Jyväskylä kertoo Jyväskylän sään. !asetasää <kaupunki> asettaa oletuspaikan.")
        return

    # Format the place name for the API
    place = place.lower().replace('ä', 'a').replace('ö', 'o')

    # Special case: if the location is "koti"
    if place == "koti":
        try:
            # Fetch weather data from custom URL
            response = requests.get("https://c.rolle.wtf/raw.php")
            response.raise_for_status()
            # Print weather for "koti"
            bot.say(f"Jyväskylä, Rollen koti: {response.text.strip()}")
        except Exception as e:
            bot.say(f"Virhe: Säädataa ei voitu hakea kodille. ({str(e)})")
        return

    try:
        # FMI API query for weather data
        fmi_url = (f"https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=GetFeature"
                   f"&storedquery_id=fmi::observations::weather::cities::simple&place={place}")
        response = requests.get(fmi_url)
        response.raise_for_status()

        root = etree.fromstring(response.content)
        namespaces = {'wfs': 'http://www.opengis.net/wfs/2.0'}

        # Retrieve temperature and wind speed based on ParameterName
        temperature = None
        wind_speed = None

        # Iterate through all elements to find temperature (T) and wind speed (WS_10MIN)
        for element in root.xpath(".//wfs:member//BsWfs:BsWfsElement", namespaces={"BsWfs": "http://xml.fmi.fi/schema/wfs/2.0"}):
            parameter_name = element.find(".//BsWfs:ParameterName", namespaces={"BsWfs": "http://xml.fmi.fi/schema/wfs/2.0"}).text
            parameter_value = element.find(".//BsWfs:ParameterValue", namespaces={"BsWfs": "http://xml.fmi.fi/schema/wfs/2.0"}).text

            if parameter_name == "T":
                temperature = parameter_value
            elif parameter_name == "WS_10MIN":
                wind_speed = parameter_value

        if temperature is None or wind_speed is None:
            bot.say(f"Säätietoja ei löytynyt paikkakunnalle {place.capitalize()}.")
            return

        # Fetch weather description using OpenWeatherMap API
        if not owm_api_key:
            bot.say("Virhe: OpenWeatherMap API-avain puuttuu. Lisää avain .env-tiedostoon.")
            return

        owm_url = f"http://api.openweathermap.org/data/2.5/weather?q={place}&appid={owm_api_key}&lang=fi"
        owm_response = requests.get(owm_url)
        weather_description = "ei saatavilla"

        if owm_response.status_code == 200:
            owm_data = owm_response.json()
            if "weather" in owm_data:
                weather_description = owm_data["weather"][0]["description"].capitalize()

        # Fetch sunrise and sunset times from Sunrise-Sunset.org API
        sunrise_sunset_url = f"https://api.sunrise-sunset.org/json?lat=60.1699&lng=24.9384&formatted=0"
        ss_response = requests.get(sunrise_sunset_url)
        sunrise = sunset = "ei saatavilla"

        if ss_response.status_code == 200:
            ss_data = ss_response.json()
            if "results" in ss_data:
                sunrise = ss_data["results"]["sunrise"].split('T')[1].split('+')[0]
                sunset = ss_data["results"]["sunset"].split('T')[1].split('+')[0]

        # Build the final message in Finnish
        bot.say(f"Sää {place.capitalize()}: {weather_description}. Lämpötila on {temperature} °C ja tuulen nopeus on {wind_speed} m/s. Aurinko laskee tänään klo {sunset} ja nousee huomenna klo {sunrise}.")
    except Exception as e:
        bot.say(f"Virhe: Säätietoja ei voitu hakea paikkakunnalle {place.capitalize()}. ({str(e)})")
