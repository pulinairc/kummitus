# coding=utf-8
"""
games.py
Made by rolle
"""
import sopel.module

@sopel.module.commands('pelit')
def games(bot, trigger):
    bot.say('#pulina-kanavan lempipelit, ole hyvä: https://www.pulina.fi/pelit')
