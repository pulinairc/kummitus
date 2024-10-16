"""
logitus.py
Made by rolle
"""
from sopel import module
import os

LOG_FILE = 'pulina.log'
CHANNEL = '#pulina'

def log_message(nick, message):
    with open(LOG_FILE, 'a') as f:
        f.write(f'<{nick}> {message}\n')

@module.rule('.*')
def log_channel_message(bot, trigger):
    nick = trigger.nick
    message = trigger.group(0)
    channel = trigger.sender

    if channel == CHANNEL and message.strip():
        log_message(nick, message)

def setup(bot):
    if not os.path.isfile(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write('')
