"""
sanakirja-org.py - Sopel Sanakirja.org Module
Copyright 2014, Marcus Leivo <meicceli@sopel.mail.kapsi.fi>
Copyright 2015, Marcus Leivo <meicceli@sopel.mail.kapsi.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""
from sopel.module import commands, rate, example
from sopel import web
from bs4 import BeautifulSoup
from urllib.parse import quote
from urllib.request import urlopen
import re

maatunnus = {"bg": "1", "ee": "2", "en": "3", "es": "4",
             "ep": "5", "it": "6", "el": "7", "lat": "8",
             "lv": "9", "lt": "10", "no": "11", "pt": "12",
             "pl": "13", "fr": "14", "se": "15", "de": "16",
             "fi": "17", "dk": "18", "cz": "19", "tr": "20",
             "hu": "21", "ru": "22", "nl": "23", "jp": "24"}


@rate(5)
@commands("sk", "sanakirja", u"käännä")
@example(u".sk :ee :fi Krikin kaja pöhö")
def sanakirja(bot, trigger):
    """Maatunnukset: bg, cz, de, dk, ee, el, en, ep, es, fi, fr, hu, it, jp, lat, lt, lv, nl, no, pl, pt, ru, se, tr"""
    if not trigger.group(2):
        bot.say(u"Yritäs ny.")
        return
    command = trigger.group(2)

    def langcode(p):
        return p.startswith(':') and (2 < len(p) < 10) and p[1:].isalpha()

    args = ['en', 'fi']

    for i in range(2):
        if ' ' not in command:
            break
        prefix, cmd = command.split(' ', 1)
        if langcode(prefix):
            args[i] = prefix[1:]
            command = cmd
    hakusana = command
    lahdekieli = args[0].lower()
    kohdekieli = args[1].lower()

    if lahdekieli == "fi" and kohdekieli == "fi":
        kohdekieli = "en"

    if lahdekieli not in maatunnus or kohdekieli not in maatunnus:
        bot.say(u"Yritä edes")
        return
    url = "http://www.sanakirja.org/search.php?q=%s&l=%s&l2=%s \
        &dont_switch_languages" % (quote(hakusana),
                                   maatunnus[lahdekieli], maatunnus[kohdekieli])
    soup = BeautifulSoup(web.get(url))
    output = ""
    # Valitsee vaan kaannokset eika mitaan genetiivei yms.
    pysaytys = 0
    for kaannokset in soup.find_all("table", attrs={"class": "translations"}):
        if pysaytys == 1:
            break
        # <tr class="sk-row(1|2)"> paskeist loytyy kaannokset
        # + ylimaarasta paskaa
        for sk_row in kaannokset.find_all("tr", attrs={"class":
                                                       re.compile("sk-row")}):
            if pysaytys == 1:
                break
            # ylimaaranen paska vittuun
            for kaannos in sk_row.find_all("a", attrs={"href":
                                                       re.compile("search")}):
                if len(output + '"%s", ' % kaannos.text) < 335:
                    output += '"%s", ' % kaannos.text
                else:
                    output += "....."
                    pysaytys = 1
    if output == "":
        for i in soup.find_all("p"):
            if i.text.find("Automatisoitujen") != -1:
                bot.say(
                    u"Kusipäähomo sanakirja blockaa :D pitää oottaa varmaa \
                    jotai 5min tyylii et toimii taas :D")
                return
        bot.say(u"Tuloksia: ei ole. (%s to %s)" % (lahdekieli, kohdekieli))
        return
    bot.say(
        "%s (%s to %s)" %
        (output[
            :-
            2],
            lahdekieli,
            kohdekieli))
