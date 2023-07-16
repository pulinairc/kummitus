"""
autokick.py - Auto kick for slur words for sopel IRC bot
Copyright 2023, rolle [roni@dude.fi]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""
import sopel.module

# Define an array of words in python
words = ['rumasana']

# Define bot, trigger all messages
def kickbot(bot, trigger):

    # Check if any of the words are in the message
    if any(word in trigger for word in words):
        bot.say("Kenkää!")
