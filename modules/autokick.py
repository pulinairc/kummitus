"""
autokick.py - Auto kick for slur words for sopel IRC bot
Copyright 2023, rolle [roni@dude.fi]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""
import re
import sopel.module

# Define the words that will trigger the kick action
trigger_words = ["transu", "neekeri", "mamu", "matu", "rättipää", "rumasana"]

# Function to check if the message contains the trigger word as a whole word
# Function to check if the message contains any of the trigger words
def get_trigger_word(text):
    for word in trigger_words:
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, text, re.IGNORECASE):
            return word
    return None

# The trigger function using the 'rule' decorator
@sopel.module.rule('.*')  # This will trigger on any messageThis will trigger on any message
def kick_on_trigger(bot, trigger):
    trigger_word = get_trigger_word(trigger.raw)
    if trigger_word:
        kick_message = f"Ei slurreja. Mainitsit sanan '{trigger_word}'."
        bot.kick(trigger.nick, '#pulina', kick_message)

# A message to ops when bot joins
@sopel.module.event('JOIN')
@sopel.module.rule('.*')
def ops_message(bot, trigger):
    # Check only for bot joins, not every user
    if trigger.nick == bot.nick:
      bot.say('Hei, pistäkääs opit (ping rolle, mustikkasoppa) eli /op kummitus, jotta saadaan moderointitoiminnot käyttöön.')
