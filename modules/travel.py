"""
travel.py - Distance and travel times between two places
Copyright 2026, Rolle Laukkarinen

!matka helsinki kaustinen
!matka Helsingistä Kaustiselle
!matka New York - Boston
"""
import json
import math
import os
import re
import time

import requests
import sopel.module
from dotenv import load_dotenv
from sopel import logger

LOGGER = logger.get_logger(__name__)

load_dotenv('/home/rolle/.sopel/.env')
API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")
API_MODEL = "google/gemini-3.1-flash-lite"

CLIENT_NAME = 'kummitus-ircbot/1.0 (+https://github.com/pulinairc/kummitus)'
GEOCODE_URL = 'https://nominatim.openstreetmap.org/search'
VALHALLA_URL = 'https://valhalla1.openstreetmap.de/route'
OSRM_URL = 'https://router.project-osrm.org/route/v1/driving/%s,%s;%s,%s'
CACHE_FILE = '/home/rolle/.sopel/modules/travel_cache.json'

# Public Valhalla caps bicycle at 150 km and walking at 100 km, past that we estimate
BIKE_ROUTE_MAX_KM = 140
WALK_ROUTE_MAX_KM = 95
BIKE_KMH = 18
WALK_KMH = 5
# Gate-to-gate airliner estimate: cruise speed plus taxi, climb and descent
FLY_MIN_KM = 300
FLY_KMH = 800
FLY_OVERHEAD_H = 0.5

SEPARATORS = re.compile(r'\s*(?:->|→|=>|\s[-–—]\s|\|)\s*|\s+(?:to|ja|kohteeseen)\s+', re.IGNORECASE)

_last_osm_call = 0.0


def _osm_wait():
    """Nominatim and Valhalla public servers allow one request per second."""
    global _last_osm_call
    delay = 1.1 - (time.time() - _last_osm_call)
    if delay > 0:
        time.sleep(delay)
    _last_osm_call = time.time()


def ask_model(prompt):
    if not API_KEY:
        return None
    try:
        response = requests.post(
            API_URL,
            json={
                'model': API_MODEL,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 100,
                'temperature': 0,
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer %s' % API_KEY,
                'HTTP-Referer': 'https://github.com/pulinairc/kummitus',
                'X-Title': 'kummitus',
            },
            timeout=20,
        )
        if response.status_code != 200:
            LOGGER.error('[TRAVEL] API %s: %s' % (response.status_code, response.text[:200]))
            return None
        text = response.json()['choices'][0]['message']['content'] or ''
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        LOGGER.error('[TRAVEL] Model call failed: %s' % e)
        return None


def ai_places(text):
    """Split free text into start and end, in the basic form a map search understands."""
    result = ask_model(
        'Käyttäjä kysyy matkaa kahden paikan välillä: "%s"\n'
        'Palauta pelkkä JSON {"from": "...", "to": "..."}. Muuta paikannimet '
        'perusmuotoon (Helsingistä -> Helsinki, Kaustiselle -> Kaustinen). '
        'Säilytä tarkenteet kuten maa tai kaupunginosa. Jos paikkoja ei löydy, '
        'palauta {"from": null, "to": null}.' % text)
    if result and result.get('from') and result.get('to'):
        return str(result['from']).strip(), str(result['to']).strip()
    return None


def split_places(text):
    parts = [p.strip() for p in SEPARATORS.split(text, maxsplit=1) if p and p.strip()]
    if len(parts) == 2:
        return parts[0], parts[1]
    words = text.split()
    if len(words) == 2:
        return words[0], words[1]
    return None


def load_cache():
    try:
        with open(CACHE_FILE, 'r') as handle:
            return json.load(handle)
    except Exception:
        return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, 'w') as handle:
            json.dump(cache, handle, ensure_ascii=False)
    except Exception as e:
        LOGGER.error('[TRAVEL] Cache write failed: %s' % e)


def _search(name, country):
    params = {'q': name, 'format': 'json', 'limit': 1, 'accept-language': 'fi'}
    if country:
        params['countrycodes'] = country
    _osm_wait()
    response = requests.get(GEOCODE_URL, params=params,
                            headers={'User-Agent': CLIENT_NAME}, timeout=15)
    hits = response.json() if response.status_code == 200 else []
    return hits[0] if hits else None


def geocode(name):
    """Exact name matches win, the better known one first (Boston is the US city,
    not the Finnish island Böstön), otherwise the Finnish hit. Cached for good.
    """
    key = name.lower()
    cache = load_cache()
    if key in cache:
        return cache[key]
    try:
        local, world = _search(name, 'fi'), _search(name, None)
    except Exception as e:
        LOGGER.error('[TRAVEL] Geocode failed for %s: %s' % (name, e))
        return None

    def exact(hit):
        return hit and (hit.get('name') or '').lower() == key

    exacts = sorted((h for h in (local, world) if exact(h)),
                    key=lambda h: float(h.get('importance') or 0), reverse=True)
    hit = (exacts[0] if exacts else None) or local or world
    if not hit:
        return None
    place = {'name': hit.get('name') or name, 'lat': float(hit['lat']), 'lon': float(hit['lon'])}
    cache[key] = place
    save_cache(cache)
    return place


