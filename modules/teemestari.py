# coding=utf-8
"""
teemestari.py
Made by rolle
"""
import sopel.module
import random

@sopel.module.commands('tee', 'teemestari')

def tea(bot, trigger):
    tea = random.choice(list(open('/home/rolle/.sopel/modules/teemestari.txt')))
    bot.say(tea)
