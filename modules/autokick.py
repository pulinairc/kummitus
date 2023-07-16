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
        kick_message = f"pulina.fi/saannot numero 4: Ei slurreja. Mainitsit sanan '{trigger_word}'."
        bot.kick(trigger.nick, '#pulina', kick_message)

# The on_join event to make the bot join channels and send a message to ops if not opped
@sopel.module.event('JOIN')
def on_join(bot, trigger):
    op_message = f"Hei, pistäkääs opit eli /op kummitus, jotta saadaan moderointitoiminnot käyttöön."
    bot.say(op_message)
