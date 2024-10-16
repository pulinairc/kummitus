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
from datetime import datetime

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
    # Check if the user provided a location; take only the first word as the location
    place = trigger.group(2).strip().split(' ')[0] if trigger.group(2) else places_cfg.get(trigger.nick)

    if not place:
        bot.say("!sää <kaupunki> - Esim. !sää Jyväskylä kertoo Jyväskylän sään. !asetasää <kaupunki> asettaa oletuspaikan.")
        return

    # Format the place name for API (convert to lowercase and replace special characters)
    place_formatted = place.lower().replace('ä', 'a').replace('ö', 'o')

    # Special case: if location is "koti"
    if place_formatted == "koti":
        try:
            # Fetch weather data from custom URL
            response = requests.get("https://c.rolle.wtf/raw.php")
            response.raise_for_status()
            # Print weather for "koti"
            bot.say(f"Rollen koti: {response.text.strip()}")
        except Exception as e:
            bot.say(f"Virhe: Säädataa ei voitu hakea kodille. ({str(e)})")
        return

    try:
        # Fetch weather description and coordinates using OpenWeatherMap API
        if not owm_api_key:
            bot.say("Virhe: OpenWeatherMap API-avain puuttuu. Lisää avain .env-tiedostoon.")
            return

        owm_url = f"http://api.openweathermap.org/data/2.5/weather?q={place}&appid={owm_api_key}&lang=fi&units=metric"
        owm_response = requests.get(owm_url)

        if owm_response.status_code == 404:
            bot.say(f"Paikkakuntaa {place.capitalize()} ei löytynyt.")
            return

        owm_data = owm_response.json()
        weather_description = "ei saatavilla"

        if owm_response.status_code == 200 and "weather" in owm_data and len(owm_data["weather"]) > 0:
            weather_description = owm_data["weather"][0]["description"].capitalize()

        # If OpenWeatherMap does not return valid weather data, abort
        if weather_description == "ei saatavilla":
            bot.say(f"Säätietoja ei voitu hakea paikkakunnalle {place.capitalize()}.")
            return

        # Get temperature and wind speed from OpenWeatherMap data
        temperature = owm_data["main"]["temp"]
        wind_speed = owm_data["wind"]["speed"]

        # Get latitude and longitude from OpenWeatherMap data
        lat = owm_data["coord"]["lat"]
        lon = owm_data["coord"]["lon"]

        # Fetch sunrise and sunset times from Sunrise-Sunset API using the coordinates
        sunrise_sunset_url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}&formatted=0"
        ss_response = requests.get(sunrise_sunset_url)
        sunrise = sunset = "ei saatavilla"
        day_length = "ei saatavilla"

        if ss_response.status_code == 200:
            ss_data = ss_response.json()
            if "results" in ss_data:
                sunrise = ss_data["results"]["sunrise"].split('T')[1].split('+')[0]
                sunset = ss_data["results"]["sunset"].split('T')[1].split('+')[0]

                # Convert sunrise and sunset to datetime objects
                sunrise_time = datetime.strptime(sunrise, "%H:%M:%S")
                sunset_time = datetime.strptime(sunset, "%H:%M:%S")

                # Calculate the length of the day
                day_length_timedelta = sunset_time - sunrise_time
                hours, remainder = divmod(day_length_timedelta.seconds, 3600)
                minutes = remainder // 60
                day_length = f"{hours} tuntia ja {minutes} minuuttia"

        # Build final weather message in Finnish
        bot.say(
            f"Sää {place.capitalize()}: {weather_description}. "
            f"Lämpötila on {temperature} °C ja tuulen nopeus on {wind_speed} m/s. "
            f"Aurinko laskee tänään klo {sunset} ja nousee huomenna klo {sunrise}. "
            f"Päivän pituus on {day_length}."
        )
    except Exception as e:
        bot.say(f"Virhe: Säätietoja ei voitu hakea paikkakunnalle {place.capitalize()}. ({str(e)})")
