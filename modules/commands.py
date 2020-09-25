# coding=utf-8
"""
commands.py
Made by Roni Laukkarinen
"""
import sopel.module

@sopel.module.commands('komennot')
def commands(bot, trigger):
    bot.say('Bottien komennot: https://www.pulina.fi/komennot')
