# coding=utf-8
"""
do.py
Made by rolle
"""
import sopel.module
import random

@sopel.module.commands('do', 'keksi', 'tekemistä')

def do(bot, trigger):
    does = random.choice(list(open('/home/rolle/.sopel/modules/tekemiset.txt')))
    bot.say(does)