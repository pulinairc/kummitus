"""
battle.py
Made by lapyo and Sikanaama
"""
import random
import re
import sopel.module

NORRIS = re.compile(r'chuck norris', re.I)

@sopel.module.commands('battle')
def battle(bot, trigger):
    group = trigger.group(2)
    if not group:
        bot.say('Tarttis parametrejä')
        return
    
    query = re.split(r',\s*\S+', group.strip())
    if len(query) < 2:
        bot.say('Tarttis enemmän parametrejä')
        return

    weights = []
    weight = 0
    for x in range(len(query)):
        word = query[x]
        if NORRIS.match(word):
            answer = ', '.join(['%s: %d%%' % (query[i], 100 if i is x else 0) for i in range(len(query))])
            bot.say(answer)
            return
        rand = random.random()
        weights.append(rand)
        weight += rand
    
    values = []
    total = 0
    for w in weights:
        value = round(w / weight * 100)
        values.append(value)
        total += value
    
    # Rounding percentages might cause total to be 101, let's
    # snatch it from the greatest value (these are random after all) :P
    if total > 100:
        max = 0
        i = 0
        for x in range(len(values)):
            v = values[x]
            if v > max:
                max = v
                i = x
        values[i] -= total - 100
    
    answer = ', '.join(['%s: %d%%' % (query[x], values[x]) for x in range(len(query))])
    bot.say(answer)
