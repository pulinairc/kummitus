# coding=utf-8
"""
kahvi.py
Made by mustikkasoppa
"""
import sopel.module
import random

@sopel.module.commands('kahvi')
def kahvi(bot, trigger):
  kahvi = random.choice(list(open('/home/rolle/.sopel/modules/kahvi.txt')))
  bot.say(kahvi)
