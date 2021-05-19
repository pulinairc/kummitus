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
  
    with open(file) as fp:
        data = json.load(fp)
        lines = data["conversations"]
        random_index = randint(0, len(questions)-1)
        randomline = lines[random_index]['lines']

        bot.say(randomline)