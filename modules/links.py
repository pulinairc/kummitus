# coding=utf-8
"""
links.py
Made by rolle
"""
import sopel.module

@sopel.module.commands('linkit', 'urlit')
def rules(bot, trigger):
    bot.say('https://botit.pulina.fi/pulinalinkit/')
