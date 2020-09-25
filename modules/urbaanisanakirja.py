"""
urbaanisanakirja.py - Sopel Urbaanisanakirja Module
Copyright 2015, Marcus Leivo <meicceli@sopel.mail.kapsi.fi>

Licensed under the Eiffel Forum License 2.

http://sopel.chat/
"""

from sopel.module import commands
from sopel import web
from bs4 import BeautifulSoup
from urllib.parse import quote
import sys


@commands('us')
def urbaani(bot, trigger):
    if not trigger.group(2):
        bot.say("Yritä edes")
        return
    haku = trigger.group(2).lower().replace(", ", ",").split(",")

    # Generoi haettavan sanan sopivaksi urbaanille sanakirjalle (URL)
    hakusana = haku[0]
    qnumero = 1

    # Jos annettu, asettaa quoten numeron ja generoi sitten urlin
    if len(haku) > 1:
        try:
            qnumero = int(haku[1])
        except:
            qnumero = 1


    # Tarkistaa onko maaritelmia, jos ei niin postaa ekan löydön
    sana = ""
    soup = BeautifulSoup(web.get("http://urbaanisanakirja.com/search/?q="+hakusana))
    try:
        url = ""
        sana = ""
        pituus = len(soup.find_all("table", attrs={'class': "table table-condensed table-striped"}))
        count = 0
        # while loopil kaikki löydetyt sanat läpi
        while pituus > count:
            # sanat käydään sarakkeittain läpi
            link = (soup.find_all("table", attrs={'class': "table table-condensed table-striped"})[count]).find_all("a", href=True)
            # käydään läpi jokane sarakkeen sana läpi ja katotaan onko match
            for i in link:
                if i.text.lower() == hakusana.lower():
                    url = i['href']
                    sana = i.text
                    count = pituus + 1
            count += 1
        # jos ei löydy 100% samaa ku hakusanaa nii postaa ekan löydön
        if sana == "":
            link = (soup.find_all("table", attrs={'class': "table table-condensed table-striped"})[0]).find_all("a", href=True)
            sana = link[0].text
            url = link[0]['href']
        soup = BeautifulSoup(web.get("http://urbaanisanakirja.com" + url))
    except IndexError:
        bot.say("Hakusanalla ei löytynyt tuloksia")
        return

    # Tarkistaa, etta annettu numero on sallituissa rajoissa
    total = len(soup.find_all("p", attrs={'class': None}))
    if qnumero > total or qnumero < 0:
        bot.say("Numero ei vastaa ketään määritelmää.")
        return

    # Hakee up ja down votet
    try:
        ups = str(soup.find_all("button", attrs={'class': 'btn btn-vote-up rate-up'})[qnumero-1].contents[1][1:])
        dns = str(soup.find_all("button", attrs={'class': 'btn btn-vote-down rate-down'})[qnumero-1].contents[1][1:])
    except IndexError:
        bot.say(u"Vituiks meni")
        return

    # Hakee maaritelman, poistaa <p> ja </p> tagit ja korvaa <br/> tagit kauttamerkilla
    definition = str(soup.find_all("p", attrs={'class': None})[qnumero-1])[3:-4].replace("<br/>", " ")
    # Jos maaritelma on yli 350 merkkia, pilkkoo maaritelmaa
    if len(definition) > 350:
        definition = definition[0:251] + "..."
        bot.say("%s >> Määritelmä %s/%s: %s (03%s|05%s) >> %s" % (sana, str(qnumero), str(total), definition, ups, dns, "http://urbaanisanakirja.com" + url))
    else:
        bot.say("%s >> Määritelmä %s/%s: %s (03%s|05%s)" % (sana, str(qnumero), str(total), definition, ups, dns))
