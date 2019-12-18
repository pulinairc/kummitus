import pymongo
from pymongo import MongoClient

import re
import datetime
import math

import sopel
from sopel.module import commands
from sopel.config.types import StaticSection, ValidatedAttribute


yes_answers = ["on", "yes", "+", "yep", "yup", "yeah"]
no_answers = ["off", "no", "nope", "nop", "no way", "nein"]

format_strip = re.compile("\x0f|\x1f|\x02|\x03(?:\d{1,2}(?:,\d{1,2})?)?",
                          re.UNICODE)

self = None


class PollSection(StaticSection):
    url = ValidatedAttribute('url', default="mongodb://localhost:27017")


def configure(config):
    config.define_section('poll', PollSection, validate=False)
    config.poll.configure_setting('url', 'MongoDB URL')


def setup(bot):
    bot.config.define_section('poll', PollSection)
    global self
    self = Poll(bot)


class Poll:

    partial = {}

    codename = re.compile("^[A-Za-z0-9_.-]{3,30}$")
    option = re.compile("^\S.*$")

    def __init__(self, bot):
        self.url = bot.config.poll.url
        self.admins = bot.config.core.admins + [bot.config.core.owner]
        self.client = MongoClient(self.url)
        self.db = self.client.sopel.poll
        self.db.create_index([("name", pymongo.ASCENDING)])

        self.updates()

    def __del__(self):
        self.client.close()

    def updates(self):
        # Added "anonymous" polls
        self.db.update_many({
            "anonymous": {
                "$exists": False
            }
        }, {"$set": {"anonymous": False}})

        # Renamed field to more sensible name
        self.db.update_many({
            "public": {"$exists": True}
        }, {"$rename": {"public": "interim"}})

        # Renamed `open` to `status`
        self.db.update_many({"open": True},
                            {"$set": {"status": 1},
                             "$unset": {"open": 0}})
        self.db.update_many({"open": False},
                            {"$set": {"status": 2},
                             "$unset": {"open": 0}})

    def new_poll(self, author, name, title, options, date, interim, anonymous):
        poll = {"author": author,
                "name": name,
                "title": title,
                "options": options,
                "date": date,
                "status": 2,
                "interim": interim,
                "anonymous": anonymous}
        self.db.insert_one(poll)

    def get_poll(self, name):
        return self.db.find_one({"name": name})

    def del_poll(self, name):
        return self.db.delete_one({"name": name}).deleted_count

    def open(self, name):
        self.db.find_one_and_update({"name": name}, {
            "$set": {"status": 1}
        })

    def close(self, name):
        self.db.find_one_and_update({"name": name}, {
            "$set": {"status": 0}
        })

    def add_vote(self, user, index, name):
        poll = self.get_poll(name)
        if not poll:
            return "no such poll"
        if poll["status"] == 0:
            return "poll is closed"
        opt = [x for x in filter(
            lambda item: item["index"] == index,
            poll["options"]
        )]
        if len(opt) == 0:
            return "no such index"
        opt = opt[0]
        if user in opt["votes"]:
            return "already voted"
        self.db.find_one_and_update(
            {"name": name,
             "options.index": index},
            {"$push": {"options.$.votes": user}}
        )
        return True

    def del_vote(self, user, index, name):
        poll = self.get_poll(name)
        if not poll:
            return "no such poll"
        if not poll["status"]:
            return "poll is closed"
        opt = [x for x in filter(
            lambda item: item["index"] == index,
            poll["options"]
        )]
        if len(opt) == 0:
            return "no such index"
        opt = opt[0]
        if user not in opt["votes"]:
            return "haven't voted"
        self.db.find_one_and_update(
            {"name": name,
             "options.index": index},
            {"$pull": {"options.$.votes": user}}
        )
        return True

    def vote(self, user, index, name):
        poll = self.get_poll(name)
        if not poll:
            return "no such poll"
        if poll["status"] == 0:
            return "poll is closed"
        for opt in poll["options"]:
            if opt["index"] == index:
                break
        else:
            return "no such index"
        already_voted = [x for x in filter(
            lambda item: user in item["votes"],
            poll["options"]
        )]
        if len(already_voted) > 0:
            self.del_vote(user, already_voted[0]["index"], name)
        self.add_vote(user, index, name)
        return True

    def isReady(self, part_poll):
        if (part_poll["name"] and
                part_poll["title"] and
                part_poll["options"] and
                len([x for x in part_poll["options"]]) > 1):
            return True
        return False

    def checkAccess(self, poll, trigger):
        return (poll["author"] == trigger.nick or
                trigger.nick in self.admins)


