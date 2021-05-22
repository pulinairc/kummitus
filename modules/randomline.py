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

@sopel.module.commands('randomjuttu', 'rj')

def randomline(bot, trigger):
    files = glob.glob("/home/rolle/.sopel/training-txt/*.txt")
    file = random.choice(files)
    # line = random.choice(list(open(file))).replace('",', '').replace('"', '')
    line = random.choice(list(open(file)))
    bot.say(line)