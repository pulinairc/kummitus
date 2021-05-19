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

    line = open(file).read()
    loadlist = json.loads(line)
    bot.say(random.choice(loadlist))