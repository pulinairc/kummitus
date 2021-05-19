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
    files = glob.glob("./training/*.json")
    file = random.choice(files)

    with open(file) as f:
        content = json.loads(f.read())
        winner = choice(content)
        line = json.dumps(winner, indent=4)
        bot.say(line)