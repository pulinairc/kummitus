"""
autokick.py - Auto kick for slur words for sopel IRC bot
Copyright 2023, rolle [roni@dude.fi]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""
import sopel.module

# Define the words that will trigger the kick action
trigger_words = ["transu", "neekeri", "rumasana"]

# Function to check if the message contains any of the trigger words
def get_trigger_word(text):
    return next((word for word in trigger_words if word in text.lower()), None)

# The trigger function using the 'rule' decorator
@module.rule('.*')  # This will trigger on any message
def kick_on_trigger(bot, trigger):
    trigger_word = get_trigger_word(trigger.raw)
    if trigger_word:
        # Replace 'YourMessageHere' with the message you want to send when kicking the user
        kick_message = f"Sääntö #4, ei slurreja. Mainitsit sanan '{trigger_word}'."
        bot.kick(trigger.sender, trigger.nick, kick_message)
