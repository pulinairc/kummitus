#encoding: utf-8

import sopel
from random import choice
import datetime
import requests
import sys
import json
import re

@sopel.module.commands('lewd','sfw','nsfw')
def lewd(bot,trigger):
    url = 'https://westcentralus.api.cognitive.microsoft.com/vision/v1.0/analyze'
    headers = {'Ocp-Apim-Subscription-Key': '66eae5acc8994216b5f07767540e93b0'} #requires microsoft computer vision api key
    params = {'visualFeatures':'Adult'}
    if trigger.group(2):
        data = {'url': trigger.group(2)}
        req = requests.post(url, headers=headers, params=params, json=data)
        js = req.json()
        
        if 'adult' in js:
            bot.say("[NSFW] Älä avaa töissä... lewd score: %.3f/1.00"%js['adult']['adultScore'])
        else:
            bot.say("Huh.. turvallinen linkki. lewd score: %.3f/1.00"%js['adult']['adultScore'])