def valhalla(start, end, costing):
    """Return (km, hours) or None."""
    try:
        _osm_wait()
        response = requests.post(VALHALLA_URL, json={
            'locations': [{'lat': start['lat'], 'lon': start['lon']},
                          {'lat': end['lat'], 'lon': end['lon']}],
            'costing': costing,
            'directions_options': {'units': 'kilometers'},
            'narrative': False,
        }, headers={'User-Agent': CLIENT_NAME}, timeout=30)
        summary = response.json().get('trip', {}).get('summary')
        if summary:
            return summary['length'], summary['time'] / 3600
        LOGGER.warning('[TRAVEL] Valhalla %s: %s' % (costing, response.text[:200]))
    except Exception as e:
        LOGGER.error('[TRAVEL] Valhalla %s failed: %s' % (costing, e))
    return None


def osrm_drive(start, end):
    try:
        response = requests.get(OSRM_URL % (start['lon'], start['lat'], end['lon'], end['lat']),
                                params={'overview': 'false'},
                                headers={'User-Agent': CLIENT_NAME}, timeout=20)
        route = response.json()['routes'][0]
        return route['distance'] / 1000, route['duration'] / 3600
    except Exception as e:
        LOGGER.error('[TRAVEL] OSRM failed: %s' % e)
        return None


def crow_km(start, end):
    lat1, lon1, lat2, lon2 = map(math.radians, (start['lat'], start['lon'], end['lat'], end['lon']))
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))


def fmt_km(km):
    if km < 10:
        return ('%.1f km' % km).replace('.', ',')
    return '%d km' % round(km)


def fmt_time(hours):
    minutes = int(round(hours * 60))
    days, minutes = divmod(minutes, 1440)
    hrs, mins = divmod(minutes, 60)
    if days:
        return '%d vrk %d h' % (days, hrs) if hrs else '%d vrk' % days
    if hrs:
        return '%d h %d min' % (hrs, mins) if mins else '%d h' % hrs
    return '%d min' % max(mins, 1)


def describe_trip(start, end):
    crow = crow_km(start, end)
    drive = valhalla(start, end, 'auto') or osrm_drive(start, end)
    if drive and drive[0] < crow * 0.95:
        # No road connection, the router snapped both ends to unrelated roads
        drive = None

    parts = []
    if drive:
        parts.append('%s tietä pitkin' % fmt_km(drive[0]))
    parts.append('%s linnuntietä' % fmt_km(crow))
    if drive:
        parts.append('autolla %s' % fmt_time(drive[1]))
        road_km = drive[0]
        bike = valhalla(start, end, 'bicycle') if road_km <= BIKE_ROUTE_MAX_KM else None
        parts.append('pyörällä %s' % (fmt_time(bike[1]) if bike else '~' + fmt_time(road_km / BIKE_KMH)))
        walk = valhalla(start, end, 'pedestrian') if road_km <= WALK_ROUTE_MAX_KM else None
        parts.append('kävellen %s' % (fmt_time(walk[1]) if walk else '~' + fmt_time(road_km / WALK_KMH)))
    if crow >= FLY_MIN_KM:
        parts.append('lentäen ~%s' % fmt_time(crow / FLY_KMH + FLY_OVERHEAD_H))

    return '\x02%s → %s:\x0F %s' % (start['name'], end['name'], ' • '.join(parts))


def resolve(text):
    """Find both places, asking the model only when plain parsing or the map search fails."""
    pair = split_places(text)
    if pair:
        start, end = geocode(pair[0]), geocode(pair[1])
        if start and end:
            return start, end
    pair = ai_places(text)
    if not pair:
        return None
    start, end = geocode(pair[0]), geocode(pair[1])
    if start and end:
        return start, end
    return None


@sopel.module.example('!matka Helsinki Kaustinen')
@sopel.module.commands('matka', 'välimatka', 'valimatka', 'etäisyys')
@sopel.module.require_chanmsg
def travel_command(bot, trigger):
    text = (trigger.group(2) or '').strip()
    if not text:
        bot.reply('Käyttö: !matka Helsinki Kaustinen (tai: !matka Helsingistä Kaustiselle)')
        return
    places = resolve(text)
    if not places:
        bot.reply('En löytänyt paikkoja. Kokeile muotoa: !matka Helsinki - Kaustinen')
        return
    start, end = places
    if crow_km(start, end) < 0.05:
        bot.reply('%s ja %s ovat samassa paikassa.' % (start['name'], end['name']))
        return
    bot.say(describe_trip(start, end))
