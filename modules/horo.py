# coding=utf-8
"""
horo.py
Made by Roni Laukkarinen
"""
import sopel.module

@sopel.module.commands('horo', 'horoskooppi')

def horo(bot, trigger):

  from urllib.request import urlopen
  from urllib.error import HTTPError
  from urllib.error import URLError
  from bs4 import BeautifulSoup
 
  try:
    html = urlopen("https://www.iltalehti.fi/horoskooppi")
  except HTTPError as e:
    print(e)
  except URLError: 
    print("Server down or incorrect domain")
  else:
    res = BeautifulSoup(html.read(), "html5lib")
    oinas = res.find("div", {"class": "article-body"}).select("p")[0].getText()
    harka = res.find("div", {"class": "article-body"}).select("p")[1].getText()
    kaksoset = res.find("div", {"class": "article-body"}).select("p")[2].getText()
    rapu = res.find("div", {"class": "article-body"}).select("p")[3].getText()
    leijona = res.find("div", {"class": "article-body"}).select("p")[4].getText()
    neitsyt = res.find("div", {"class": "article-body"}).select("p")[5].getText()
    vaaka = res.find("div", {"class": "article-body"}).select("p")[6].getText()
    skorpioni = res.find("div", {"class": "article-body"}).select("p")[7].getText()
    jousimies = res.find("div", {"class": "article-body"}).select("p")[8].getText()
    kauris = res.find("div", {"class": "article-body"}).select("p")[9].getText()
    vesimies = res.find("div", {"class": "article-body"}).select("p")[10].getText()
    kalat = res.find("div", {"class": "article-body"}).select("p")[11].getText()

  if not trigger.group(2):
    bot.say("!horo <horoskooppi> - Esim. !horo skorpioni kertoo skorpionin horoskoopin. Toimii myös lyhenteillä, esim. oi, skor, här, kak, jne.")
    return

  word = trigger.group(2).strip()

  if word == 'oinas':
    bot.say(oinas)
  elif word == 'Oinas':
    bot.say(oinas)
  elif word == 'oi':
    bot.say(oinas)
  elif word == 'Härkä':
    bot.say(harka)
  elif word == 'härkä':
    bot.say(harka)
  elif word == 'här':
    bot.say(harka)
  elif word == 'Kaksoset':
    bot.say(kaksoset)
  elif word == 'kaksoset':
    bot.say(kaksoset)
  elif word == 'kak':
    bot.say(kaksoset)
  elif word == 'Rapu':
    bot.say(rapu)
  elif word == 'rapu':
    bot.say(rapu)
  elif word == 'rap':
    bot.say(rapu)
  elif word == 'Leijona':
    bot.say(leijona)
  elif word == 'leijona':
    bot.say(leijona)
  elif word == 'lei':
    bot.say(leijona)
  elif word == 'Neitsyt':
    bot.say(neitsyt)
  elif word == 'neitsyt':
    bot.say(neitsyt)
  elif word == 'nei':
    bot.say(neitsyt)
  elif word == 'Vaaka':
    bot.say(vaaka)
  elif word == 'vaaka':
    bot.say(vaaka)
  elif word == 'vaa':
    bot.say(vaaka)
  elif word == 'Skorpioni':
    bot.say(skorpioni)
  elif word == 'skorpioni':
    bot.say(skorpioni)
  elif word == 'skor':
    bot.say(skorpioni)
  elif word == 'Jousimies':
    bot.say(jousimiess)
  elif word == 'jousimies':
    bot.say(jousimiess)
  elif word == 'jou':
    bot.say(jousimiess)
  elif word == 'Kauris':
    bot.say(kauris)
  elif word == 'kauris':
    bot.say(kauris)
  elif word == 'kau':
    bot.say(kauris)
  elif word == 'Vesimies':
    bot.say(vesimies)
  elif word == 'vesimies':
    bot.say(vesimies)
  elif word == 'ves':
    bot.say(vesimies)
  elif word == 'Kalat':
    bot.say(kalat)
  elif word == 'kalat':
    bot.say(kalat)
  elif word == 'kal':
    bot.say(kalat)
  else:
    bot.say("Ime säkkiäs, typotit, EVO!! Ei ole sellaista kuin {}".format(word))