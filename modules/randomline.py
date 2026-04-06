# coding=utf-8
"""
randomline.py
Made by Roni "rolle" Laukkarinen
"""
import os
import glob
import json
import re
import sopel.module
import random

@sopel.module.commands('randomjuttu', 'rj')
def randomline(bot, trigger):
    files = glob.glob("/home/rolle/.sopel/training-txt/*.txt")
    files += glob.glob("/home/rolle/pulina.fi/pulina-days/*.log")
    file = random.choice(files)
    lines = list(open(file))
    random.shuffle(lines)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip log metadata lines
        if line.startswith('---') or '-!-' in line:
            continue
        # Parse live log format: "HH:MM <nick> message"
        match = re.match(r'^\d{2}:\d{2}\s+<[^>]+>\s+(.+)$', line)
        if match:
            line = match.group(1)
        # Skip lines that are just URLs or too short
        if len(line) < 3:
            continue
        bot.say(line)
        return