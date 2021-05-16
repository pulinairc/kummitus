"""
hali.py - Because we all need a hug!
Copyright 2018, Kharidiron [kharidiron@gmail.com]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just
  can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""

from random import choice

from sopel.module import commands, example


verb = ["halaa", "halaa", "halaa", "litistää", "taklaa", "ruttuhalaa",
        "syleilee", "puristaa", "rutistaa", "ruttaa", "pusertaa"]
flavor = ["tiukasti", "hellästi", "vammasimmalla mahdollisella tavalla", "rakastavaisesti", "söpösti", "kivasti", "lämpimästi", "ja puristaa perseestä",
          "tosi tiukasti", "rauhoittavasti", "takaapäin"]

@commands('hali')
@example('!hali')
@example('!hali <nimimerkki>')
def hug(bot, trigger):
    """Anna halu... tai jopa enemmän."""
    hugged = trigger.group(3) if trigger.group(3) else "ketään erityisesti"
    bot.say(f"{trigger.nick} {choice(verb)} {hugged} {choice(flavor)}.")

if __name__ == "__main__":
    pass