# coding=utf-8
"""
horo.py
Made by Roni Laukkarinen
ja lapyo ;_;
"""
import sopel.module
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.error import URLError
from bs4 import BeautifulSoup

HOROT = ['oinas', 'harka', 'kaksoset', 'rapu', 'leijona', 'neitsyt',
    'vaaka', 'skorpioni', 'jousimies', 'kauris', 'vesimies', 'kalat']


@sopel.module.commands('horo', 'horoskooppi')
def horo(bot, trigger):

  if not trigger.group(2):
    bot.say("!horo <horoskooppi> - Esim. !horo skorpioni kertoo skorpionin horoskoopin. Toimii myös lyhenteillä, esim. oi, skor, här, kak, jne.")
    return

  # hakusana
  query = trigger.group(2).strip()
  # muutetaan ä:t a:ksi (härkä -> harka)
  query = query.lower().translate(str.maketrans('ä', 'a'))

  # tehdään lista horoskoopeista ottamalla kustakin horosta hakusanan pituinen substring
  horo_prefix = list(map(lambda x: x[:len(query)], HOROT))

  # katsotaan montako osumaa hakusanalla löytyy
  match_count = horo_prefix.count(query)

  # haetaan horo intter webseistä jos haulla löytyy vain yksi osuma
  if match_count == 1:

    try:
      html = urlopen("https://www.iltalehti.fi/horoskooppi")
    except HTTPError as e:
      print(e)
      return
    except URLError: 
      print("Server down or incorrect domain")
      return
    res = BeautifulSoup(html.read(), "html5lib")

    bot.say(res.find("div", {"class": "article-body"}).select("p")[horo_prefix.index(query)].getText())
    return

  # ulistaan jos useampi osuma
  if match_count >= 2:
    bot.say("Tarkenna hakuasi, hakusanalla \"" + query + "\" löytyy " + str(match_count) +
        " horoskooppimerkkiä")
    return

  # imetetään joulupukin lahjojensäilytyssysteemiä virheellisestä hausta
  bot.say('Ime säkkiäs, typotit, EVO!! Ei ole sellaista kuin "' + query + '"')
