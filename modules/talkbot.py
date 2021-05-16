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

chatbot = ChatBot('kummitus')
#trainer = ChatterBotCorpusTrainer(chatbot)

#trainer.train(
#    "/home/rolle/.sopel/modules/chatterbot-corpus/chatterbot_corpus/data/finnish/"
#)

from chatterbot import ChatBot

from chatterbot.trainers import ListTrainer

conversation = [
    "Moi",
    "Moro!",
    "Mitä kuuluu?",
    "Hyvää",
    "Hyvää yötä",
    "Öitä!",
    "Mene nukkumaan.",
    "Niin menenkin.",
    "Huomenta",
    "Hyvää huomenta!",
    "Pitäisikö mennä nukkumaan?",
    "Pitäisi.",
    "Onko?",
    "On."
    "Onko?",
    "Ei ole."
    "Kalja",
    "Kalja on hyvää",
    "Kalja",
    "Kalja on pahaa"
]

trainer = ListTrainer(chatbot)

trainer.train(conversation)

# Stores data in file so that it can remember
trainer.export_for_training('./export.json')

import sopel.module

@sopel.module.rule('.*')

def talkbot_all(bot, trigger):
    only_message_all = trigger.split(": ", 0)[1] 

    # Parrot mode:
    bot.say(only_message_all)

    #request = only_message
    #response = chatbot.get_response(request)
    #bot.reply(response)


@sopel.module.nickname_commands('.*')

def talkbot(bot, trigger):
    query = trigger.replace('!', '')

    only_message = query.split(": ", 1)[1] 

    # Parrot mode:
    #bot.reply(only_message)

    request = only_message
    response = chatbot.get_response(request)
    bot.reply(response)
