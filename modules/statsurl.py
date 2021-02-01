# coding=utf-8
"""
statsurl.py
Made by Roni Laukkarinen
"""
import sopel.module
import random

@sopel.module.commands('stats')
@sopel.module.commands('statsit')
@sopel.module.commands('tilastot')

def stats (bot, trigger):
    bot.say('Kanavan tilastot: https://pulina.fi/statsit - Kuukausi: https://pulina.fi/statsit/kuukausi - Reaaliaikainen hall of fame: https://peikko.us/toptod.php')
