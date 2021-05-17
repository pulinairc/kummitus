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
    "./export.json"
)

# Stores data in file so that it can remember
trainer.export_for_training('./export.json')

import sopel.module

@sopel.module.rule('\*')

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

@sopel.module.nickname_commands('\*')

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
