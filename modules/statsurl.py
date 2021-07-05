# coding=utf-8
"""
statsurl.py
Made by rolle
"""
import sopel.module
import random

@sopel.module.commands('stats')
@sopel.module.commands('statsit')
@sopel.module.commands('tilastot')

def stats (bot, trigger):
    bot.say('--> https://www.pulina.fi/statsit')
