"""
kuha.py - Sopel Lannistaja Kuha Module
Copyright 2015, Marcus Leivo <meicceli@sopel.mail.kapsi.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""
from urllib.request import urlopen
from bs4 import BeautifulSoup
from sopel.module import commands, example


@commands('kuha')
@example('.kuha 69')
def lannistaja_kuha(bot, trigger):
    number = ""
    if trigger.group(2):
        try:
            number = str(int(trigger.group(2).split(" ")[0]))
        except:
            pass
    if len(number) > 0:
        url = urlopen("http://lannistajakuha.com/" + number).read().decode()
    else:
        url = urlopen("http://lannistajakuha.com/random").read().decode()
    soup = BeautifulSoup(url)
    result = (soup.find("p", attrs={"class": "teksti"}))
    result = result.text.strip()
    bot.say(result)
