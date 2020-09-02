#encoding: utf-8

import sopel
from random import choice
import datetime
import requests
import re

shrugs = [u"乁( ⁰͡ Ĺ̯ ⁰͡ ) ㄏ",
          u"¯\_(ツ)_/¯",
          u"¯\(º_o)/¯",
          u"┐(ツ)┌",
          u"¯\_( ͠° ͟ʖ °͠ )_/¯",
          u"ʅ(°_°)ʃ",
          u"┐(°,ʖ°)┌",
          u"¯\_(⌣̯̀ ⌣́)_/¯",
          u"¯\_(°ᴥ°)_/¯",
          u"¯\_(ツ)_/¯",
          u"¯\(º_o)/¯",
          u"┐(ツ)┌"]

@sopel.module.commands("shrug")
def rand_shrug(bot, trigger):
   bot.say(u"%s" % (choice(shrugs)))
