"""
autokick.py - Auto kick for slur words for sopel IRC bot
Copyright 2023, rolle [roni@dude.fi]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""
import re
import sopel.plugin

# Define the words that will trigger the kick action
trigger_words = ["transu", "neekerit", "nigger", "neekeripoika", "neekeri", "neekerin", "mamujen", "matujen", "mamu", "matu", "rättipää", "rättipäät", "hurri", "karvakäsi", "karvakäden", "karvakäsien", "kumihuuli", "kumihuulien", "kumihuulet", "kanukki", "kanukit", "japsi", "jutku", "jutkut", "jutkujen", "jutkuista", "jutkuille", "polakki", "polakit", "polakkien", "lakupekka", "lakupekat", "lakupekkojen", "niggers", "rullahuuli", "ryssä", "ryssät", "mokkakikkeli", "mokkakikkelit", "inkkari", "inkkarit", "japsit", "hurrit", "kehari", "keharit", "kehareiden", "vinosilmä", "vinosilmät", "vinosilmien", "vinosilmäinen", "yön Timo", "yöntimo"]

CHANNEL = '#pulina'


def get_trigger_word(text):
    for word in trigger_words:
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            return word
    return None


# Only what someone said on the channel itself: not private messages, not the nick!user@host of the line,
# and never an op or half-op, so an opped bot cannot start a kick war.
@sopel.plugin.rule('.*')
@sopel.plugin.require_chanmsg
def kick_on_trigger(bot, trigger):
    if trigger.sender.lower() != CHANNEL:
        return
    trigger_word = get_trigger_word(trigger.plain)
    if not trigger_word:
        return
    chan = bot.channels.get(CHANNEL)
    if not chan or not chan.has_privilege(bot.nick, sopel.plugin.OP) or chan.has_privilege(trigger.nick, sopel.plugin.HALFOP):
        return
    bot.kick(trigger.nick, CHANNEL, f"Ei slurreja. Mainitsit sanan '{trigger_word}'.")


# A message to ops when bot joins
#@sopel.module.event('JOIN')
#@sopel.module.rule('.*')
#def ops_message(bot, trigger):

#    if trigger.nick == bot.nick:
#      bot.say('Hei, pistäkääs opit (ping rolle, mustikkasoppa) eli /op kummitus, jotta saadaan moderointitoiminnot käyttöön.')
