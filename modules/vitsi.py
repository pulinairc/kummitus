# coding=utf-8
"""
vitsi.py
Made by Roni Laukkarinen
"""
import sopel.module
import random

@sopel.module.commands('vitsi')

def vitsi(bot, trigger):
    joke = random.choice(list(open('/home/rolle/.sopel/modules/vitsit.txt')))
    bot.say(joke)