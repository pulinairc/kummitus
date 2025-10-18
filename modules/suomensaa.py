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
from datetime import datetime, timedelta

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
            home_sensors = response.text.strip()

            # Fetch min/max temperatures from Open-Meteo for Jyväskylä
            meteo_url = "https://api.open-meteo.com/v1/forecast?latitude=62.2426&longitude=25.7473&current=temperature_2m&daily=temperature_2m_max,temperature_2m_min&timezone=Europe/Helsinki&forecast_days=1"
            meteo_response = requests.get(meteo_url, timeout=10)
            meteo_response.raise_for_status()
            meteo_data = meteo_response.json()

            temp_current = round(meteo_data['current']['temperature_2m'])
            temp_min = round(meteo_data['daily']['temperature_2m_min'][0])
            temp_max = round(meteo_data['daily']['temperature_2m_max'][0])

            # Print weather for "koti" with min/max
            bot.say(f"Rollen ja mustikkasopan koti: {home_sensors}. Ulkona nyt {temp_current}°C, tänään kylmimmillään {temp_min}°C ja lämpimimmillään {temp_max}°C.")
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
        temp_min = owm_data["main"]["temp_min"]
        temp_max = owm_data["main"]["temp_max"]
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

                # Fetch timezone offset from OpenWeatherMap data (in seconds)
                timezone_offset = owm_data["timezone"]

                # Use local time
                sunrise_time = datetime.strptime(sunrise, "%H:%M:%S") + timedelta(seconds=timezone_offset)
                sunset_time = datetime.strptime(sunset, "%H:%M:%S") + timedelta(seconds=timezone_offset)

                # Format sunrise and sunset times
                sunrise = sunrise_time.strftime("%H:%M")
                sunset = sunset_time.strftime("%H:%M")

                # Calculate the length of the day
                day_length_timedelta = sunset_time - sunrise_time
                hours, remainder = divmod(day_length_timedelta.seconds, 3600)
                minutes = remainder // 60
                day_length = f"{hours} tuntia ja {minutes} minuuttia"

        # Fetch home weather data
        home_weather = ""
        try:
            home_response = requests.get("https://c.rolle.wtf/raw.php", timeout=5)
            home_response.raise_for_status()
            home_weather = f" Rollen ja mustikkasopan koti: {home_response.text.strip()}"
        except Exception as e:
            # If home weather fails, just skip it
            pass

        # Build final weather message in Finnish
        bot.say(
            f"Sää {place.capitalize()}: {weather_description}. "
            f"Lämpötila on {temperature} °C. Kylmin lämpötila tänään on {temp_min} °C ja lämpimin {temp_max} °C. "
            f"Tuulen nopeus on {wind_speed} m/s. "
            f"Aurinko laskee tänään klo {sunset} ja nousee huomenna klo {sunrise}. "
            f"Päivän pituus on {day_length}.{home_weather}"
        )
    except Exception as e:
        bot.say(f"Virhe: Säätietoja ei voitu hakea paikkakunnalle {place.capitalize()}. ({str(e)})")
