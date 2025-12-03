"""
pythia.py - Oraakkeli/Pythia command
Fetches answers from oraakkeli.app
"""
import sopel
import requests
import re
import random

@sopel.module.commands('pythia', 'oraakkeli')
def pythia_command(bot, trigger):
    """Ask the oracle a question: !pythia <question>"""
    if not trigger.group(2):
        bot.say(f"{trigger.nick}: Kysy jotain, esim: !pythia mitä tulevaisuus tuo tullessaan?")
        return

    question = trigger.group(2).strip()
    rnd = random.randint(10000000, 99999999)

    try:
        response = requests.get(
            "https://oraakkeli.app/",
            params={
                f"kysymys_{rnd}": question,
                "submit": "",
                "rnd": rnd
            },
            timeout=10
        )

        if response.status_code == 200:
            # Extract answer from <p class='vastaus'>...</p>
            match = re.search(r"<p class='vastaus'>([^<]+)</p>", response.text)
            if match:
                answer = match.group(1).strip()
                bot.say(f"{trigger.nick}: {answer}")
            else:
                bot.say(f"{trigger.nick}: Oraakkeli on hiljaa...")
        else:
            bot.say(f"{trigger.nick}: Oraakkeli ei vastaa (virhe {response.status_code})")

    except Exception as e:
        bot.say(f"{trigger.nick}: Oraakkeli on rikki: {e}")
