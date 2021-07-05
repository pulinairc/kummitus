# coding=utf-8
"""
motivaatiovalas.py
Made by rolle
"""
import sopel.module
import random

@sopel.module.commands('moti', 'motivaativalas', 'motivaatio')

def vitsi(bot, trigger):
    moti = random.choice(list(open('/home/rolle/.sopel/modules/motit.txt')))
    bot.say(moti)
