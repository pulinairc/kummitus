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

# Create a new instance of a ChatBot
chatbot = ChatBot(
    'kummitus',
    storage_adapter='chatterbot.storage.SQLStorageAdapter',
    logic_adapters=[
        {
            "chatterbot.logic.MathematicalEvaluation",
            'import_path': 'chatterbot.logic.BestMatch',
            'default_response': 'En ymmärrä. Opettelen vielä...',
            'maximum_similarity_threshold': 0.90
        }
    ]
)
#trainer = ChatterBotCorpusTrainer(chatbot)

#trainer.train(
#    "/home/rolle/.sopel/modules/chatterbot-corpus/chatterbot_corpus/data/finnish/"
#)

from chatterbot import ChatBot

from chatterbot.trainers import ListTrainer

conversations = [
  "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mee nukkumaan.", "Mee nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Iltaa", "Moi", "Iltaa", "Mitäpä kuuluu?", "Mitäpä kuuluu?", "Hyvää", "Mitäpä kuuluu?", "No hyvä.", "No hyvä.", "Moi", "No hyvä.", "Moi vaan.", "Moi vaan.", "Moi", "Moi vaan.", "Kiva juttu.", "Kiva juttu.", "Iltaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mee nukkumaan.", "Mee nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Onko?", "On se.", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Kiva juttu.", "Onko kivaa", "Onko kivaa", "Iltaa", "Onko kivaa", "Onko?", "Onko?", "On.", "Onko?", "Ei ole.", "Ei ole.", "Kalja on hyvää", "Ei ole.", "Vai mitä?", "Vai mitä?", "Moi", "Vai mitä?", "No moi moi.", "No moi moi.", "Moi", "No moi moi.", "Kalja on pahaa,.", "Kalja on pahaa,.", "Moi", "Kalja on pahaa,.", "Nyt on yö.", "Nyt on yö.", "Iltaa", "Nyt on yö.", "Pitäiskö mennä nukkumaan?", "Pitäiskö mennä nukkumaan?", "Iltaa", "Pitäiskö mennä nukkumaan?", "Iltaa iltaa.", "Iltaa iltaa.", "Iltaa", "Iltaa iltaa.", "Miten menee?", "Miten menee?", "Moi", "Miten menee?", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Mitä kuuluu?", "Hyvä että kuuluu hyvää.", "Hyvä että kuuluu hyvää.", "Moi", "Hyvä että kuuluu hyvää.", "Moi moi.", "Moi moi.", "Moi", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mee nukkumaan.", "Mee nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Onko?", "Ei ole kaljaa.", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "Kalja on loppu.", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi moi.", "Moi", "Moi", "Moro!", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Onko?", "Onko?", "On.Onko?", "On.Onko?", "Ei ole.Kalja", "Ei ole.Kalja", "Kalja on hyvää", "Kalja on hyvää", "Kalja", "Kalja", "Kalja on pahaa", "Moi", "Eiks nii", "Eiks nii", "Iltaa", "Moi", "Moro!", "Moro!", "Mitä kuuluu?", "Mitä kuuluu?", "Hyvää", "Hyvää", "Hyvää yötä", "Hyvää yötä", "Öitä!", "Öitä!", "Mene nukkumaan.", "Mene nukkumaan.", "Niin menenkin.", "Niin menenkin.", "Huomenta", "Huomenta", "Hyvää huomenta!", "Hyvää huomenta!", "Pitäisikö mennä nukkumaan?", "Pitäisikö mennä nukkumaan?", "Pitäisi.", "Pitäisi.", "Kalja", "Kalja on hyvää.", "Kalja", "Kalja", "Kalja on pahaa", "Onko kaikki hyvin?", "On.", "Onko kaikki hyvin?", "Ei ole."
]

trainer = ListTrainer(chatbot)

trainer.train(conversations)

# Stores data in file so that it can remember
trainer.export_for_training('./export.json')

import sopel.module

@sopel.module.rule('.*')

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

@sopel.module.nickname_commands('.*')

def talkbot(bot, trigger):
    only_message_check_only = trigger.split(": ", 1)

    if len(only_message_check_only) >= 2 and only_message_check_only[1]:
      only_message = trigger.split(": ", 1)[1]

      # Parrot mode:
      #bot.reply(only_message)

      if chatbot.confidence > 0.80:
        request = only_message
        response = chatbot.get_response(request)
        bot.reply(response)
      
      if chatbot.confidence < 0.80:
        bot.reply('En ymmärrä. Opettelen vielä...')
