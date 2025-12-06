"""
pythia.py - Oraakkeli/Pythia command
Uses local categorized data file (scraped from oraakkeli.app)
"""
import sopel
import json
import random
import os
import re

# Load answers from categorized data file
DATA_FILE = os.path.join(os.path.dirname(__file__), "oraakkeli_categorized.json")
CATEGORIZED = {}

def load_answers():
    global CATEGORIZED
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            CATEGORIZED = data.get('categorized', {})
            print(f"Loaded oraakkeli categories: {', '.join(f'{k}={len(v)}' for k, v in CATEGORIZED.items())}")
    except Exception as e:
        print(f"Error loading oraakkeli data: {e}")
        CATEGORIZED = {}

def get_question_type(question):
    """Determine question type based on Finnish question words"""
    q_lower = question.lower().strip()

    # Yes/No questions (start with verb or "-ko/-kö" suffix)
    if (re.match(r'^(onko|oliko|oletko|onhan|eikö|eiköhän|voiko|voitko|voinko|saako|saanko|pitääkö|täytyykö|kannattaako|uskotko|luuletko|tiedätkö|haluatko|rakastatko|tykkäätkö|pidätkö|ootko|ooksä|ootsä|eiks|eks)', q_lower) or
        re.search(r'\b\w+(ko|kö|ks)\b', q_lower[:30])):  # -ko/-kö/-ks suffix in first few words
        return 'yes_no'

    # Time questions
    if re.match(r'^(milloin|koska|mihin aikaan|kuinka kauan|kauanko|moneenko|millon)', q_lower):
        return 'time'

    # Person questions
    if re.match(r'^(kuka|kenen|kenelle|keneltä|ketä|ketkä|keneen|kehen|kelle)', q_lower):
        return 'person'

    # Place questions
    if re.match(r'^(missä|mistä|mihin|minne|mistäpäin|miltä|mis)', q_lower):
        return 'place'

    # Count questions
    if re.match(r'^(montako|kuinka monta|kuinka paljon|monesko|kuinka moni|paljonko|monta)', q_lower):
        return 'count'

    # Reason questions
    if re.match(r'^(miksi|minkä takia|minkä vuoksi|mistä syystä|mitä varten|miks)', q_lower):
        return 'reason'

    # What/which questions
    if re.match(r'^(mitä|mikä|mitkä|minkä|millainen|minkälainen|kumpi|mitäs)', q_lower):
        return 'what'

    # How questions
    if re.match(r'^(miten|kuinka|millä tavalla|millä tavoin|mites)', q_lower):
        return 'how'

    return 'other'

# Load on module import
load_answers()

@sopel.module.commands('pythia', 'oraakkeli')
def pythia_command(bot, trigger):
    """Ask the oracle a question: !pythia <question>"""
    if not trigger.group(2):
        bot.say(f"{trigger.nick}: Kysy jotain, esim: !pythia mitä tulevaisuus tuo tullessaan?")
        return

    question = trigger.group(2).strip()

    if not CATEGORIZED:
        load_answers()

    if not CATEGORIZED:
        bot.say(f"{trigger.nick}: Oraakkeli on hiljaa...")
        return

    # Determine question type and pick from appropriate category
    q_type = get_question_type(question)

    # Try to get answer from matching category, fall back to 'other', then any category
    if CATEGORIZED.get(q_type):
        answer = random.choice(CATEGORIZED[q_type])
    elif CATEGORIZED.get('other'):
        answer = random.choice(CATEGORIZED['other'])
    else:
        # Pick from any category
        all_answers = [a for answers in CATEGORIZED.values() for a in answers]
        answer = random.choice(all_answers) if all_answers else "En tiedä."

    bot.say(f"{trigger.nick}: {answer}")

# Old external API version (commented out):
# import requests
#
# @sopel.module.commands('pythia', 'oraakkeli')
# def pythia_command(bot, trigger):
#     """Ask the oracle a question: !pythia <question>"""
#     if not trigger.group(2):
#         bot.say(f"{trigger.nick}: Kysy jotain, esim: !pythia mitä tulevaisuus tuo tullessaan?")
#         return
#
#     question = trigger.group(2).strip()
#     rnd = random.randint(10000000, 99999999)
#
#     try:
#         response = requests.get(
#             "https://oraakkeli.app/",
#             params={
#                 f"kysymys_{rnd}": question,
#                 "submit": "",
#                 "rnd": rnd
#             },
#             timeout=10
#         )
#
#         if response.status_code == 200:
#             match = re.search(r"<p class='vastaus'>([^<]+)</p>", response.text)
#             if match:
#                 answer = match.group(1).strip()
#                 bot.say(f"{trigger.nick}: {answer}")
#             else:
#                 bot.say(f"{trigger.nick}: Oraakkeli on hiljaa...")
#         else:
#             bot.say(f"{trigger.nick}: Oraakkeli ei vastaa (virhe {response.status_code})")
#
#     except Exception as e:
#         bot.say(f"{trigger.nick}: Oraakkeli on rikki: {e}")
