"""
pythia.py - Oraakkeli/Pythia command
Uses local data file (scraped from oraakkeli.app)
With question type matching logic
"""
import sopel
import json
import random
import os
import re

# Load answers from local data file
DATA_FILE = os.path.join(os.path.dirname(__file__), "oraakkeli_data.json")
ANSWERS = []
CATEGORIZED = {}

def categorize_answers():
    """Categorize answers by type based on their content patterns"""
    global CATEGORIZED

    CATEGORIZED = {
        'yes_no': [],      # Kyllä/Ei type answers
        'time': [],        # Time-related answers (milloin, koska)
        'person': [],      # Person answers (kuka, kenelle, keneltä)
        'place': [],       # Place answers (missä, mistä, mihin)
        'count': [],       # Number/count answers (montako, kuinka monta)
        'reason': [],      # Reason answers (miksi, minkä takia)
        'what': [],        # What answers (mitä, mikä)
        'how': [],         # How answers (miten, kuinka)
        'other': []        # Everything else
    }

    for answer in ANSWERS:
        a_lower = answer.lower()

        # Yes/No patterns
        if (a_lower.startswith(('kyllä', 'joo', 'jep', 'ei', 'en ', 'et ', 'ehdottomasti',
            'totta kai', 'ehkä', 'mahdollisesti', 'tuskin', 'epäilen', 'varmasti',
            'tietysti', 'luultavasti', 'todennäköisesti', 'ei ikinä', 'ei koskaan')) or
            a_lower in ['kyllä', 'joo', 'jep', 'ei', 'kyllä.', 'ei.', 'joo!', 'ei!'] or
            re.match(r'^(kyllä|joo|ei|en)\b', a_lower) or
            '*punastus*' in a_lower or '*nyökkä' in a_lower):
            CATEGORIZED['yes_no'].append(answer)

        # Time patterns (contains time units or time expressions)
        elif (re.search(r'\d+\s*(min|sek|tunti|päivä|viikko|kk|kuukautta|vuotta|vko)', a_lower) or
              a_lower.startswith(('aamulla', 'illalla', 'yöllä', 'huomenna', 'ensi', 'viime')) or
              'aamuun asti' in a_lower or 'ikuisesti' in a_lower or 'pian' in a_lower):
            CATEGORIZED['time'].append(answer)

        # Person patterns (ends with -lle, -lta, -sta for people, or contains titles)
        elif (re.search(r'\b(äidille|isälle|veljelle|siskolle|kaverille|ystävälle|rakastajalle|puolisollesi|kihlatullesi|aviopuolisollesi)\b', a_lower) or
              answer.endswith(('llesi.', 'llesi', 'lleen.', 'lleen', 'ttarelle.', 'ttarelle')) or
              re.search(r'^[A-ZÄÖÅ][a-zäöå]+\.$', answer) or  # Single capitalized name
              a_lower.startswith(('sinun ', 'hänen ', 'minun '))):
            CATEGORIZED['person'].append(answer)

        # Place patterns
        elif (re.search(r'\b(suomessa|ruotsissa|saksassa|afrikassa|euroopassa|aasiassa|amerikassa|kotona|ulkona|sisällä|täällä|siellä)\b', a_lower) or
              answer.endswith(('ssa.', 'ssä.', 'ssa', 'ssä', 'sta.', 'stä.', 'sta', 'stä', 'lle.', 'ään.')) or
              a_lower.startswith(('afrikan', 'euroopan', 'aasian'))):
            CATEGORIZED['place'].append(answer)

        # Count/number patterns
        elif re.match(r'^\d+[.,]?\d*\.?$', answer.strip()):
            CATEGORIZED['count'].append(answer)

        # Reason patterns
        elif (a_lower.startswith(('koska', 'siksi', 'sen takia', 'sen vuoksi', 'sillä')) or
              'koska' in a_lower[:30]):
            CATEGORIZED['reason'].append(answer)

        # Everything else goes to 'other' (works for 'mitä', 'mikä', 'miten' etc)
        else:
            CATEGORIZED['other'].append(answer)

def load_answers():
    global ANSWERS
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            ANSWERS = data.get('answers', [])
            categorize_answers()
    except Exception as e:
        print(f"Error loading oraakkeli data: {e}")
        ANSWERS = []

def get_question_type(question):
    """Determine question type based on Finnish question words"""
    q_lower = question.lower().strip()

    # Yes/No questions (start with verb or "-ko/-kö" suffix)
    if (re.match(r'^(onko|oliko|oletko|onhan|eikö|eiköhän|voiko|voitko|voinko|saako|saanko|pitääkö|täytyykö|kannattaako|uskotko|luuletko|tiedätkö|haluatko|rakastatko|tykkäätkö|pidätkö)', q_lower) or
        re.search(r'\b\w+(ko|kö)\b', q_lower[:30])):  # -ko/-kö suffix in first few words
        return 'yes_no'

    # Time questions
    if re.match(r'^(milloin|koska|mihin aikaan|kuinka kauan|kauanko|moneenko)', q_lower):
        return 'time'

    # Person questions
    if re.match(r'^(kuka|kenen|kenelle|keneltä|ketä|ketkä|keneen|kehen)', q_lower):
        return 'person'

    # Place questions
    if re.match(r'^(missä|mistä|mihin|minne|mistäpäin|miltä)', q_lower):
        return 'place'

    # Count questions
    if re.match(r'^(montako|kuinka monta|kuinka paljon|monesko|kuinka moni)', q_lower):
        return 'count'

    # Reason questions
    if re.match(r'^(miksi|minkä takia|minkä vuoksi|mistä syystä|mitä varten)', q_lower):
        return 'reason'

    # What/which questions
    if re.match(r'^(mitä|mikä|mitkä|minkä|millainen|minkälainen|kumpi)', q_lower):
        return 'what'

    # How questions
    if re.match(r'^(miten|kuinka|millä tavalla|millä tavoin)', q_lower):
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

    if not ANSWERS:
        load_answers()

    if not ANSWERS:
        bot.say(f"{trigger.nick}: Oraakkeli on hiljaa...")
        return

    # Determine question type and pick from appropriate category
    q_type = get_question_type(question)

    # Try to get answer from matching category, fall back to 'other', then all answers
    if CATEGORIZED.get(q_type):
        answer = random.choice(CATEGORIZED[q_type])
    elif CATEGORIZED.get('other'):
        answer = random.choice(CATEGORIZED['other'])
    else:
        answer = random.choice(ANSWERS)

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
