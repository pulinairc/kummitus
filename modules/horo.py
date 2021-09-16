# coding=utf-8
"""
horo.py
Made by rolle
ja lapyo ;_;
"""
import sopel.module
from urllib.request import urlopen
from urllib.parse import quote, unquote
from urllib.error import HTTPError
from urllib.error import URLError
from bs4 import BeautifulSoup

HOROT = ['oinas', 'harka', 'kaksoset', 'rapu', 'leijona', 'neitsyt',
    'vaaka', 'skorpioni', 'jousimies', 'kauris', 'vesimies', 'kalat']

def get_horo_matches(short_query):
  # tehdään lista horoskoopeista ottamalla kustakin horosta hakusanan pituinen substring
  return list(map(lambda x: x[:len(short_query)], HOROT))

def set_horo(bot, nick, horo):
  bot.db.set_nick_value(nick, 'horo', str(quote(horo)))

def get_horo(bot, nick):
  horo = bot.db.get_nick_value(nick, 'horo')
  if horo:
    return unquote(horo)

# muutetaan ä:t a:ksi (härkä -> harka)
def convert_umlauts(query):
  return query.lower().translate(str.maketrans('ä', 'a'))

@sopel.module.commands('asetahoro', 'asetahoroskooppi')
def asetahoro(bot, trigger):
  if not trigger.group(2):
    bot.say("!asetahoro <horoskooppi> - Esim. !asetahoro \x02skorpioni\x02 kertoo skorpionin horoskoopin. Toimii myös lyhenteillä, esim. oi, skor, här, kak, jne.")
    return

  # hakusana
  original_query = trigger.group(2).strip()

  query = convert_umlauts(original_query)

  # haetaan osumalista
  horo_prefix = get_horo_matches(query)

  # katsotaan montako osumaa hakusanalla löytyy
  match_count = horo_prefix.count(query)

  # asetetaan horo jos haulla löytyy vain yksi osuma
  if match_count == 1:
    horo = HOROT[horo_prefix.index(query)]
    set_horo(bot, trigger.nick, horo)
    bot.say('horo \x02' + horo + '\x02 asetettu nimimerkin \x02' + trigger.nick + '\x02 oletushuoraksi.')
    return

  if match_count >= 2:
    bot.say("Tarkenna hakuasi, hakusanalla \"" + original_query + "\" löytyy " + str(match_count) + " horoskooppimerkkiä")
    return

  bot.say('Ime säkkiäs, typotit, EVO!! Ei ole sellaista kuin "' + original_query + '"')

@sopel.module.commands('horo', 'horoskooppi')
def horo(bot, trigger):

  # alustetaan horo
  horo = None

  if not trigger.group(2):
    horo = get_horo(bot, trigger.nick)
    if not horo:
      bot.say("!horo <horoskooppi> - Esim. !horo skorpioni kertoo skorpionin horoskoopin. Toimii myös lyhenteillä, esim. oi, skor, här, kak, jne. !asetahoro <horoskooppi> asettaa oletushoron nimimerkillesi jonka jälkeen pelkkä !horo hakee horoskoopin.")
      return

  if not horo:
    # hakusana
    original_query = trigger.group(2).strip()
    # muutetaan ä:t a:ksi (härkä -> harka)
    query = convert_umlauts(original_query)

    # haetaan osumalista
    horo_prefix = get_horo_matches(query)

    # katsotaan montako osumaa hakusanalla löytyy
    match_count = horo_prefix.count(query)

    if match_count >= 2:
      bot.say("Tarkenna hakuasi, hakusanalla \"" + original_query + "\" löytyy " + str(match_count) + " horoskooppimerkkiä")
      return

    if match_count != 1:
      bot.say('Ime säkkiäs, typotit, EVO!! Ei ole sellaista kuin "' + original_query + '"')
      return

    # haetaan vain jos 1 osuma
    horo = HOROT[horo_prefix.index(query)]

  try:
    html = urlopen("https://www.iltalehti.fi/horoskooppi")
  except HTTPError as e:
    print(e)
    return
  except URLError:
    print("Server down or incorrect domain")
    return
  res = BeautifulSoup(html.read(), "html5lib")

  bot.say(res.find("div", {"class": "article-body"}).select("p")[HOROT.index(horo)].getText())

  return

