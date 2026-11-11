"""Tells the owner about new Pulina account applications in a private message.

Polls chat.pulina.fi for applications nobody has been told about yet. The key that
lets it ask lives in .env as PULINA_ACCOUNTS_KEY; without it the module stays quiet.
"""

import os

import requests
import sopel.module
from dotenv import load_dotenv
from sopel.tools import get_logger

LOGGER = get_logger(__name__)
load_dotenv('/home/rolle/.sopel/.env')

API = 'https://chat.pulina.fi/accounts'
KEY = os.getenv('PULINA_ACCOUNTS_KEY')
POLL_SECONDS = 60
TIMEOUT = 15
CLIENT_NAME = 'kummitus-ircbot/1.0 (+https://github.com/pulinairc/kummitus)'


@sopel.module.interval(POLL_SECONDS)
def tell_new_applications(bot):
    if not KEY:
        return
    headers = {'X-Key': KEY, 'User-Agent': CLIENT_NAME}
    try:
        pending = requests.get(f'{API}/pending', headers=headers, timeout=TIMEOUT).json()
    except Exception as e:
        LOGGER.error('[ACCOUNTS] Fetching applications failed: %s' % e)
        return
    owner = bot.config.core.owner
    for app in pending:
        known = app.get('known') or '–'
        bot.say('Uusi tunnushakemus: %s. Kanavalla tunnetaan nimellä: %s. %s'
                % (app['account'], known, app['link']), owner)
        try:
            requests.post(f'{API}/notified', json={'account': app['account']}, headers=headers, timeout=TIMEOUT)
        except Exception as e:
            LOGGER.error('[ACCOUNTS] Marking %s told failed: %s' % (app['account'], e))
