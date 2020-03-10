"""
fml.py - Willie FMyLife Module
Copyright 2015, Marcus Leivo <meicceli@sopel.mail.kapsi.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""
from urllib.request import urlopen;from sopel import web;from sopel.module import commands, rule;import xml.etree.ElementTree as ET
@commands('fml')
def fmylife(bot, trigger): bot.say(ET.fromstring(urlopen('http://api.fmylife.com/view/random?language=en&key=53637bae986a8').read().decode()).find('items/item/text').text)
