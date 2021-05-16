"""
flip.py - Because flipping things is fun!
Copyright 2016, Kharidiron [kharidiron@gmail.com]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just
  can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""

from sopel.module import commands, example
import upsidedown

@commands("flippaa")
@example('!flippaa')
@example('!flippaa pöytä/pöydät')
@example('!flippaa pöydän yli')
@example('!flippaa henkilö')
@example('!flippaa <nimimerkki>')
def flip(bot, trigger):
    """Flippaa juttuja ... se on se pointti."""
    if not trigger.group(2):
        bot.say("Mitä flipataan? o.o")
        return

    target = " ".join(trigger.group().split()[1:])
    try:
        if target == "pöytä":
            return bot.say(u"(╯°□°）╯︵ ┻━┻")
        elif target == "pöydän yli":
            return bot.say(u"┬──┬ ノ(゜-゜ノ)")
        elif target == "pöydät":
            return bot.say(u"┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻")
        elif target == "aivot":
            return bot.say(u"ಠ﹏ಠ")
        elif target == "lintu":
            return bot.say(u"t(°□ °t)")
        elif target == "henkilö":
            return bot.say(u"(╯°Д°）╯︵ /(.□ . \)")
        elif target == "russia":
            bot.reply("In Soviet Russia, table flip you!")
            return bot.say(u"┬─┬ ︵  ( \o°o)\\")
        else:
            return bot.say(upsidedown.transform(target))
    except ValueError:
        return bot.reply(u"Ei tuota voi flipata. -_-;")


if __name__ == "__main__":
    pass