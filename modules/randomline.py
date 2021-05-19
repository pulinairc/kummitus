# coding=utf-8
"""
randomline.py
Made by Roni "rolle" Laukkarinen
"""
import os
import glob
import json
import sopel.module
import random

@sopel.module.commands('randomjuttu')

def randomline(bot, trigger):
    files = glob.glob("/home/rolle/.sopel/training/*.json").replace('"', '').rstrip(',')
    file = random.choice(files)
    line = random.choice(list(open(file)))
    bot.say(line)