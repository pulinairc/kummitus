"""
almanakka.py - Sopel Almanakka Module
Copyright 2015, Marcus Leivo <meicceli@sopel.mail.kapsi.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""
from sopel.module import commands
from urllib.request import urlopen
from bs4 import BeautifulSoup as BS4


@commands(u'almanakka', u'tänään', u'nimipäivät')
def almanakka(bot, trigger):
    url = "http://almanakka.helsinki.fi/fi/"
    soossi = BS4(urlopen(url).read().decode())
    nimet = soossi.find("div", attrs={"id": "rt-sidebar-a"})
    nimet = nimet.find("div", attrs={"class": "module-content"})

    erikoispaiva = str(nimet.find_all("p")[0].text)
    nimet = str(nimet.find_all("p")[1])

    nimet = BS4(str(nimet).replace("<br></br>", "").replace(")", ");"))
    nimet = str(nimet.text.split(": ")[1][:-1])
    output = ""
    if erikoispaiva != "":
        output += "%s: %s" % (erikoispaiva, nimet)
    else:
        output += nimet
    bot.say(output)
