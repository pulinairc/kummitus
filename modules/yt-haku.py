# coding=utf-8
"""
youtube-haku
"""
import sopel.module
from searchyt import searchyt

BASE_URL = 'https://youtu.be/'

@sopel.module.commands('yt')
def pakko(bot, trigger):
    if not trigger.group(2):
        return

    syt = searchyt()
    res = syt.search(trigger.group(2))

    if len(res) > 0:
        bot.say('hakusanoilla "' + trigger.group(2) + '" löytyi: ' + BASE_URL + res[0]['id'] + ' | ' +
                res[0]['title'] + ' | lataaja: ' + res[0]['author'])

    else:
        bot.say('hakusanoilla "' + trigger.group(2) + '" ei löytynyt mitään')


