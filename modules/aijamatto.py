# coding=utf-8
"""
aijamatto.py
Made by Roni "rolle" Laukkarinen
"""
import sopel.module
import random

@sopel.module.commands('aijamatto', 'äijämatto', 'äm', 'äijästoori')

def aijamatto(bot, trigger):
    matto = random.choice(list(open('/home/rolle/.sopel/modules/aijamatto.txt')))
    bot.say(matto)