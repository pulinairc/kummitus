# coding=utf-8
"""
games.py
Made by Roni Laukkarinen
"""
import sopel.module

@sopewl.module.commands('pelit')
def olenaa(bot, trigger):
    bot.say('#pulina-kanavan lempipelit, ole hyvä: https://www.pulina.fi/pelit')
