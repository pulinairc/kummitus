"""
megahal.py - MegaHAL for sopel IRC bot
Copyright 2021, Roni Laukkarinen [roni@dude.fi]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just
  can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""

import megahal
from megahal import *
import sopel.module

megahal = MegaHAL()
megahal.train('/home/rolle/.sopel/trainerfile.txt')

# Learn everything (for some reason this regex causes problems when someone says ":(" for example):
@sopel.module.rule(".*")

def megahal_all(bot, trigger):
    only_message_all_check_only = trigger.split(": ", 1)

    if len(only_message_all_check_only) >= 2 and only_message_all_check_only[1]:
      only_message_all = trigger.split(": ", 1)[1]
      megahal.learn(only_message_all)
      megahal.sync()
      megahal.close() 

@sopel.module.nickname_commands(".*")

def megahal(bot, trigger):

    only_message_check_only = trigger.split(": ", 1)

    if len(only_message_check_only) >= 2 and only_message_check_only[1]:
      query = trigger.replace('!', '')
      only_message = query.split(": ", 1)[1]

      request = only_message
      megahal.learn(only_message)
      response = megahal.get_reply(request)
      bot.reply(response)
