import os
# coding=utf-8
"""
chatbot.py
by rolle
"""
import sopel.module

@sopel.module.nickname_commands(".*")

def chatbot(bot, trigger):

    from wit import Wit
    import logging

    access_token = os.getenv('WIT_TOKEN', '')
    client = Wit(access_token)

    query = trigger.group(1)
    resp = client.message(query)
    print('Yay, got Wit.ai response: ' + str(resp))
    #bot.reply(answer)