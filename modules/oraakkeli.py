# coding=utf-8
"""
oraakkeli.py - Sopel Oraakkeli module
by Roni Laukkarinen
"""
from __future__ import unicode_literals, absolute_import, print_function, division

import re
from sopel import web
from sopel.module import commands, example
import requests
import xmltodict
import sys

if sys.version_info.major < 3:
    from urllib import quote_plus, unquote as _unquote
    unquote = lambda s: _unquote(s.encode('utf-8')).decode('utf-8')
else:
    from urllib.parse import quote_plus, unquote

import sopel.module

@sopel.module.nickname_commands(".*")

def oraakkeli(bot, trigger):
    query = trigger.replace('!', '')
    uri = 'http://www.lintukoto.net/viihde/oraakkeli/index.php?kysymys=%s&html' % query
    answer = requests.get(uri, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'}).text
    bot.reply(answer)