# coding=utf-8
"""
battle.py
Made by lapyo
"""
import sys
import re
import random
import sopel.module

@sopel.module.commands('battle')

def battle(bot, trigger):

    word = trigger.group(2).strip()
    query = word = trigger.group(2).strip().split(", ")
    range = 100
    answer = "battle: "
    i = 0
    while i < len(query) - 1:
        randval = random.randint(0,range)
        range -= randval
        answer += query[i] + ": " + str(randval) + "%. "
        i += 1

    answer += query[len(query) - 1] + ": " + str(range) + "%"
    bot.say(answer)
