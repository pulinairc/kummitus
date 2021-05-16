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

chatbot = ChatBot('Ron Obvious')
trainer = ChatterBotCorpusTrainer(chatbot)

trainer.train(
    "/home/rolle/.sopel/modules/chatterbot-corpus/chatterbot_corpus/data/finnish/"
)

# Stores data in file so that it can remember
trainer.export_for_training('./export.json')

import sopel.module

@sopel.module.commands(".*")
def chatterbot_everyline(bot, trigger):
    match_everything = trigger.replace('!', '')
    only_message_everything = match_everything.split(": ",1)[1] 
    bot.say(only_message_everything)

@sopel.module.nickname_commands(".*")

def chatterbot(bot, trigger):
    query = trigger.replace('!', '')

    only_message = query.split(": ",1)[1] 

    bot.reply(only_message)
    #request = query
    #response = chatbot.get_response(request)

    #bot.reply(response)
