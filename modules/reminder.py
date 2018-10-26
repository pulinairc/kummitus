"""
    reminder.py
    Made by Sikanaama
    Reminds users about their stuff
"""

import datetime
import re
import sopel.module
from threading import Timer

REGEX = r'^.muistuta (?:(\d{1,2}:\d{2})|(?:(\d+)\s*h\s*)?(?:(\d+)\s*min\s*)?(?:(\d+)\s*s)?)(.*)'

def reminder(bot, trigger):
    del bot.memory['reminder_queue'][trigger.nick]
    bot.say('Muistutus %s: %s' % (trigger.nick, trigger.group(5).strip()))

@sopel.module.rule(REGEX)
@sopel.module.example('!muistuta 02:00 Nukkumaan pitäis mennä')
def module(bot, trigger):
    """
        Time can be given in the following formats:
        As time 02:00 or 2:00
        As interval 1h40min, 2h, 30min or 10s
    """
    
    if not bot.memory.contains('reminder_queue'):
        bot.memory['reminder_queue'] = {}

    now = datetime.datetime.now()
    time = None
    timeformat = '%H:%M'
    
    if trigger.group(1):
        parts = [int(t, 10) for t in trigger.group(1).split(':')]
        time = now.replace(hour=parts[0], minute=parts[1], second=0, microsecond=0)
        if time < now:
            time += datetime.timedelta(1)
    else:
        diff = 0
        if trigger.group(2):
            diff += int(trigger.group(2), 10) * 3600
        if trigger.group(3):
            diff += int(trigger.group(3), 10) * 60
        if trigger.group(4):
            diff += int(trigger.group(4), 10)
        if diff > 0:
            if diff > 86400:
                bot.say('%s: En mä nyt noin pitkälle muista' % (trigger.nick))
                return
            time = now + datetime.timedelta(seconds=diff)
            timeformat = '%H:%M:%S'
    
    if not time:
        bot.say('%s: Virheellinen aika, anna joko kellonaika (00:00) tai aikaväli (esim. 1h 30min)' % (
            trigger.nick
        ))
        return
    
    if trigger.nick in bot.memory['reminder_queue']:
        old = bot.memory['reminder_queue'][trigger.nick]
        old.cancel()
        bot.say('%s: edellinen muistutus peruttu, uusi asetettu kello %s' % (
            trigger.nick,
            time.strftime(timeformat),
        ))
        del bot.memory['reminder_queue'][trigger.nick]
    else:
        bot.say('%s: Muistutus asetettu kello %s' % (
            trigger.nick,
            time.strftime(timeformat),
        ))

    t = Timer((time - now).total_seconds(), reminder, args=(bot, trigger))
    t.start()
    bot.memory['reminder_queue'][trigger.nick] = t
