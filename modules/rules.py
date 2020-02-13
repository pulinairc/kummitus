# coding=utf-8
"""
rules.py
Made by Roni Laukkarinen
"""
import sopel.module

@sopel.module.commands('säännöt', 'saannot', 'rules', 'etiketti')
def olenaa(bot, trigger):
    bot.say('#pulina-kanavan säännöt, ole hyvä: https://www.pulina.fi/saannot')