def bar(width, perc):
    chars = [""]
    for i in range(0x258f, 0x2587, -1):
        chars.append(chr(i))
    cell_width = width / 100
    w = perc * cell_width
    blocks = math.floor(w)
    fr = w - math.floor(w)
    idx = math.floor(fr * 8)
    if idx == 8:
        idx = 7
    last_block = chars[idx]
    empty_blocks = width - blocks - len(last_block)
    if perc < 25:
        color = "05"
    elif perc < 50:
        color = "07"
    elif perc < 66:
        color = "08"
    elif perc < 85:
        color = "09"
    elif perc < 100:
        color = "10"
    else:
        color = "11"
    return ("▕" +
            "\x03" + color +
            "█" * blocks +
            last_block +
            " " * empty_blocks +
            "\x0f▏\x03")


def priv_only(bot, trigger):
    if not trigger.is_privmsg:
        bot.reply("Send this command to me as a PM!")
        return False
    return True


def format_len(s):
    actual_len = len(format_strip.sub("", s))
    return len(s) - actual_len


@commands("poll")
def poll(bot, trigger):
    try:
        cmd = trigger.group(2).split(" ")[0]
    except (AttributeError, IndexError):
        cmd = None
    if not cmd:
        return False
    else:
        arg = trigger.group(2)[len(cmd) + 1:]
    if trigger.nick not in self.partial:
        if cmd == "create":
            if not priv_only(bot, trigger):
                return
            self.partial[trigger.nick] = {
                "name": None,
                "title": None,
                "date": None,
                "options": None,
                "optional": {"anonymous": False,
                             "interim": False}}
            bot.reply("\x02SWITCHED TO EDIT MODE\x02. "
                      "Let's create a new poll!")
            bot.reply("Type \x1d.poll help\x1d for the list of commands")
            return True
        elif cmd == "help":
            if not priv_only(bot, trigger):
                return
            bot.reply("\x1d.poll create\x1d: create a poll, and switch "
                      "to edit mode.")
            bot.reply("\x1d.poll delete <poll>\x1d: delete a poll.")
            bot.reply("\x1d.poll info <poll>\x1d: show detailed report about "
                      "poll.")
            bot.reply("\x1d.poll vote <poll> <vote index>\x1d: vote. Note "
                      "that an index is expected (see .poll info), not "
                      "the full name of an option.")
            bot.reply("\x1d.poll open <poll>\x1d: open a poll.")
            bot.reply("\x1d.poll close <poll>\x1d: close a poll.")
            bot.reply("\x1d.poll list\x1d: List polls.")
            bot.reply("\x1d.poll unvote <poll>\x1d: Remove your vote.")
            bot.reply("\x1d.poll delvote <poll> <user>\x1d: Remove vote of a "
                      "user. Only available for admins.")
            return True
    else:
        # EDIT MODE
        poll = self.partial[trigger.nick]
        if cmd == "#":
            if not priv_only(bot, trigger):
                return
            if not self.codename.match(arg):
                bot.reply("Bad codename. It's length must be greater than "
                          "2 and less than 31, and it must contain "
                          "alphanumeric symbols, underline, period, or dash.")
                return
            if self.get_poll(arg):
                bot.reply("Codename must be unique.")
                return
            poll["name"] = arg
            bot.reply("The \x02codename\x02 set to '" + arg + "'!")
            return True
        elif cmd == "!":
            if not priv_only(bot, trigger):
                return
            poll["title"] = arg
            bot.reply("The \x02title\x02 set to '" + arg + "\x0f'!")
            return True
        elif cmd == "?":
            if not priv_only(bot, trigger):
                return
            bot.reply("\x02Codename:\x02 " +
                      ("'" + poll["name"] + "'"
                       if poll["name"] else "\x0307not set\x0f"))
            bot.reply("\x02Title:\x02 " +
                      ("'" + poll["title"] + "'"
                       if poll["title"] else "\x0307not set\x0f"))
            bot.reply("\x02Interim results:\x02 " +
                      ("yes" if poll["optional"]["interim"] else "no"))
            if poll["options"]:
                bot.reply("\x02Options:\x02 " + ", ".join(
                    "\x02#" + str(pos) + "\x02: " + name + "\x0f"
                    for pos, name in enumerate(poll["options"])
                ))
            else:
                bot.reply("\x02Options:\x02 \x0307not set")
            bot.reply("The poll is \x02anonymous\x02."
                      if poll["optional"]["anonymous"] else
                      "The poll is \x02unanonymous\x02.")
            if self.isReady(poll):
                bot.reply("\x0303Poll is \x02ready\x02 to be commited.")
            else:
                bot.reply("\x0307Some fields are still \x02unset\x02.")
            return True
        elif cmd == ">":
            if not priv_only(bot, trigger):
                return
            if not self.option.match(arg):
                bot.reply("Well, you didn't provide a name for your "
                          "option.")
                return
            if poll["options"] is None:
                poll["options"] = []
            poll["options"].append(arg)
            bot.reply("Added option #" + str(poll["options"].index(arg)) +
                      ": '" + arg + "\x0f'")
            return True
        elif cmd == "<":
            if not priv_only(bot, trigger):
                return
            try:
                index = int(arg)
            except ValueError:
                bot.reply("Bad argument. You're probably providing a "
                          "name. Well, I need an index.")
                return
            if poll["options"] is None:
                bot.reply("You'd better add an option before using this "
                          "command :)")
                return
            try:
                poll["options"][index]
            except IndexError:
                bot.reply("No such index.")
                return
            opt = poll["options"].pop(index)
            if len(poll["options"]) == 0:
                poll["options"] = None
            bot.reply("Removed option #" + str(index) + ": '" + opt + "\x0f'")
            return True
        elif cmd == "=":
            if not priv_only(bot, trigger):
                return
            try:
                set_name, set_arg = arg.split(" ", 1)
            except ValueError:
                set_name = arg
                set_arg = ""
            if set_name in ["anon", "anonymous"]:
                if set_arg.lower() in yes_answers:
                    poll["optional"]["anonymous"] = True
                    bot.reply("Okay, votes \x02won't\x02 be ever shown.")
                    return True
                elif set_arg.lower() in no_answers:
                    poll["optional"]["anonymous"] = False
                    bot.reply("Well, I've marked your poll as unanonymous.")
                    return True
                else:
                    bot.reply("Uh oh, I couldn't understand what you told me.")
                    return
            elif set_name == "interim":
                if set_arg.lower() in yes_answers:
                    poll["optional"]["interim"] = True
                    bot.reply("Interim results are set to be "
                              "\x02available\x02!")
                    return True
                elif set_arg.lower() in no_answers:
                    poll["optional"]["interim"] = False
                    bot.reply("Results will be \x02unavaiable\x02 until "
                              "closed!")
                    return True
                else:
                    bot.reply("Erm, what?")
                    return
            else:
                bot.reply("I'm afraid I can't decipher what you gave :<")
                return
        elif cmd == "~~~":
            if not priv_only(bot, trigger):
                return
            if not self.isReady(poll):
                bot.reply("Some fields are still unset. You can't commit "
                          "partially filled polls.")
                return
            options = [{"index": pos, "name": name, "votes": []}
                       for pos, name in enumerate(poll["options"])]
            date = datetime.datetime.utcnow()
            self.new_poll(author=trigger.nick,
                          name=poll["name"],
                          title=poll["title"],
                          date=date,
                          options=options,
                          interim=poll["optional"]["interim"],
                          anonymous=poll["optional"]["anonymous"])
            self.partial.pop(trigger.nick)
            bot.reply("Your poll is created. When you're ready, open it.")
            bot.reply("\x02SWITCHED TO NORMAL MODE\x02.")
            return True
        elif cmd == "***":
            if not priv_only(bot, trigger):
                return
            self.partial.pop(trigger.nick)
            bot.reply("Your poll is deleted. \x02SWITCHED TO NORMAL MODE\x02.")
            return True
        elif cmd == "help":
            if not priv_only(bot, trigger):
                return
            if arg == "=":
                bot.reply("\x1d.poll = anon <{yes|no}>\x1d: set whether the "
                          "poll should be anonymous (won't list nicks of "
                          "voters).")
                bot.reply("\x1d.poll = interim <{on|off}>\x1d: when 'on', "
                          "votes are shown even if the poll is open.")
                return True
            bot.reply("\x1d.poll # <code name>\x1d: set the code name. It "
                      "must only contain alphanumeric characters, underline, "
                      "dash, or period. Its length must be greater than 2 and "
                      "less than 31.")
            bot.reply("\x1d.poll ! <title>\x1d: set the title.")
            bot.reply("\x1d.poll > <option name>\x1d: append an option.")
            bot.reply("\x1d.poll < <option index>\x1d: remove an option. Note "
                      "that an index is expected (see .poll ?), not the full "
                      "name of an option.")
            bot.reply("\x1d.poll ?\x1d: show pending changes.")
            bot.reply("\x1d.poll = <setting> [value]\x1d: set some "
                      "optional settings. See \x1d.poll help =\x1d")
            bot.reply("\x1d.poll ~~~\x1d: commit changes.")
            bot.reply("\x1d.poll ***\x1d: abort changes.")
            return True

    if cmd in ["close", "open"]:
        poll = self.get_poll(arg)
        if not poll:
            bot.reply("Erm, no such poll.")
            return
        if not self.checkAccess(poll, trigger):
            bot.reply("Erm, no access.")
            return
        if cmd == "open":
            if (poll["status"] == 2 or
                    poll["status"] == 0 and trigger.nick in self.admins):
                self.open(arg)
                bot.reply("Poll opened!")
                return True
            else:
                bot.reply("Unfortunately, the closed poll can't be opened.")
                return
        else:
            if poll["status"] == 1:
                self.close(arg)
                bot.reply("Poll closed!")
                return True
            else:
                bot.reply("The poll is already closed.")
                return
    elif cmd == "vote":
        if len(arg.split(" ")) != 2:
            bot.reply("Something is wrong with your command. Type "
                      "\x1d.poll help\x1d for help.")
            return
        poll_name, index = arg.split(" ")
        try:
            index = int(index)
        except ValueError:
            bot.reply("Bad index. Yes, I need an index, not name!")
            return
        result = self.vote(user=trigger.nick,
                           index=index,
                           name=poll_name)
        if result is True:
            poll = self.get_poll(poll_name)
            for opt in poll["options"]:
                if opt["index"] == index:
                    name = opt["name"]
                    break
            bot.reply("You've voted for \x02#" + str(index) + "\x02: " +
                      name + "\x0f!")
            return True
        else:
            bot.reply("Uh oh, " + result + ".")
            return
    elif cmd in ["delete", "remove"]:
        poll = self.get_poll(arg)
        if not poll:
            bot.reply("Erm, no such poll.")
            return
        if not self.checkAccess(poll, trigger):
            bot.reply("Erm, no access.")
            return
        if poll["status"] == 1:
            bot.reply("Close the poll first!")
            return
        else:
            self.del_poll(arg)
            bot.reply("Poll has been deleted.")
            return True
    elif cmd == "info":
        poll = self.get_poll(arg)
        if not poll:
            bot.reply("Uh oh, no such poll.")
            return
        if poll["status"] == 0:
            status = "Poll is \x0304closed\x03."
        elif poll["status"] == 1:
            status = "Poll is \x0303open\x03."
        elif poll["status"] == 2:
            status = "Poll is \x0307not opened yet\x03."
        bot.reply("\x02Title:\x02 " + poll["title"])
        bot.reply("\x02Created by\x02 " + poll["author"] + " at " +
                  str(poll["date"]) + ". " + status)
        total = 0
        maxLen = 0
        for item in poll["options"]:
            total += len(item["votes"])
            maxLen = max(maxLen, len(format_strip.sub("", item["name"])))
        bot.reply("\x02" + str(total) + "\x02 votes total. Poll is \x02" +
                  ("anonymous"
                   if poll["anonymous"] else
                   "unanonymous") + "\x02.")
        if poll["status"] == 1 and not poll["interim"]:
            for item in poll["options"]:
                bot.reply("  \x02#" + str(item["index"]) + "\x02: " +
                          item["name"])
        else:
            for item in poll["options"]:
                vnum = len(item["votes"])
                if total == 0:
                    perc = 0.0
                else:
                    perc = round(100 * vnum / total, 1)
                bot.reply("  \x02" + str(vnum) + "\x02 votes " +
                          "{:>5}".format(perc) + "% " +
                          bar(10, perc) + " \x02#" +
                          str(item["index"]) + "\x02: " +
                          "{:<{len}}".format(item["name"] + "\x0f",
                                             len=maxLen + 1 +
                                             format_len(item["name"])) +
                          (" │ " + ", ".join(item["votes"])
                           if not poll["anonymous"] else ""))
        return True
    elif cmd == "list":
        if self.db.count() == 0:
            bot.reply("No polls.")
            return True
        polls = [x for x in self.db.find()]
        reply = []
        for i in polls:
            if i["status"] == 0:
                format_code = "\x0315"
            elif i["status"] == 1:
                format_code = "\x0303"
            elif i["status"] == 2:
                format_code = "\x0307"
            reply.append(format_code + i["name"] + "\x0f")
        bot.reply("Polls: " + ", ".join(reply))
        return True
    elif cmd == "unvote":
        poll = self.get_poll(arg)
        if not poll:
            bot.reply("Erm, no such poll.")
            return
        for option in poll["options"]:
            if trigger.nick in option["votes"]:
                index = option["index"]
                break
        else:
            bot.reply("Wait, don't you think you need to vote first?")
        result = self.del_vote(trigger.nick, index, arg)
        if result is True:
            bot.reply("All set! Your vote has been deleted.")
            return True
        else:
            bot.reply("Uh oh, " + result + ".")
            return
    elif cmd in ["delvote", "remvote"]:
        if trigger.nick not in self.admins:
            bot.reply("I'm sorry, you don't have permission to run this "
                      "command.")
            return
        if len(arg.split(" ")) != 2:
            bot.reply("Something is wrong with your command. Type "
                      "\x1d.poll help\x1d for help.")
            return
        poll_name, user = arg.split(" ")
        poll = self.get_poll(poll_name)
        if not poll:
            bot.reply("Erm, no such poll.")
            return
        for option in poll["options"]:
            if user in option["votes"]:
                index = option["index"]
                break
        else:
            bot.reply("The user hasn't even voted for any of the "
                      "options!")
            return
        result = self.del_vote(user, index, poll_name)
        if result is True:
            bot.reply("Well, their vote has been deleted.")
            return True
        else:
            bot.reply("Uh oh, " + result + ".")
            return
    else:
        bot.reply("Unknown command.")
        return