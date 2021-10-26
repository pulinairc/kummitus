"""
kuha.py
Lannistajakuha.com
Sopel module made by rolle
"""

@commands('kuha', 'lannistajakuha')

def kuha(bot, trigger):
    moti = random.choice(list(open('/home/rolle/.sopel/modules/kuhat.txt')))
    bot.say(kuha)
