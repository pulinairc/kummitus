"""
chatterbot.py - Chat bot for sopel IRC bot
Copyright 2021, Roni Laukkarinen [roni@dude.fi]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just
  can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""
from __future__ import unicode_literals, absolute_import, print_function, division

import re
from sopel import web
from sopel.module import commands, example
import requests
import xmltodict
import sys

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.logic import LogicAdapter
from chatterbot import filters

# Create a new ChatBot instance
chatbot = ChatBot(
    'kummitus',
    storage_adapter='chatterbot.storage.MongoDatabaseAdapter',
    logic_adapters=[
        'chatterbot.logic.BestMatch'
    ],
    database_uri='mongodb://localhost:27017/chatterbot-database'
)

trainer = ChatterBotCorpusTrainer(chatbot)

from chatterbot.trainers import ListTrainer

trainer.train(
#     "./training/pulina-2008-04.log.json",
#     "./training/pulina-2008-05.log.json",
#     "./training/pulina-2008-06.log.json",
#     "./training/pulina-2008-07.log.json",
#     "./training/pulina-2008-08.log.json",
#     "./training/pulina-2008-09.log.json",
#     "./training/pulina-2008-10.log.json",
#     "./training/pulina-2008-11.log.json",
#     "./training/pulina-2008-12.log.json",
#     "./training/pulina-2009-01.log.json",
#     "./training/pulina-2009-02.log.json",
#     "./training/pulina-2009-03.log.json",
#     "./training/pulina-2009-04.log.json",
#     "./training/pulina-2009-05.log.json",
#     "./training/pulina-2009-06.log.json",
#     "./training/pulina-2009-07.log.json",
#     "./training/pulina-2009-08.log.json",
#     "./training/pulina-2009-09.log.json",
#     "./training/pulina-2009-10.log.json",
#     "./training/pulina-2009-11.log.json",
#     "./training/pulina-2009-12.log.json",
#     "./training/pulina-2010-01.log.json",
#     "./training/pulina-2010-02.log.json",
#     "./training/pulina-2010-03.log.json",
#     "./training/pulina-2010-04.log.json",
#     "./training/pulina-2010-05.log.json",
#     "./training/pulina-2010-06.log.json",
#     "./training/pulina-2010-07.log.json",
#     "./training/pulina-2010-08.log.json",
#     "./training/pulina-2010-09.log.json",
#     "./training/pulina-2010-10.log.json",
#     "./training/pulina-2010-11.log.json",
#     "./training/pulina-2010-12.log.json",
#     "./training/pulina-2011-01.log.json",
#     "./training/pulina-2011-02.log.json",
#     "./training/pulina-2011-03.log.json",
#     "./training/pulina-2011-04.log.json",
#     "./training/pulina-2011-05.log.json",
#     "./training/pulina-2011-06.log.json",
#     "./training/pulina-2011-07.log.json",
#     "./training/pulina-2011-08.log.json",
#     "./training/pulina-2011-09.log.json",
#     "./training/pulina-2011-10.log.json",
#     "./training/pulina-2011-11.log.json",
#     "./training/pulina-2011-12.log.json",
#     "./training/pulina-2012-01.log.json",
#     "./training/pulina-2012-02.log.json",
#     "./training/pulina-2012-03.log.json",
#     "./training/pulina-2012-04.log.json",
#     "./training/pulina-2012-05.log.json",
#     "./training/pulina-2012-06.log.json",
#     "./training/pulina-2012-07.log.json",
#     "./training/pulina-2012-08.log.json",
#     "./training/pulina-2012-09.log.json",
#     "./training/pulina-2012-10.log.json",
#     "./training/pulina-2012-11.log.json",
#     "./training/pulina-2012-12.log.json",
#     "./training/pulina-2013-01.log.json",
#     "./training/pulina-2013-02.log.json",
#     "./training/pulina-2013-03.log.json",
#     "./training/pulina-2013-04.log.json",
#     "./training/pulina-2013-05.log.json",
#     "./training/pulina-2013-06.log.json",
#     "./training/pulina-2013-07.log.json",
#     "./training/pulina-2013-08.log.json",
#     "./training/pulina-2013-09.log.json",
#     "./training/pulina-2013-10.log.json",
    "./training/pulina-2013-11.log.json",
#     "./training/pulina-2013-12.log.json",
#     "./training/pulina-2014-01.log.json",
#     "./training/pulina-2014-02.log.json",
#     "./training/pulina-2014-03.log.json",
#     "./training/pulina-2014-04.log.json",
#     "./training/pulina-2014-05.log.json",
#     "./training/pulina-2014-06.log.json",
#     "./training/pulina-2014-07.log.json",
#     "./training/pulina-2014-08.log.json",
#     "./training/pulina-2014-09.log.json",
#     "./training/pulina-2014-10.log.json",
#     "./training/pulina-2014-11.log.json",
#     "./training/pulina-2014-12.log.json",
#     "./training/pulina-2015-01.log.json",
#     "./training/pulina-2015-02.log.json",
    "./training/pulina-2015-03.log.json",
#     "./training/pulina-2015-04.log.json",
#     "./training/pulina-2015-05.log.json",
#     "./training/pulina-2015-06.log.json",
#     "./training/pulina-2015-07.log.json",
#     "./training/pulina-2015-08.log.json",
#     "./training/pulina-2015-09.log.json",
#     "./training/pulina-2015-10.log.json",
#     "./training/pulina-2015-11.log.json",
#     "./training/pulina-2015-12.log.json",
#     "./training/pulina-2016-01.log.json",
#     "./training/pulina-2016-02.log.json",
#     "./training/pulina-2016-03.log.json",
#     "./training/pulina-2016-04.log.json",
    "./training/pulina-2016-05.log.json",
#     "./training/pulina-2016-06.log.json",
#     "./training/pulina-2016-07.log.json",
#     "./training/pulina-2016-08.log.json",
#     "./training/pulina-2016-09.log.json",
#     "./training/pulina-2016-10.log.json",
#     "./training/pulina-2016-11.log.json",
#     "./training/pulina-2016-12.log.json",
#     "./training/pulina-2017-01.log.json",
#     "./training/pulina-2017-02.log.json",
#     "./training/pulina-2017-03.log.json",
#     "./training/pulina-2017-04.log.json",
#     "./training/pulina-2017-05.log.json",
#     "./training/pulina-2017-06.log.json",
#     "./training/pulina-2017-07.log.json",
#     "./training/pulina-2017-08.log.json",
    "./training/pulina-2017-09.log.json",
#     "./training/pulina-2017-10.log.json",
#     "./training/pulina-2017-11.log.json",
#     "./training/pulina-2017-12.log.json",
#     "./training/pulina-2018-01.log.json",
#     "./training/pulina-2018-02.log.json",
#     "./training/pulina-2018-03.log.json",
#     "./training/pulina-2018-04.log.json",
#     "./training/pulina-2018-05.log.json",
#     "./training/pulina-2018-06.log.json",
    "./training/pulina-2018-07.log.json",
#     "./training/pulina-2018-08.log.json",
#     "./training/pulina-2018-09.log.json",
#     "./training/pulina-2018-10.log.json",
#     "./training/pulina-2018-11.log.json",
#     "./training/pulina-2018-12.log.json",
#     "./training/pulina-2019-01.log.json",
    "./training/pulina-2019-02.log.json",
#     "./training/pulina-2019-03.log.json",
#     "./training/pulina-2019-04.log.json",
#     "./training/pulina-2019-05.log.json",
#     "./training/pulina-2019-06.log.json",
#     "./training/pulina-2019-07.log.json",
#     "./training/pulina-2019-08.log.json",
    "./training/pulina-2019-09.log.json",
#     "./training/pulina-2019-10.log.json",
#     "./training/pulina-2019-11.log.json",
#     "./training/pulina-2019-12.log.json",
#     "./training/pulina-2020-01.log.json",
#     "./training/pulina-2020-02.log.json",
#     "./training/pulina-2020-03.log.json",
    "./training/pulina-2020-04.log.json",
    # "./training/pulina-2020-05.log.json",
    # "./training/pulina-2020-06.log.json",
    # "./training/pulina-2020-07.log.json",
    # "./training/pulina-2020-08.log.json",
    # "./training/pulina-2020-09.log.json",
    # "./training/pulina-2020-10.log.json",
    # "./training/pulina-2020-11.log.json",
    "./training/pulina-2020-12.log.json",
    # "./training/pulina-2021-01.log.json",
    # "./training/pulina-2021-02.log.json",
    "./training/pulina-2021-03.log.json",
    # "./training/pulina-2021-04.log.json",
#     "./training/pulina-2021-05.log.json"
)

import sopel.module

@sopel.module.rule('[^\*]*')

def talkbot_all(bot, trigger):
    only_message_all_check_only = trigger.split(": ", 1)

    if len(only_message_all_check_only) >= 2 and only_message_all_check_only[1]:
      only_message_all = trigger.split(": ", 1)[1]

      # Parrot mode:
      #bot.say(only_message_all)
      chatbot.get_response(only_message_all)
    else:
      only_message_all_no_colons = trigger
      
      # Parrot mode:
      #bot.say(only_message_all_no_colons)
      chatbot.get_response(only_message_all_no_colons)

@sopel.module.nickname_commands('[^\*]*')

def talkbot(bot, trigger):
    only_message_check_only = trigger.split(": ", 1)

    if len(only_message_check_only) >= 2 and only_message_check_only[1]:
      only_message = trigger.split(": ", 1)[1]

      # Parrot mode:
      #bot.reply(only_message)

      request = only_message
      response = chatbot.get_response(request)
      bot.reply(response)

      #if chatbot.confidence > 0.80:
      #  request = only_message
      #  response = chatbot.get_response(request)
      #  bot.reply(response)
      
      #if chatbot.confidence < 0.80:
      #  bot.reply('En ymmärrä. Opettelen vielä...')
