# coding=utf-8
"""
battle.py
Made by Roni Laukkarinen
"""
import sopel.module
import sys
import re
import random

@sopel.module.commands('battle')

def battle(bot, message):
    if re.match('^battle .', message, 0):
        query = message[len("battle "):].split(", ")
        #print(query[0])
        range = 100
        answer = ""
        i = 0
        while i < len(query) - 1:
            randval = random.randint(0,range)
            range -= randval
            answer += query[i] + ": " + str(randval) + "%. "
            i += 1

    answer += query[len(query) - 1] + " " + str(range) + "%"
    return answer

print(battle(sys.argv[1]))