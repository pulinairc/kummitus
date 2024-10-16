"""
logitus.py
Made by rolle
"""
from sopel import module
import os
from datetime import datetime

LOG_FILE = 'pulina.log'
CHANNEL = '#pulina'

def log_message(message):
    timestamp = datetime.now().strftime('%H:%M')  # Hakee nykyisen ajan muodossa HH:MM
    with open(LOG_FILE, 'a') as f:
        f.write(f'{timestamp} {message}\n')

@module.rule('.*')
def log_channel_message(bot, trigger):
    nick = trigger.nick
    message = trigger.group(0)
    channel = trigger.sender

    # Log messages from the channel
    if channel == CHANNEL and message.strip():
        log_message(f'<{nick}> {message}')

    # Log own messages
    if channel == CHANNEL and message.strip() and nick == bot.nick:
        log_message(f'<{bot.nick}> {message}')

# Log joins
@module.event('join')
@module.rule('.*')
def log_join(bot, trigger):
    channel = trigger.sender
    nick = trigger.nick

    if channel == CHANNEL:
        log_message(f'{nick} liittyi kanavalle.')

# Log parts
@module.event('part')
@module.rule('.*')
def log_part(bot, trigger):
    channel = trigger.sender
    nick = trigger.nick

    if channel == CHANNEL:
        log_message(f'{nick} lähti kanavalta.')

# Log quits
@module.event('quit')
@module.rule('.*')
def log_quit(bot, trigger):
    nick = trigger.nick
    reason = trigger.args[0] if trigger.args else 'ei syytä'

    log_message(f'{nick} lopetti IRC-yhteyden: {reason}')

# Log kicks
@module.event('kick')
@module.rule('.*')
def log_kick(bot, trigger):
    channel = trigger.sender
    kicker = trigger.nick
    kicked = trigger.args[0]
    reason = trigger.args[1] if len(trigger.args) > 1 else 'ei syytä'

    if channel == CHANNEL:
        log_message(f'{kicked} potkaistiin kanavalta käyttäjän {kicker} toimesta: {reason}')

# Log bans
@module.event('ban')
@module.rule('.*')
def log_ban(bot, trigger):
    channel = trigger.sender
    banner = trigger.nick
    banned = trigger.args[0]

    if channel == CHANNEL:
        log_message(f'{banned} bannattiin kanavalta käyttäjän {banner} toimesta.')

def setup(bot):
    if not os.path.isfile(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            # Create empty file if it doesn't exist
            f.write('')
