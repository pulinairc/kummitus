# coding=utf-8
"""
horo.py
Made by rolle
"""
import sopel.module
from urllib.request import urlopen, Request
from urllib.parse import quote, unquote
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup

HOROT = ['oinas', 'harka', 'kaksoset', 'rapu', 'leijona', 'neitsyt',
         'vaaka', 'skorpioni', 'jousimies', 'kauris', 'vesimies', 'kalat']

MAX_MESSAGE_LENGTH = 400

def get_horo_matches(short_query):
    return list(map(lambda x: x[:len(short_query)], HOROT))

def set_horo(bot, nick, horo):
    bot.db.set_nick_value(nick, 'horo', str(quote(horo)))

def get_horo(bot, nick):
    horo = bot.db.get_nick_value(nick, 'horo')
    if horo:
        return unquote(horo)

def convert_umlauts(query):
    return query.lower().translate(str.maketrans('äöå', 'aoa'))

def fetch_horo(horo):
    url = f"https://www.horoskooppi.co/horoskooppi/{horo}/"
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req)
    except HTTPError as e:
        return f"Virhe horoskoopin hakemisessa: {e}"
    except URLError:
        return "Palvelin on alhaalla tai verkkotunnus on virheellinen"

    try:
        soup = BeautifulSoup(response.read(), "html.parser")
        cat_holders = soup.find_all("div", class_="cat_holder")
        if not cat_holders:
            return "Horoskooppia ei löytynyt tai sivuston rakenne on muuttunut."

        horoskooppi = ""
        for holder in cat_holders:
            cat_text = holder.find("div", class_="cat_text")
            if cat_text:
                title_tag = cat_text.find("h5")
                description_tag = cat_text.find("p")
                if title_tag and description_tag:
                    title = title_tag.get_text(strip=True)
                    description = description_tag.get_text(strip=True)
                    horoskooppi += f"{title}: {description} \n"

        horoskooppi = horoskooppi.strip()
        if len(horoskooppi) > (MAX_MESSAGE_LENGTH - len(url) - 5):
            horoskooppi = horoskooppi[:MAX_MESSAGE_LENGTH - len(url) - 5] + "..."

        return f"{horoskooppi} {url}"

    except Exception as e:
        return f"Virhe horoskoopin käsittelyssä: {e}"

@sopel.module.commands('asetahoro', 'asetahoroskooppi')
def asetahoro(bot, trigger):
    if not trigger.group(2):
        bot.say("!asetahoro <horoskooppi> - Esim. !asetahoro skorpioni kertoo skorpionin horoskoopin. Toimii myös lyhenteillä, esim. oi, skor, här, kak, jne.")
        return

    original_query = trigger.group(2).strip()
    query = convert_umlauts(original_query)

    horo_prefix = get_horo_matches(query)
    match_count = horo_prefix.count(query)

    if match_count == 1:
        horo = HOROT[horo_prefix.index(query)]
        set_horo(bot, trigger.nick, horo)
        bot.say(f'horo \x02{horo}\x02 asetettu nimimerkin \x02{trigger.nick}\x02 oletushoroskoopiksi.')
    elif match_count >= 2:
        bot.say(f"Tarkenna hakuasi, hakusanalla \"{original_query}\" löytyy {match_count} horoskooppimerkkiä.")
    else:
        bot.say(f'Ei ole sellaista horoskooppimerkkiä kuin "{original_query}".')

@sopel.module.commands('horo', 'horoskooppi')
def horo(bot, trigger):
    horo = None
    if not trigger.group(2):
        horo = get_horo(bot, trigger.nick)
        if not horo:
            bot.say("!horo <horoskooppi> - Esim. !horo skorpioni kertoo skorpionin horoskoopin. Toimii myös lyhenteillä, esim. oi, skor, här, kak, jne. !asetahoro <horoskooppi> asettaa oletushoron nimimerkillesi.")
            return
    else:
        original_query = trigger.group(2).strip()
        query = convert_umlauts(original_query)
        horo_prefix = get_horo_matches(query)
        match_count = horo_prefix.count(query)

        if match_count == 1:
            horo = HOROT[horo_prefix.index(query)]
        elif match_count >= 2:
            bot.say(f"Tarkenna hakuasi, hakusanalla \"{original_query}\" löytyy {match_count} horoskooppimerkkiä.")
            return
        else:
            bot.say(f'Ei ole sellaista horoskooppimerkkiä kuin "{original_query}".')
            return

    result = fetch_horo(horo)
    bot.say(result)
