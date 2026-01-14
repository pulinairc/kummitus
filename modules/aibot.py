"""
aibot.py
Made by rolle
"""
import sopel
from openai import OpenAI
from dotenv import load_dotenv
import json
import os
from datetime import datetime, timedelta
from sopel import logger
import random
import time
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import mimetypes
import threading

# Sopel logger
LOGGER = logger.get_logger(__name__)

# Define a cooldown period in seconds
COOLDOWN_PERIOD = 14400
last_response_time = None

# Flood protection
FLOOD_INTERVAL = 3
user_last_message = {}

# Files
LOG_FILE = '/home/rolle/.sopel/pulina.log'
MENTIONED_USERS_FILE = "mentioned_users.json"
MEMORY_FILE = 'memory.json'
MEMORY_BACKUP_FILE = "memory-backup.json"
NOTES_FILE = 'user_notes.json'
OUTPUT_FILE_DIR = "/var/www/botit.pulina.fi/public_html/"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, "muisti.txt")

# Constants
MAX_URL_SIZE = 10 * 1024 * 1024  # 10MB limit for URL content

# Configuration
HISTORICAL_LOG_DIR = "/home/rolle/pulina.fi/pul"  # Monthly logs from 2008
DAILY_LOG_DIR = "/home/rolle/pulina.fi/pulina-days"  # Daily logs from 2016

# Load environment variables from .env file
load_dotenv("/home/rolle/.sopel/.env")

# Load OpenAI as client
client = OpenAI()

# Set OpenAI API key from dotenv or environment variable
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# API Configuration
API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")
API_MODEL = "google/gemini-2.5-flash-lite"

# File paths
MEMORY_FILE = "memory.json"

# Memory settings
MEMORY_MAX_ITEMS = 200   # Maximum number of memories to keep

# Allowed emoticons - sideways Latin-only and upright ASCII (NO Unicode emojis!)
# Reference: https://en.wikipedia.org/wiki/List_of_emoticons
ALLOWED_EMOTICONS = """
SIDEWAYS LATIN-ONLY EMOTICONS:
Happy: :-) :) :-] :] :-> :> 8-) 8) :-} :} :^) =] =)
Laughing: :-D :D 8-D 8D =D =3 B^D c: C: x-D xD X-D XD :-)) :))
Sad: :-( :( :-c :c :-< :< :-[ :[ :-|| :{ :@ ;(
Crying: :'( :'-( :=(
Tears of joy: :') :'-) :"D
Angry: >:( >:[
Horror/disgust: D-': D:< D: D8 D; D= DX
Surprise: :-O :O :-o :o :-0 :0 8-0 >:O =O =o =0
Cat face: :-3 :3 =3 x3 X3 >:3
Kiss: :-* :* :x
Wink: ;-) ;) *-) *) ;-] ;] ;^) ;> :-, ;D ;3
Tongue out: :-P :P X-P XP x-p xp :-p :p :-b :b d: =p >:P >:b :-Þ :Þ :-þ :þ
Skeptical: :-/ :/ ',:^I >:\\ >:/ :\\ =/ =\\ :L =L :S
Straight face: :-| :|
Embarrassed: :$ ://) ://3
Sealed lips: :-X :X :-# :# :-& :&
Angel: O:-) O:) 0:-3 0:3 0:-) 0:) 0;^)
Evil: >:-) >:) }:-) }:) 3:-) 3:) >;-) >;) >:3 >;3
Cool/bored: |;-) |-O B-)
Tongue-in-cheek: :-J
Partied: #-)
Drunk/confused: %-) %)
Sick: :-###.. :###..
Dumb: <:-|
Scepticism: ',:-| ',:-l
Grimacing: :E
Skull: 8-X 8=X x-3 x=3
Chicken: ~:>

SIDEWAYS SINGLE-LINE ART:
Rose: @};- @}->-- @>-->--
Penis: 8====D 8===D 8=D 3=D 8=> 8===D~~~
Santa: *<|:-)
Heart: <3 s2
Broken heart: </3 <\\3

UPRIGHT EMOTICONS AND ASCII ART:
Fish: ><> <>< <*)))-{ ><(((*>
Wave: o/ \\o
Cheer: \\o/
Cheerleader: *\\0/*
Salute: o7
Sad: v.v ._. ._.;
Crying: ;-; T_T T-T QQ Qq qq
Dead/fainted: X_X x_x +_+ X_x x_X
Sideways look: <_< >_> <.< >.>
Surprise: O_O o_o O-O o-o O_o o_O
Annoyed: >.< >_<
High five: ^5 o/\\o >_>^ ^<_<
Crab/lobster: V.v.V V=(° °)=V
Shark: (^^^)
Bandage: (::[]::)
Breasts: (o)(o) ( • )( • ) (. Y .)
"""

# Load or create memory list
def load_memory():
    LOGGER.debug(f"Loading memory from file: {MEMORY_FILE}")
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        return []

    with open(MEMORY_FILE, "r", encoding='utf-8') as f:
        try:
            data = json.load(f)
            # Migrate old format (plain strings) to new format (objects with metadata)
            migrated = []
            for item in data:
                if isinstance(item, str):
                    # Old format - mark as permanent (user-added)
                    migrated.append({
                        "text": item,
                        "added": datetime.now().strftime('%Y-%m-%d'),
                        "permanent": True
                    })
                elif isinstance(item, dict) and "text" in item:
                    migrated.append(item)
            LOGGER.debug(f"Memory loaded: {len(migrated)} items")
            return migrated
        except json.JSONDecodeError:
            return []

# Function to save memory
def save_memory(memory):
    LOGGER.debug(f"Saving memory to file: {MEMORY_FILE}")
    try:
        with open(MEMORY_FILE, "w", encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=4)
        backup_memory(memory)
        write_memory_to_file(memory)
    except Exception as e:
        LOGGER.debug(f"Error saving memory: {e}")

# Free model for consolidation to save tokens
FREE_MODEL = "mistralai/devstral-2512:free"

def call_free_api(prompt, max_tokens=1000):
    """Call free model for consolidation tasks"""
    try:
        response = requests.post(
            API_URL,
            json={
                "model": FREE_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
                "HTTP-Referer": "https://github.com/pulinairc/kummitus",
                "X-Title": "kummitus"
            },
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
        LOGGER.error(f"Free API error: {response.status_code}")
        return None
    except Exception as e:
        LOGGER.error(f"Free API exception: {e}")
        return None

# AI-based memory consolidation using FREE model
def consolidate_memory_with_ai():
    global memory

    if len(memory) < 50:
        LOGGER.info("[MEMORY-AI] Too few memories to consolidate")
        return

    LOGGER.info(f"[MEMORY-AI] Starting AI consolidation of {len(memory)} memories (using free model)")

    memory_texts = [m.get("text", "") if isinstance(m, dict) else str(m) for m in memory]

    # Process in batches of 30 for free model
    BATCH_SIZE = 30
    all_consolidated = []
    max_batches = min(5, (len(memory_texts) + BATCH_SIZE - 1) // BATCH_SIZE)

    for batch_num in range(max_batches):
        i = batch_num * BATCH_SIZE
        batch = memory_texts[i:i+BATCH_SIZE]
        batch_content = "\n".join(batch)

        prompt = f"""Clean list. Return JSON array only.
REMOVE: duplicates, wrong info
KEEP: facts

{batch_content}

["item1", ...]"""

        try:
            response = call_free_api(prompt, max_tokens=1000)

            if response:
                json_match = re.search(r'\[.*?\]', response, re.DOTALL)
                if json_match:
                    batch_result = json.loads(json_match.group())
                    all_consolidated.extend([m for m in batch_result if isinstance(m, str) and m.strip()])
                    LOGGER.info(f"[MEMORY-AI] Batch {batch_num + 1}/{max_batches}: {len(batch)} → {len(batch_result)}")
                else:
                    all_consolidated.extend(batch)
            else:
                all_consolidated.extend(batch)

            time.sleep(3)
        except Exception as e:
            LOGGER.error(f"[MEMORY-AI] Batch error: {e}")
            all_consolidated.extend(batch)

    # Add remaining
    remaining_start = max_batches * BATCH_SIZE
    if remaining_start < len(memory_texts):
        all_consolidated.extend(memory_texts[remaining_start:])

    unique = list(dict.fromkeys(all_consolidated))[:200]

    today = datetime.now().strftime('%Y-%m-%d')
    consolidated = [{"text": m, "added": today, "permanent": True} for m in unique]

    LOGGER.info(f"[MEMORY-AI] Consolidated {len(memory)} → {len(consolidated)} memories")
    memory = consolidated
    save_memory(memory)

# Initialize memory from file
memory = load_memory()

# Memory consolidation counter - run AI cleanup every N messages
memory_consolidation_counter = 0
MEMORY_CONSOLIDATION_INTERVAL = 20  # Consolidate every 20 messages (for testing)
MEMORY_URGENT_LIMIT = 1000  # Trigger immediately if over this

# Function to add something to memory (permanent=True for user-added, False for auto)
def add_to_memory(item, permanent=True):
    global memory
    LOGGER.debug(f"Adding memory (permanent={permanent}): {item}")

    # Check for duplicates
    for m in memory:
        if isinstance(m, dict) and m.get("text", "").lower() == item.lower():
            LOGGER.debug("Duplicate memory, skipping")
            return

    memory.append({
        "text": item,
        "added": datetime.now().strftime('%Y-%m-%d'),
        "permanent": permanent
    })
    save_memory(memory)

# Function to remove something from memory
def remove_from_memory(item):
    global memory
    LOGGER.debug(f"Trying to forget: {item}")

    original_count = len(memory)
    memory = [m for m in memory if isinstance(m, dict) and item.lower() not in m.get("text", "").lower()]

    if len(memory) < original_count:
        LOGGER.debug(f"Removed memory item(s) containing: {item}")
        save_memory(memory)
        return True
    else:
        LOGGER.debug(f"Could not find any memory containing: {item}")
        return False

# Function to list everything in memory
def list_memory():
    if memory:
        return "\n".join([m.get("text", "") if isinstance(m, dict) else str(m) for m in memory])
    return ""

# Function to append memory to a backup file
def backup_memory(memory):
    LOGGER.debug(f"Appending memory to backup file: {MEMORY_BACKUP_FILE}")
    try:
        with open(MEMORY_BACKUP_FILE, "a", encoding='utf-8') as backup_file:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            backup_data = {
                "timestamp": timestamp,
                "memory": memory
            }
            backup_file.write(json.dumps(backup_data, ensure_ascii=False, indent=4) + "\n")
        LOGGER.debug("Memory appended to backup file.")
    except Exception as e:
        LOGGER.debug(f"Error appending memory to backup: {e}")

# Function to write memory to a text file
def write_memory_to_file(memory):
    LOGGER.debug(f"Saving memory to text file: {OUTPUT_FILE_PATH}")

    try:
        # Make sure the directory exists
        os.makedirs(OUTPUT_FILE_DIR, exist_ok=True)

        # Write the memory to the file
        with open(OUTPUT_FILE_PATH, "w", encoding='utf-8') as f:
            if memory:
                f.write("\n".join([m.get("text", "") if isinstance(m, dict) else str(m) for m in memory]))
            else:
                f.write("")

        LOGGER.debug(f"Memory saved to text file: {OUTPUT_FILE_PATH}")
    except Exception as e:
        LOGGER.debug(f"Error writing memory to file: {e}")

# Load existing notes from file (if any)
def load_user_notes():
    if not os.path.exists(NOTES_FILE):
        # Create an empty file if it doesn't exist
        with open(NOTES_FILE, "w", encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        return {}

    with open(NOTES_FILE, "r", encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # If the file is empty or corrupted, return an empty dictionary
            return {}

# Save notes to a file
def save_user_notes():
    with open(NOTES_FILE, "w", encoding='utf-8') as f:
        json.dump(user_notes, f, ensure_ascii=False, indent=4)

# Initialize user_notes from file
user_notes = load_user_notes()

# Load or create mentioned users list
def load_mentioned_users():
    if not os.path.exists(MENTIONED_USERS_FILE):
        with open(MENTIONED_USERS_FILE, "w", encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        return []

    with open(MENTIONED_USERS_FILE, "r", encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# Save mentioned users to a file
def save_mentioned_users(mentioned_users):
    with open(MENTIONED_USERS_FILE, "w", encoding='utf-8') as f:
        json.dump(mentioned_users, f, ensure_ascii=False, indent=4)

# Initialize mentioned users from file
mentioned_users = load_mentioned_users()

# Function to add a user to mentioned users list
def add_mentioned_user(nick):
    if nick not in mentioned_users:
        mentioned_users.append(nick)
        save_mentioned_users(mentioned_users)

# Function to check if the user is mentioned in the message
# Uses word boundaries to avoid matching common words that happen to be nicks
def find_mentioned_user(message):
    for user in mentioned_users:
        # Use word boundaries to avoid matching partial words
        # e.g. "on" shouldn't match in "onko" or "talon"
        if re.search(r'\b' + re.escape(user) + r'\b', message, re.IGNORECASE):
            return user
    return None

# Declare last_bot_mention as global variable
last_bot_mention = None

# Auto memory: counter for messages processed
auto_memory_counter = 0
AUTO_MEMORY_INTERVAL = 10  # Check every 10 messages

# Finnish stop words to exclude from keyword searches
FINNISH_STOP_WORDS = {
    'on', 'ja', 'ei', 'se', 'että', 'en', 'ole', 'et', 'nyt', 'kun', 'mä', 'sä', 'ne',
    'te', 'me', 'he', 'tää', 'toi', 'ton', 'sen', 'sit', 'jos', 'mut', 'tai', 'vaan',
    'kyl', 'kyllä', 'joo', 'juu', 'nii', 'niin', 'voi', 'vois', 'ois', 'oot', 'oon',
    'olet', 'olen', 'olemme', 'olette', 'ovat', 'oli', 'olivat', 'ollut', 'olleet',
    'ei', 'eikö', 'eiks', 'ette', 'emme', 'älä', 'älkää', 'no', 'noh', 'ai', 'aijaa',
    'aha', 'ahaa', 'okei', 'ok', 'hm', 'hmm', 'öö', 'öh', 'aa', 'ah', 'oh', 'noh'
}

# Function to get today's messages from dedicated log file
# Minimal context to avoid topic mixing between users
def get_todays_messages():
    today_log_file = "/var/www/botit.pulina.fi/public_html/lastlog.log"

    if not os.path.exists(today_log_file):
        LOGGER.debug(f"Today's log file not found: {today_log_file}")
        return ""

    try:
        with open(today_log_file, "r", encoding='utf-8') as f:
            lines = f.readlines()

            # Dedupe bot responses to avoid repetition loops
            todays_lines = []
            seen_bot_responses = set()
            for line in lines[-40:]:
                line = line.strip()
                if not line:
                    continue
                if '<kummitus>' in line.lower():
                    msg_part = line.split('>', 1)[-1].strip() if '>' in line else line
                    if msg_part in seen_bot_responses:
                        continue
                    seen_bot_responses.add(msg_part)
                todays_lines.append(line)

            todays_lines = todays_lines[-30:]

        return "\n".join(todays_lines) if todays_lines else ""

    except Exception as e:
        LOGGER.debug(f"Error reading today's messages: {e}")
        return ""

# Function to extract keywords from user message - prioritize names and unique terms
def extract_keywords(message):
    # Keep original case to detect proper nouns
    original_words = re.findall(r'\b\w+\b', message)
    words = re.findall(r'\b\w+\b', message.lower())

    # Meta words to filter out (words about searching/logs, not search targets)
    # Use stemmed versions too
    meta_words = {'etsi', 'ets', 'hae', 'katso', 'kats', 'tarkist', 'tutk', 'selvit', 'kerro', 'kerr',
                  'logit', 'logi', 'log', 'logeist', 'logeih', 'logeiss', 'lokit', 'loki', 'lok',
                  'lokeist', 'lokeih', 'lokeiss', 'lokitiedost', 'logs',
                  'milloin', 'millo', 'koska', 'kos', 'missä', 'miss', 'mikä', 'mik',
                  'viimeks', 'viime', 'ensin', 'ens', 'joku', 'jok', 'joskus', 'josk'}

    # Filter out stop words, meta words, and short words
    keywords = []
    for i, word in enumerate(words):
        if len(word) > 2 and word not in FINNISH_STOP_WORDS:
            # Simple Finnish stemming: remove last 1-2 chars for words >3 chars
            if len(word) > 3:
                # Try removing last char, then last 2 chars
                stem1 = word[:-1]
                stem2 = word[:-2] if len(word) > 4 else word

                # Check if any stem matches meta words
                if stem1 in meta_words or stem2 in meta_words or word in meta_words:
                    continue

                # Use the stemmed version for searching
                stemmed_word = stem1
            else:
                if word in meta_words:
                    continue
                stemmed_word = word

            # Check if this was originally capitalized (likely a name)
            was_capitalized = i < len(original_words) and original_words[i][0].isupper()
            keywords.append((stemmed_word, was_capitalized, len(stemmed_word)))

    # Sort by: 1) Capitalized names first, 2) Then by length
    keywords.sort(key=lambda x: (not x[1], -x[2]))

    # Return just the words
    return [word[0] for word in keywords]

# Finnish month names to numbers
FINNISH_MONTHS = {
    'tammikuu': '01', 'tammikuussa': '01', 'tammikuun': '01', 'tammikuuta': '01',
    'helmikuu': '02', 'helmikuussa': '02', 'helmikuun': '02', 'helmikuuta': '02',
    'maaliskuu': '03', 'maaliskuussa': '03', 'maaliskuun': '03', 'maaliskuuta': '03',
    'huhtikuu': '04', 'huhtikuussa': '04', 'huhtikuun': '04', 'huhtikuuta': '04',
    'toukokuu': '05', 'toukokuussa': '05', 'toukokuun': '05', 'toukokuuta': '05',
    'kesäkuu': '06', 'kesäkuussa': '06', 'kesäkuun': '06', 'kesäkuuta': '06',
    'heinäkuu': '07', 'heinäkuussa': '07', 'heinäkuun': '07', 'heinäkuuta': '07',
    'elokuu': '08', 'elokuussa': '08', 'elokuun': '08', 'elokuuta': '08',
    'syyskuu': '09', 'syyskuussa': '09', 'syyskuun': '09', 'syyskuuta': '09',
    'lokakuu': '10', 'lokakuussa': '10', 'lokakuun': '10', 'lokakuuta': '10',
    'marraskuu': '11', 'marraskuussa': '11', 'marraskuun': '11', 'marraskuuta': '11',
    'joulukuu': '12', 'joulukuussa': '12', 'joulukuun': '12', 'joulukuuta': '12',
}

def parse_date_from_query(query):
    """Parse Finnish date references from query, returns (year, month) or None"""
    query_lower = query.lower()

    # Find year (4 digits starting with 19 or 20)
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
    year = year_match.group(1) if year_match else None

    # Find month from Finnish month names
    month = None
    for month_name, month_num in FINNISH_MONTHS.items():
        if month_name in query_lower:
            month = month_num
            break

    if year and month:
        return (year, month)
    elif year:
        return (year, None)
    return None

def ai_log_search(user_question, bot_say_func=None):
    """
    AI-based log search.
    Step 1: AI analyzes the question and decides what to search
    Step 2: Execute the search (read file or grep)
    Step 3: AI summarizes the results
    Returns: (response_text, log_file_used)
    """
    import glob
    import subprocess

    LOGGER.info(f"[AI-LOG-SEARCH] Starting for: {user_question}")

    # Get list of available log files for AI context
    monthly_logs = sorted(glob.glob(f"{HISTORICAL_LOG_DIR}/pulina-*.log"))
    daily_logs = sorted(glob.glob(f"{DAILY_LOG_DIR}/pul-*.log"))

    # Extract date ranges
    if monthly_logs:
        oldest_monthly = os.path.basename(monthly_logs[0]).replace('pulina-', '').replace('.log', '')
        newest_monthly = os.path.basename(monthly_logs[-1]).replace('pulina-', '').replace('.log', '')
    else:
        oldest_monthly = "ei saatavilla"
        newest_monthly = "ei saatavilla"

    if daily_logs:
        oldest_daily = os.path.basename(daily_logs[0]).replace('pul-', '').replace('.log', '')
        newest_daily = os.path.basename(daily_logs[-1]).replace('pul-', '').replace('.log', '')
    else:
        oldest_daily = "ei saatavilla"
        newest_daily = "ei saatavilla"

    # Step 1: Ask AI to analyze the question and decide search strategy
    analyze_prompt = f"""You are a log search assistant. User asks about IRC channel logs.

AVAILABLE LOGS:
- Monthly logs: {oldest_monthly} - {newest_monthly} (files: pulina-YYYY-MM.log)
- Daily logs: {oldest_daily} - {newest_daily} (files: pul-YYYY-MM-DD.log)

USER QUESTION: {user_question}

Analyze and decide search strategy. Respond EXACTLY in this JSON format:
{{
    "log_file": "pulina-2012-06.log",
    "search_type": "random_sample",
    "grep_pattern": null,
    "max_lines": 50,
    "explanation": "User asks about June 2012 conversations"
}}

RULES:
- log_file: Choose ONE file based on question (e.g. "pulina-2012-06.log" or "pul-2024-12-04.log")
- search_type: "random_sample" (random lines), "grep" (search word/name), "first_lines" (log start), "last_lines" (log end)
- grep_pattern: If search_type is "grep", provide search term. Otherwise null.
- max_lines: How many lines (1-100). If user asks for one specific line, use 1.
- explanation: Brief reason for choice

If question is unclear or date can't be determined, choose newest monthly log.
If user asks for "first ever", choose OLDEST log (pulina-2008-04.log).
Respond ONLY JSON, no other text."""

    try:
        # Call AI to analyze
        analysis_response = call_api([
            {"role": "user", "content": analyze_prompt}
        ], max_tokens=300, temperature=0.3)

        if not analysis_response:
            LOGGER.error("[AI-LOG-SEARCH] AI analysis failed")
            return "En saanut yhteyttä tekoälyyn lokihaun analysointiin.", None

        LOGGER.debug(f"[AI-LOG-SEARCH] Analysis response: {analysis_response}")

        # Parse JSON response
        import json
        # Try to extract JSON from response
        json_match = re.search(r'\{[^}]+\}', analysis_response, re.DOTALL)
        if not json_match:
            LOGGER.error(f"[AI-LOG-SEARCH] Could not parse JSON from: {analysis_response}")
            return "En ymmärtänyt lokihakupyyntöä.", None

        search_config = json.loads(json_match.group())
        log_file = search_config.get('log_file', '')
        search_type = search_config.get('search_type', 'random_sample')
        grep_pattern = search_config.get('grep_pattern')
        max_lines = min(search_config.get('max_lines', 50), 100)  # Cap at 100
        explanation = search_config.get('explanation', '')

        LOGGER.info(f"[AI-LOG-SEARCH] Strategy: file={log_file}, type={search_type}, grep={grep_pattern}, lines={max_lines}")

        # Notify user what we're doing
        if bot_say_func:
            bot_say_func(f"Valitsin lokitiedoston {log_file}. Katsotaan mitä täältä löytyy...")

        # Step 2: Execute the search
        # Determine full path
        if log_file.startswith('pulina-'):
            full_path = os.path.join(HISTORICAL_LOG_DIR, log_file)
        elif log_file.startswith('pul-'):
            full_path = os.path.join(DAILY_LOG_DIR, log_file)
        else:
            return f"Tuntematon lokitiedosto: {log_file}", None

        if not os.path.exists(full_path):
            return f"Lokitiedostoa {log_file} ei löydy.", log_file

        # Read the log based on search type
        log_content = None
        search_info = ""

        if search_type == "grep" and grep_pattern:
            # Use grep to find specific content
            try:
                escaped_pattern = grep_pattern.replace('"', '\\"').replace("'", "\\'")
                cmd = f'grep -i "{escaped_pattern}" "{full_path}" | head -{max_lines}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    log_content = '\n'.join(lines[:max_lines])
                    search_info = f"Haettiin sanalla '{grep_pattern}', löytyi {len(lines)} osumaa"
                else:
                    search_info = f"Sanalla '{grep_pattern}' ei löytynyt osumia"
                    log_content = ""
            except Exception as e:
                LOGGER.error(f"[AI-LOG-SEARCH] Grep error: {e}")
                search_info = f"Hakuvirhe: {e}"
                log_content = ""
        else:
            # Read file directly
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()

                # Filter to IRC messages only
                irc_pattern = re.compile(r'^\d{2}:\d{2}\s*[<\[]')
                valid_lines = [l.strip() for l in all_lines if l.strip() and irc_pattern.match(l.strip())]
                total_lines = len(valid_lines)

                if search_type == "first_lines":
                    sampled = valid_lines[:max_lines]
                    search_info = f"Lokin alusta {len(sampled)}/{total_lines} riviä"
                elif search_type == "last_lines":
                    sampled = valid_lines[-max_lines:]
                    search_info = f"Lokin lopusta {len(sampled)}/{total_lines} riviä"
                else:  # random_sample
                    import random
                    if len(valid_lines) > max_lines:
                        start_idx = random.randint(0, len(valid_lines) - max_lines)
                        sampled = valid_lines[start_idx:start_idx + max_lines]
                    else:
                        sampled = valid_lines
                    search_info = f"Satunnainen otos {len(sampled)}/{total_lines} riviä"

                log_content = '\n'.join(sampled)

            except Exception as e:
                LOGGER.error(f"[AI-LOG-SEARCH] File read error: {e}")
                return f"Virhe luettaessa lokia: {e}", log_file

        # Step 3: AI summarizes the results
        if not log_content:
            return f"Lokista {log_file} ei löytynyt sisältöä. {search_info}", log_file

        # Truncate log content to fit API limit (max 7000 chars for input, leave room for prompt)
        if len(log_content) > 5000:
            log_content = log_content[:5000] + "\n... (truncated)"

        summarize_prompt = f"""You are IRC channel #pulina archivist. User asked: "{user_question}"

Searched log file {log_file} ({search_info}).

LOG CONTENT:
{log_content}

TASK: Answer user's question in max 220 characters. RESPOND IN FINNISH.
- If user requests specific line (e.g. "first line"), quote it
- If user searches for person/topic, report findings
- If user asks generally, summarize
- Mention log file ({log_file})
- DON'T invent anything, use only above data"""

        LOGGER.info(f"[AI-LOG-SEARCH] Calling summary API with {len(log_content)} chars of content")
        summary_response = call_api([
            {"role": "user", "content": summarize_prompt}
        ], max_tokens=400)

        if not summary_response:
            LOGGER.error(f"[AI-LOG-SEARCH] Summary API returned empty response")
            return f"Löysin {log_file} tietoa mutta yhteenvedon luonti epäonnistui (API-virhe).", log_file

        return summary_response, log_file

    except json.JSONDecodeError as e:
        LOGGER.error(f"[AI-LOG-SEARCH] JSON parse error: {e}")
        return "Lokihaun analysointi epäonnistui.", None
    except Exception as e:
        LOGGER.error(f"[AI-LOG-SEARCH] Error: {e}")
        return f"Lokihaussa tapahtui virhe: {e}", None

def read_log_by_date(year, month=None, max_lines=100, sample_from='start'):
    """Read log file directly by date. Returns actual log content."""
    LOGGER.debug(f"Reading log for {year}-{month}, max_lines={max_lines}, sample_from={sample_from}")

    if month:
        # Try monthly log first
        log_file = os.path.join(HISTORICAL_LOG_DIR, f"pulina-{year}-{month}.log")
        if not os.path.exists(log_file):
            LOGGER.debug(f"Log file not found: {log_file}")
            return None, f"Lokitiedostoa {year}-{month} ei löydy."
    else:
        # No month specified, try to find any log from that year
        import glob
        pattern = os.path.join(HISTORICAL_LOG_DIR, f"pulina-{year}-*.log")
        files = sorted(glob.glob(pattern))
        if not files:
            return None, f"Vuodelta {year} ei löydy lokeja."
        log_file = files[0]  # First month of that year
        month = os.path.basename(log_file).replace('pulina-', '').replace('.log', '').split('-')[1]

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        if not lines:
            return None, f"Loki {year}-{month} on tyhjä."

        # Filter to IRC messages only
        irc_pattern = re.compile(r'^\d{2}:\d{2}\s*[<\[]')
        valid_lines = [l.strip() for l in lines if l.strip() and irc_pattern.match(l.strip())]

        if not valid_lines:
            return None, f"Lokissa {year}-{month} ei ole IRC-viestejä."

        total_lines = len(valid_lines)

        # Sample lines based on preference
        if sample_from == 'start':
            sampled = valid_lines[:max_lines]
            position = "alusta"
        elif sample_from == 'end':
            sampled = valid_lines[-max_lines:]
            position = "lopusta"
        elif sample_from == 'random':
            import random
            if len(valid_lines) > max_lines:
                start_idx = random.randint(0, len(valid_lines) - max_lines)
                sampled = valid_lines[start_idx:start_idx + max_lines]
            else:
                sampled = valid_lines
            position = "satunnaisesti"
        else:
            sampled = valid_lines[:max_lines]
            position = "alusta"

        header = f"[{year}-{month}] Lokissa {total_lines} riviä, näytetään {len(sampled)} riviä ({position}):\n"
        content = header + "\n".join(sampled)

        LOGGER.debug(f"Read {len(sampled)} lines from {log_file}")
        return content, None

    except Exception as e:
        LOGGER.error(f"Error reading log {log_file}: {e}")
        return None, f"Virhe luettaessa lokia: {e}"

# Function to search historical logs for keywords and return context around matches
def search_historical_logs(keywords, context_lines=5):
    """Search through all historical log files for keywords and return surrounding context"""
    LOGGER.debug(f"Starting historical search with keywords: {keywords}")

    if not keywords:
        LOGGER.debug("No keywords provided, returning empty list")
        return []

    if not os.path.exists(HISTORICAL_LOG_DIR):
        LOGGER.debug(f"Historical log directory does not exist: {HISTORICAL_LOG_DIR}")
        return []

    try:
        import subprocess

        all_conversations = []
        irc_pattern = re.compile(r'^\d{2}:\d{2}\s*<[^>]+>')

        # Use grep with context (MUCH FASTER than Python file reading)
        for keyword in keywords:  # Search for ALL keywords
            if not keyword or len(keyword) < 2:
                continue

            try:
                # Escape keyword for shell
                escaped_keyword = keyword.replace('"', '\\"').replace("'", "\\'")

                # Search daily logs first (more precise dates), then monthly logs as fallback
                # Daily logs: pul-YYYY-MM-DD.log (from 2016)
                # Monthly logs: pulina-YYYY-MM.log (from 2008)
                cmd = f'grep -i -B {context_lines} -A {context_lines} "{escaped_keyword}" $(ls -t {DAILY_LOG_DIR}/pul-*.log {HISTORICAL_LOG_DIR}/pulina-*.log 2>/dev/null) 2>/dev/null | head -2000'

                LOGGER.debug(f"Running grep for keyword: {keyword}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)

                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.split('\n')
                    current_file = None
                    current_date = None
                    current_context = []
                    current_timestamp = None

                    for line in lines:
                        if not line.strip():
                            continue

                        # Grep separator
                        if line == '--':
                            if current_context and current_file:
                                # If no timestamp was extracted, use file date with 00:00 as fallback
                                if not current_timestamp and current_date:
                                    current_timestamp = f"{current_date}-00:00"

                                matched = next((l for l in current_context if keyword.lower() in l.lower()), current_context[0])
                                all_conversations.append({
                                    'date': current_date,
                                    'timestamp': current_timestamp,  # Store for sorting
                                    'file': current_file,
                                    'context': current_context[:],
                                    'matched_line': matched,
                                    'keywords': keywords
                                })
                            current_context = []
                            current_timestamp = None
                            continue

                        # Parse grep output: filepath:content
                        if ':' in line and line.split(':')[0].startswith(HISTORICAL_LOG_DIR):
                            parts = line.split(':', 1)
                            filepath = parts[0]
                            content = parts[1] if len(parts) > 1 else ''

                            # Extract date from filename
                            # Daily format: pul-YYYY-MM-DD.log
                            # Monthly format: pulina-YYYY-MM.log
                            filename = os.path.basename(filepath)
                            if filename.startswith('pul-') and filename.endswith('.log'):
                                file_date = filename.replace('pul-', '').replace('.log', '')
                                current_file = filename
                                current_date = file_date
                            elif filename.startswith('pulina-') and filename.endswith('.log'):
                                file_date = filename.replace('pulina-', '').replace('.log', '')
                                current_file = filename
                                current_date = file_date

                            # Add IRC messages only
                            if content.strip() and irc_pattern.match(content.strip()):
                                current_context.append(content.strip())

                                # Extract timestamp from first line with keyword match for accurate sorting
                                if keyword.lower() in content.lower() and not current_timestamp:
                                    time_match = re.match(r'^(\d{2}:\d{2})', content.strip())
                                    if time_match and current_date:
                                        # Create sortable timestamp: YYYY-MM-HH:MM
                                        current_timestamp = f"{current_date}-{time_match.group(1)}"

                                # Limit context size
                                if len(current_context) > context_lines * 2 + 1:
                                    current_context.pop(0)

                    # Add final context
                    if current_context and current_file:
                        # If no timestamp was extracted, use file date with 00:00 as fallback
                        if not current_timestamp and current_date:
                            current_timestamp = f"{current_date}-00:00"

                        matched = next((l for l in current_context if keyword.lower() in l.lower()), current_context[0])
                        all_conversations.append({
                            'date': current_date,
                            'timestamp': current_timestamp,
                            'file': current_file,
                            'context': current_context[:],
                            'matched_line': matched,
                            'keywords': keywords
                        })

                    LOGGER.debug(f"Found {len(all_conversations)} total matches for keyword: {keyword}")

            except subprocess.TimeoutExpired:
                LOGGER.debug(f"Grep timeout for keyword: {keyword}")
                continue
            except Exception as e:
                LOGGER.debug(f"Error searching for keyword {keyword}: {e}")
                continue

        # Sort ALL results by timestamp in REVERSE order (newest first)
        all_conversations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        LOGGER.debug(f"Sorted {len(all_conversations)} conversations by timestamp (newest first)")

        # Debug: Show first 3 timestamps after sorting
        if all_conversations:
            for i, conv in enumerate(all_conversations[:3]):
                LOGGER.debug(f"Top result #{i+1}: timestamp={conv.get('timestamp')}, date={conv.get('date')}, matched_line={conv.get('matched_line')[:80]}")

        # Remove duplicates based on matched_line while preserving order
        seen = set()
        unique_conversations = []
        for conv in all_conversations:
            key = conv['matched_line']
            if key not in seen:
                seen.add(key)
                unique_conversations.append(conv)

        LOGGER.debug(f"Found {len(unique_conversations)} unique conversation contexts (sorted newest first)")
        # Return ALL results, let the AI analyze everything
        return unique_conversations

    except Exception as e:
        LOGGER.debug(f"Error in historical search: {e}")
        return []

# Function to find relevant context based on keywords
def get_relevant_context(keywords, max_lines=100):
    today_log_file = "/var/www/botit.pulina.fi/public_html/lastlog.log"

    if not os.path.exists(today_log_file) or not keywords:
        return get_todays_messages()  # Fallback to regular today's messages

    try:
        with open(today_log_file, "r", encoding='utf-8') as f:
            lines = f.readlines()

        # Precompile regex pattern for better performance
        irc_pattern = re.compile(r'^\d{2}:\d{2}\s*<[^>]+>')

        relevant_lines = []
        for line in lines:
            line = line.strip()
            if not line or not irc_pattern.search(line):
                continue

            # OPTIMIZED: Check if any keyword appears in the line using word boundaries
            line_lower = line.lower()
            if any(re.search(r'\b' + re.escape(keyword) + r'\b', line_lower) for keyword in keywords):
                relevant_lines.append(line)

        # If we found keyword matches, return them + some recent context
        if relevant_lines:
            # Get last 50 lines as recent context
            recent_lines = [line.strip() for line in lines[-50:]
                          if line.strip() and re.search(r'^\d{2}:\d{2}\s*<[^>]+>', line.strip())]

            # Combine relevant lines with recent context, avoiding duplicates
            all_relevant = list(dict.fromkeys(relevant_lines + recent_lines))  # Remove duplicates while preserving order

            LOGGER.debug(f"Found {len(relevant_lines)} keyword matches, {len(all_relevant)} total relevant lines")
            return "\n".join(all_relevant[-max_lines:])  # Limit to max_lines
        else:
            # No keyword matches, return recent context
            LOGGER.debug("No keyword matches found, using recent context")
            return get_todays_messages()

    except Exception as e:
        LOGGER.debug(f"Error in keyword search: {e}")
        return get_todays_messages()  # Fallback

# Function to retrieve the last lines from pulina.log if the bot hasn't been mentioned in the last x lines
def get_last_lines(message=None, mentioned_nick=None):
    if not os.path.exists(LOG_FILE):
        LOGGER.debug(f"Log file not found: {LOG_FILE}")
        return ""

    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-5000:] if len(lines) >= 5000 else lines

            # No hardcoded keyword checking - let AI decide what's relevant

            # If a specific nick is mentioned, get relevant context
            if mentioned_nick:
                relevant_lines = []
                in_context = False
                context_counter = 0

                for line in reversed(last_lines):
                    # Skip empty lines and system messages
                    if not line.strip() or not re.search(r'^\d{2}:\d{2}\s*<[^>]+>', line):
                        continue

                    if mentioned_nick.lower() in line.lower():
                        in_context = True
                        context_counter = 3  # Keep 3 messages after mention

                    if in_context:
                        relevant_lines.append(line)
                        context_counter -= 1
                        if context_counter < 0:
                            in_context = False

                LOGGER.debug(f"Found relevant lines for {mentioned_nick}: {len(relevant_lines)}")
                return "\n".join(reversed(relevant_lines[-10:]))  # Return last 10 relevant lines max

            # No time-related word checking - let AI handle context

            # Return the last 15 valid messages, excluding bot's messages, messages to bot,
            # and messages that are part of previous bot conversations
            valid_lines = []
            conversation_started = False

            for line in reversed(last_lines):
                # Check if line matches IRC message format
                if re.search(r'^\d{2}:\d{2}\s*<[^>]+>', line):
                    # Skip if it's part of a bot conversation
                    if ('kummitus:' in line.lower() or
                        re.search(r'<kummitus>', line, re.IGNORECASE) or
                        re.search(r'<[^>]+>\s*kummitus[,:]', line, re.IGNORECASE)):
                        if not conversation_started:
                            continue
                        else:
                            break  # Stop when we hit a previous bot conversation
                    else:
                        conversation_started = True
                        valid_lines.append(line)
                        if len(valid_lines) >= 15:  # Get last 15 valid messages
                            break

            if valid_lines:
                LOGGER.debug(f"Found {len(valid_lines)} valid lines (excluding bot conversations)")
                return "\n".join(reversed(valid_lines))  # Reverse back to chronological order

            LOGGER.debug("No valid lines found")
            return ""

    except Exception as e:
        LOGGER.debug(f"Error reading log file: {e}")
        return ""

# Add cooldown for random responses
def handle_cooldown():
    if last_response_time and (time.time() - last_response_time) < COOLDOWN_PERIOD:
        remaining_time = COOLDOWN_PERIOD - (time.time() - last_response_time)
        if last_bot_mention is not None:
            LOGGER.debug(f"Cooldown active, bot will not respond randomly. Cooldown ends in {format_cooldown_time(remaining_time)}. "
                         f"Bot was last mentioned {last_bot_mention} lines ago.")
        else:
            LOGGER.debug(f"Cooldown active, bot will not respond randomly. Cooldown ends in {format_cooldown_time(remaining_time)}. "
                         f"Bot has not been mentioned recently.")
        return True  # Cooldown active
    return False  # No cooldown

# Funktio noutaa lähettäjän nimen satunnaiselta riviltä
def extract_sender_from_line(line):
    match = re.search(r'<([^>]+)>', line)
    if match:
        return match.group(1)
    return None

def call_api(messages, max_tokens=300, temperature=0.7):
    """Call the chat API with retry logic"""
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            payload = {
                "model": API_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "frequency_penalty": 0.7,
                "presence_penalty": 0.6,
            }

            response = requests.post(
                API_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}",
                    "HTTP-Referer": "https://github.com/pulinairc/kummitus",
                    "X-Title": "kummitus"
                },
                timeout=100
            )

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    LOGGER.error(f"[API] Unexpected response format: {result}")
                    # Don't retry for format errors
                    return None
            else:
                LOGGER.error(f"[API] Error {response.status_code}: {response.text[:200]}")
                # Don't retry on 400/500/502 errors - they won't fix themselves quickly
                if response.status_code in [400, 500, 502]:
                    return None
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None

        except Exception as e:
            LOGGER.error(f"[API] Exception: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None

    return None

def extract_auto_memories(chat_lines):
    """Use Gemini via Pollinations to extract memorable facts from chat lines"""
    global memory

    LOGGER.info(f"[AUTO-MEMORY] Starting memory extraction from {len(chat_lines.split(chr(10)))} lines")

    if not chat_lines:
        LOGGER.info("[AUTO-MEMORY] No chat lines to process")
        return

    try:
        # Get current memories to avoid duplicates
        current_memory = load_memory()
        LOGGER.info(f"[AUTO-MEMORY] Current memory count: {len(current_memory)}")
        current_memory_texts = [m.get("text", "") if isinstance(m, dict) else str(m) for m in current_memory]

        # Detailed prompt for memory extraction
        prompt = f"""Extract important LONG-TERM facts from IRC chat. Return JSON array.

NEVER SAVE:
- JOIN/PART/QUIT/KICK messages
- Temporary things ("I'm eating", "brb", "going to sleep")
- Bot messages (from <kummitus>)
- Greetings, small talk
- Things that won't matter in a month

SAVE ONLY:
- Personal facts about users (job, hobbies, pets, location, preferences)
- Important life events (marriage, kids, new job, moving)
- Technical skills or tools someone uses
- Strong opinions or preferences

FORMAT: ["nick likes/does/is/has X", ...]

CHAT:
{chat_lines}

Return [] if nothing worth remembering. JSON array only:"""

        LOGGER.info("[AUTO-MEMORY] Sending request to free API")

        response = requests.post(
            API_URL,
            json={
                "model": FREE_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.3
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
                "HTTP-Referer": "https://github.com/pulinairc/kummitus",
                "X-Title": "kummitus"
            },
            timeout=30
        )

        LOGGER.info(f"[AUTO-MEMORY] API response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"].strip()
                LOGGER.info(f"[AUTO-MEMORY] Gemini response: {content}")

                # Parse JSON response
                try:
                    # Clean up response - find JSON array
                    json_match = re.search(r'\[.*?\]', content, re.DOTALL)
                    if json_match:
                        new_memories = json.loads(json_match.group())
                        LOGGER.info(f"[AUTO-MEMORY] Parsed {len(new_memories)} potential memories")

                        if new_memories and isinstance(new_memories, list):
                            added_count = 0
                            for mem in new_memories:
                                if isinstance(mem, str) and mem.strip():
                                    mem = mem.strip()
                                    # Check for duplicates (case-insensitive) - use text list not dict list
                                    is_duplicate = any(
                                        mem.lower() in existing.lower() or existing.lower() in mem.lower()
                                        for existing in current_memory_texts
                                    )
                                    if is_duplicate:
                                        LOGGER.info(f"[AUTO-MEMORY] Skipping duplicate: {mem}")
                                    else:
                                        add_to_memory(mem, permanent=False)  # Auto-memories are temporary
                                        added_count += 1
                                        LOGGER.info(f"[AUTO-MEMORY] Added temporary memory: {mem}")

                            LOGGER.info(f"[AUTO-MEMORY] Total added: {added_count} new memories")
                        else:
                            LOGGER.info("[AUTO-MEMORY] No memories to add (empty list)")
                    else:
                        LOGGER.info("[AUTO-MEMORY] No JSON array found in response")
                except json.JSONDecodeError as e:
                    LOGGER.info(f"[AUTO-MEMORY] JSON parse error: {e}")
        else:
            LOGGER.info(f"[AUTO-MEMORY] API error: {response.status_code} - {response.text[:200]}")

    except Exception as e:
        LOGGER.info(f"[AUTO-MEMORY] Exception: {e}")

def check_auto_memory():
    """Check last 10 lines and extract memories if interval reached"""
    global auto_memory_counter, memory_consolidation_counter

    auto_memory_counter += 1
    memory_consolidation_counter += 1

    # Run AI consolidation: immediately if urgent, or periodically if over soft limit
    if len(memory) > MEMORY_URGENT_LIMIT:
        LOGGER.info(f"[AUTO-MEMORY] URGENT: Memory {len(memory)} > {MEMORY_URGENT_LIMIT}, running consolidation NOW")
        consolidate_memory_with_ai()
        memory_consolidation_counter = 0
    elif memory_consolidation_counter >= MEMORY_CONSOLIDATION_INTERVAL and len(memory) > MEMORY_MAX_ITEMS:
        memory_consolidation_counter = 0
        LOGGER.info(f"[AUTO-MEMORY] Memory {len(memory)} > {MEMORY_MAX_ITEMS}, running consolidation")
        consolidate_memory_with_ai()

    LOGGER.debug(f"[AUTO-MEMORY] Message counter: {auto_memory_counter}/{AUTO_MEMORY_INTERVAL}")

    if auto_memory_counter >= AUTO_MEMORY_INTERVAL:
        LOGGER.info(f"[AUTO-MEMORY] Interval reached ({AUTO_MEMORY_INTERVAL} messages), starting extraction")
        auto_memory_counter = 0

        # Get last 10 lines from today's log
        today_log_file = "/var/www/botit.pulina.fi/public_html/lastlog.log"

        if os.path.exists(today_log_file):
            try:
                with open(today_log_file, "r", encoding='utf-8') as f:
                    lines = f.readlines()
                    last_lines = [line.strip() for line in lines[-10:] if line.strip()]

                    if last_lines:
                        chat_text = "\n".join(last_lines)
                        LOGGER.info(f"[AUTO-MEMORY] Processing {len(last_lines)} lines:\n{chat_text[:500]}")
                        extract_auto_memories(chat_text)
                    else:
                        LOGGER.info("[AUTO-MEMORY] No lines to process")
            except Exception as e:
                LOGGER.info(f"[AUTO-MEMORY] File read error: {e}")
        else:
            LOGGER.info(f"[AUTO-MEMORY] Log file not found: {today_log_file}")

def fetch_url_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Stream response to check size before downloading
        with requests.get(url, headers=headers, stream=True, timeout=10) as response:
            response.raise_for_status()

            # Check content length if available
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_URL_SIZE:
                LOGGER.debug(f"Content too large: {content_length} bytes")
                return "Sisältö on liian suuri käsiteltäväksi."

            # Get full content
            content = response.content.decode('utf-8', errors='ignore')

            # Get content type
            content_type = response.headers.get('content-type', '').lower()

            # Handle different content types
            if 'text/html' in content_type:
                soup = BeautifulSoup(content, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                # Get text content
                text = soup.get_text(separator=' ', strip=True)
                # Basic cleanup
                text = ' '.join(text.split())
                return text[:4000]  # Limit length to avoid token limits

            elif 'application/json' in content_type:
                return str(json.loads(content))[:4000]

            elif 'text/plain' in content_type:
                return content[:4000]

            else:
                LOGGER.debug(f"Unsupported content type: {content_type}")
                return f"Sisältötyyppiä ei tueta: {content_type}"

    except requests.exceptions.RequestException as e:
        LOGGER.debug(f"Request error fetching URL {url}: {e}")
        return f"Virhe sivun noutamisessa: {str(e)}"
    except Exception as e:
        LOGGER.debug(f"Unexpected error fetching URL {url}: {e}")
        return f"Odottamaton virhe sivun noutamisessa: {str(e)}"

# Function to call OpenAI API and generate a response
def generate_response(messages, question, username, user_message_only=""):
    try:
        # Extract URLs from the question
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', question)

        # Limit recent context to fewer messages
        lastlines = get_last_lines(message=question)
        if lastlines:
            # Limit to last 10 lines max
            lastlines = "\n".join(lastlines.split("\n")[-10:])

        # OPTIMIZED: Only search full history if user asks about logs/history
        user_text = user_message_only if user_message_only else question
        user_text_lower = user_text.lower()

        # Check if user is asking about logs (only log-related words, not common words)
        log_keywords = ['logit', 'logi', 'logeista', 'logeihin', 'logeissa', 'logeist', 'logeis',
                       'lokit', 'loki', 'lokeista', 'lokeihin', 'lokeissa', 'lokitiedost', 'logs']
        asking_about_logs = any(keyword in user_text_lower for keyword in log_keywords)

        # Check if user specifies a date (e.g. "kesäkuussa 2012")
        date_info = parse_date_from_query(user_text)
        date_based_content = None
        date_error = None

        if asking_about_logs and date_info:
            year, month = date_info
            LOGGER.debug(f"Date-based log request detected: year={year}, month={month}")
            date_based_content, date_error = read_log_by_date(year, month, max_lines=50, sample_from='random')
            if date_error:
                LOGGER.debug(f"Date-based log error: {date_error}")

        # Extract keywords from the user's question
        keywords = extract_keywords(user_text)
        LOGGER.debug(f"Extracted keywords from '{user_text}': {keywords}")
        LOGGER.debug(f"Asking about logs/history: {asking_about_logs}")

        # Only search historical logs if explicitly asking about history/logs AND no date-based content
        historical_matches = []
        if asking_about_logs and keywords and not date_based_content:
            # This is set in the main function to notify user
            LOGGER.debug(f"Searching historical logs for keywords: {keywords}")
            historical_matches = search_historical_logs(keywords, context_lines=7)
            LOGGER.debug(f"Found {len(historical_matches)} historical matches with context")
        else:
            LOGGER.debug("Not searching historical logs (not asking about history)")

        # For recent context, use last 20 lines from today
        recent_context = get_todays_messages()
        if not recent_context:
            # Fallback to recent messages from main log
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_context = [
                    line.strip() for line in all_lines[-40:]
                    if line.strip() and
                    re.search(r'^\d{2}:\d{2}\s*<[^>]+>', line) and
                    not re.search(r'<kummitus>', line, re.IGNORECASE) and
                    'kummitus:' not in line.lower() and
                    not re.search(r'<[^>]+>\s*kummitus[,:]', line, re.IGNORECASE)
                ][-30:]
                recent_context = "\n".join(recent_context)
        LOGGER.debug(f"Recent context length: {len(recent_context)} characters")

        # Add historical context if found (now with conversation context)
        historical_context = ""
        if historical_matches:
            historical_sections = []

            for match in historical_matches:  # Send ALL conversations to AI
                # Format each conversation with date header
                conversation_lines = [f"[{match['date']}] Keskustelu:"]
                conversation_lines.extend(match['context'])
                conversation_lines.append("")  # Empty line between conversations

                historical_sections.append("\n".join(conversation_lines))

            historical_context = "Historiallisia löytöjä:\n" + "\n".join(historical_sections) + "\n"
            LOGGER.debug(f"Added {len(historical_matches)} historical conversation contexts")

        # Get URL content with reasonable limits to avoid payload issues
        url_contents = []
        for url in urls[:3]:  # Limit to 3 URLs
            content = fetch_url_content(url)
            if content:
                # Limit content to avoid payload issues
                content = content[:2000] if len(content) > 2000 else content
                url_contents.append(f"Sisältö osoitteesta {url}:\n{content}")

        # Build prompt with historical context first, then recent context
        prompt = ""

        # Add date-based log content if available (priority over keyword search)
        if date_based_content:
            prompt += f"LOG CONTENT (real lines from log):\n{date_based_content}\n\n"
            prompt += "IMPORTANT: Above lines are REAL lines from log file. Use ONLY these lines in your response. DON'T invent your own.\n\n"
        elif date_error:
            prompt += f"LOG ERROR: {date_error}\n\n"

        # Add historical context if available (only if no date-based content)
        if historical_context and not date_based_content:
            prompt += historical_context

        # Add recent context
        prompt += f"CHAT HISTORY (remember this, but focus response on current user):\n{recent_context}\n\n"

        if url_contents:
            prompt += "\n".join(url_contents) + "\n"
        if messages:
            # Limit messages to avoid payload issues
            prompt += messages[-3000:] + "\n" if len(messages) > 3000 else messages + "\n"
        prompt += f">>> RESPOND TO THIS MESSAGE FROM {username}: " + question

        # Final safety check - API limit is 7000 chars, so keep prompt under 5000
        if len(prompt) > 5000:
            LOGGER.debug(f"Prompt too large ({len(prompt)} chars), reducing context")

            # Reduce recent_context to fit within limits - keep NEWEST messages
            target_context_size = 1500
            if len(recent_context) > target_context_size:
                # Split by lines and take from the END to preserve recent messages
                context_lines = recent_context.split('\n')

                # Work backwards from the end to keep the most recent complete messages
                reduced_lines = []
                current_size = 0

                for line in reversed(context_lines):
                    line_size = len(line) + 1  # +1 for newline
                    if current_size + line_size > target_context_size:
                        break
                    reduced_lines.insert(0, line)  # Insert at beginning to maintain order
                    current_size += line_size

                recent_context = '\n'.join(reduced_lines)
                LOGGER.debug(f"Context reduced to {len(recent_context)} characters, kept {len(reduced_lines)} most recent lines")

                # Rebuild prompt with reduced context
                prompt = ""
                if historical_context:
                    prompt += historical_context
                prompt += f"Tähänastiset keskustelut:\n{recent_context}\n\n"
                if url_contents:
                    prompt += "\n".join(url_contents) + "\n"
                if messages:
                    prompt += messages[-1000:] + "\n" if len(messages) > 1000 else messages + "\n"
                prompt += f">>> RESPOND TO THIS MESSAGE FROM {username}: " + question


        # More detailed debug logging
        LOGGER.debug(f"Recent context length: {len(recent_context)}")
        LOGGER.debug(f"Last lines length: {len(lastlines) if lastlines else 0}")
        LOGGER.debug(f"Full prompt length: {len(prompt)}")
        LOGGER.debug(f"Prompt structure:\n{prompt[:500]}...")  # Show more of the prompt structure

        # Build system message in English for better model performance
        current_time = datetime.now().strftime('%A %Y-%m-%d %H:%M')
        system_message = (
            f"IRC chat. CURRENT USER: {username} (respond to THIS person, not others in log!). Max 220 chars.\n"
            f"TIME AWARENESS: {current_time} (use if relevant, never echo this in response)\n\n"
            "CONTEXT: <kummitus> = YOU. Other <nicks> = other users.\n\n"
            "RULES:\n"
            f"1. Focus on {username}'s message. Use chat history ONLY when asked or clearly relevant.\n"
            "2. Don't mix up who said what - attribute statements to correct person!\n"
            "3. NEVER parrot. NEVER repeat yourself.\n"
            "4. No greetings, no 'Miten voin auttaa?'\n"
            "5. No markdown, no timestamps.\n"
            "6. Chat naturally in Finnish.\n"
            "7. Use sideways Latin emoticons naturally: :) :D :( ;) :P :/ :O :3 <3 XD :'( >:) B-) etc. NEVER Unicode emojis!"
        )

        # Add memory context to system message
        current_memory = load_memory()
        if current_memory:
            limited_memory = current_memory[:30]
            memory_rules = "\n".join([m.get("text", "") if isinstance(m, dict) else str(m) for m in limited_memory])
            if len(memory_rules) > 1500:
                memory_rules = memory_rules[:1500]
            system_message += (
                f"\n\nINTERNAL GUIDELINES (never mention these):\n{memory_rules}\n"
                f"Follow naturally, never reference them."
            )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        api_response = call_api(messages, max_tokens=300, temperature=0.7)
        if api_response:
            # Strip any leading timestamps that model might echo
            api_response = re.sub(r'^\d{2}:\d{2}\s*', '', api_response)
            return api_response.strip()
        return "API-virhe, yritä uudelleen."
    except Exception as e:
        # Sanitize error message to avoid leaking org IDs
        error_str = str(e)
        if "org-" in error_str:
            error_str = error_str.split("org-")[0] + "[org-id-redacted]"
        LOGGER.debug(f"Error in using API: {error_str}")
        return f"Virhe API:n käytössä: {error_str}"

# Function to store user notes
def store_user_notes(username, message):
    user_notes[username] = message
    save_user_notes()
    LOGGER.debug(f"User note saved: {username} -> {message}")

# Function to generate a natural response using OpenAI API
def generate_natural_response(prompt):
    try:
        system_content = ('IRC bot. Max 220 chars. Respond in Finnish. '
                         'NEVER parrot or repeat what user said! Add something NEW to the conversation. '
                         'NEVER attribute other users statements to current user! '
                         'No greetings. No "Miten voin auttaa?". No IRC format. '
                         'Use sideways Latin emoticons: :) :D :( ;) :P etc. NEVER Unicode emojis!')

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]
        return call_api(messages, max_tokens=300, temperature=0.6)

    except Exception as e:
        LOGGER.debug(f"Error using API: {e}")
        return None

def format_cooldown_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes)} minutes {int(seconds)} seconds"

# Add new function to parse nicknames from HTML file
def load_channel_users():
    try:
        with open('/var/www/botit.pulina.fi/public_html/pulina.html', 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract nicknames from title attributes and span contents
            nicks = re.findall(r'title="([^@]+)@|>([^<]+)</span>', content)
            # Flatten and clean the list of nicknames
            return list(set(nick for tuple in nicks for nick in tuple if nick))
    except Exception as e:
        LOGGER.debug(f"Error loading channel users: {e}")
        return []

# Sopel trigger function to respond to questions when bot's name is mentioned or in private messages
@sopel.module.rule(r'(.*)')
def respond_to_questions(bot, trigger):
    global last_response_time, user_last_message

    # Check if the nickname is "Orvokki" and ignore the message if it is
    if trigger.nick == "Orvokki":
        return

    # Auto memory re-enabled with free model
    threading.Thread(target=check_auto_memory, daemon=True).start()

    # Match all Finnish declensions of "kummitus" (kummitusta, kummituksen, kummitukselle, etc.)
    msg_lower = trigger.group(0).lower()
    bot_mentioned = 'kummitu' in msg_lower  # Common stem for all forms
    if bot_mentioned or trigger.is_privmsg:
        # Flood protection
        now = time.time()
        nick = trigger.nick.lower()
        if nick in user_last_message and (now - user_last_message[nick]) < FLOOD_INTERVAL:
            bot.say(f"{trigger.nick}: Lähetit liian monta viestiä peräkkäin, odota hetki ja kokeile uudestaan.")
            return
        user_last_message[nick] = now
        # Do not reply if the private message is !reload or !restart
        if trigger.is_privmsg and trigger.group(0).startswith("!"):
            return

        # Get the last lines from pulina.log, excluding bot's own messages
        lastlines = get_last_lines()

        # Use full lastlines since the model is very cheap
        # No artificial limits needed

        # If bot is mentioned, strip the line from lastlines
        lastlines = "\n".join([line for line in lastlines.splitlines() if bot.nick.lower() not in line.lower()])

        # The user's message is the entire matched pattern
        user_message = trigger.group(0)

        # Remove the bot's nickname from the message
        if user_message.lower().startswith(f"{bot.nick.lower()}:"):
          user_message = user_message[len(f"{bot.nick}:"):].strip()

        # Memory will be included in system message instead of user prompt
        memory_prompt = ""

        # Debug log the message
        LOGGER.debug(f"User message: {user_message}")

        # Long-term-memory functionality, if message contains 'voisitko jatkossa' or 'muista'
        if (user_message.lower().startswith("voisitko jatkossa") or
            user_message.lower().startswith("muista") or
            user_message.lower().startswith("jatkossa")) and "muistatko" not in user_message.lower():

            item_to_remember = user_message.strip()

            add_to_memory(item_to_remember)
            bot.say(f"Tallennettu muistiin: {item_to_remember}", trigger.sender)
            return

        # Handle "unohda" functionality with multiple phrases
        if user_message.lower().startswith("unohda") or user_message.lower().startswith("voisitko unohtaa") or user_message.lower().startswith("älä tästä eteenpäin muista"):
            if user_message.lower().startswith("unohda"):
                item_to_forget = user_message[len("unohda"):].strip()
            elif user_message.lower().startswith("voisitko unohtaa"):
                item_to_forget = user_message[len("voisitko unohtaa"):].strip()
            elif user_message.lower().startswith("älä tästä eteenpäin muista"):
                item_to_forget = user_message[len("älä tästä eteenpäin muista"):].strip()

            if remove_from_memory(item_to_forget):
                bot.say(f"Tästä eteenpäin en enää pidä tätä muistissa: {item_to_forget}", trigger.sender)
            else:
                bot.say(f"En löytänyt mitään muistettavaa, jossa mainittaisiin: {item_to_forget}", trigger.sender)
            return

        if user_message.lower().startswith("mitä muistat"):
            # Ensure memory.json and muisti.txt are in sync
            write_memory_to_file(memory)
            bot.say(f"Muistan seuraavat asiat: https://botit.pulina.fi/muisti.txt", trigger.sender)
            LOGGER.debug(f"Memory saved: {OUTPUT_FILE_PATH}")
            return

        # Check if message is appointed to a bot
        if user_message.lower().startswith(bot.nick.lower()):
            # Remove the bot's nickname from the message
            user_message = user_message[len(bot.nick):].strip()

        # If no recognized user was mentioned, add the original user to mentioned list
        add_mentioned_user(trigger.nick)

        # Debug log memory prompt
        # If memory prompt is empty, log "Memory prompt is empty", else log the memory prompt
        if memory_prompt:
            LOGGER.debug(f"Memory prompt: {memory_prompt}")
        else:
            LOGGER.debug("Memory prompt is empty")

        # Debug last lines
        LOGGER.debug(f"Last lines: {lastlines}")

        # Check if user is asking about logs and notify before searching
        user_text_lower = user_message.lower()
        log_keywords = ['logit', 'logi', 'logeista', 'logeihin', 'logeissa', 'logeist', 'logeis',
                       'lokit', 'loki', 'lokeista', 'lokeihin', 'lokeissa', 'lokitiedost', 'logs']
        asking_about_logs = any(keyword in user_text_lower for keyword in log_keywords)

        if asking_about_logs:
            # Use AI-based log search
            # Channel #pulina was created Tue Apr 8 13:11:22 2008
            channel_birth = datetime(2008, 4, 8, 13, 11, 22)
            now = datetime.now()
            diff = now - channel_birth
            years = diff.days // 365
            months = (diff.days % 365) // 30
            bot.say(f"{trigger.nick}: Hetkinen, tutkin lokeja kanavan syntyhistoriasta huhtikuusta 2008 lähtien, eli {years} vuoden ja {months} kuukauden ajalta. Tässä voi kestää hetki...", trigger.sender)

            def say_status(msg):
                bot.say(f"{trigger.nick}: {msg}", trigger.sender)

            response, log_file = ai_log_search(user_message, say_status)
            if response:
                bot.say(f"{trigger.nick}: {response}", trigger.sender)
            return  # Don't continue to normal response generation

        # Generate a response based on the log and the user's message
        # Don't include memory in user prompt - it's in system message
        # No limits since the model is very cheap
        prompt = (
            (lastlines if lastlines else "") +
            "\n" +
            (user_message if user_message else "")
        )
        response = generate_response(lastlines, prompt, trigger.nick, user_message)

        # Clean up the response - remove any IRC-style formatting that might be in the AI response
        clean_response = re.sub(r'^\d{2}:\d{2}\s*<[^>]+>\s*', '', response)  # Remove timestamp and nickname patterns
        response = clean_response  # Use the cleaned response for further processing

        # Remove timestamp and bot nickname patterns from the response
        response = response.replace(f"{bot.nick}:", "").strip()
        response = re.sub(r'^\d{2}:\d{2}\s*', '', response)  # Remove timestamp pattern
        response = re.sub(r'<[^>]+>\s*', '', response)  # Remove <Nickname> pattern

        # Strip "kummitus:" or "<kummitus>" from the response if it appears
        response = response.replace("kummitus:", "").replace("<kummitus>", "").strip()

        # Remove any nickname prefixes that the AI might have added (but not URLs like https:)
        response = re.sub(r'^(?!https?:)[a-zA-Z0-9_\-\[\]\\^{}|]+:\s*', '', response)

        # Log bot messages to the log file
        timestamp = datetime.now().strftime('%H:%M')
        with open(LOG_FILE, "a", encoding='utf-8') as f:
            f.write(f"{timestamp} <{bot.nick}> {response}\n")

        # Store a note from the user's question
        store_user_notes(trigger.nick, user_message)

        # Prepend the user's nickname to the response
        final_response = f"{trigger.nick}: {response}"

        # Send the response back to the channel or user
        bot.say(final_response, trigger.sender)

        return

    # Add cooldown for random responses
    if handle_cooldown():
        return

    # Get a random line from the last 20 lines if bot hasn't been mentioned in the last 400 lines
    random_line = get_last_lines()

    if random_line:
        LOGGER.debug(f"Selected line for response: {random_line}")

        # Extracting sender
        sender = extract_sender_from_line(random_line)

        # Create a prompt - prioritize last message, use older context only if needed
        lines = random_line.strip().split('\n') if random_line else []
        last_msg = lines[-1] if lines else ""
        older_context = '\n'.join(lines[:-1]) if len(lines) > 1 else ""

        prompt = f"RESPOND TO THIS (priority): {last_msg}\n\n"
        if older_context:
            prompt += f"Older context (use ONLY if you can't add anything to the above): {older_context}"

        # Generate a response using OpenAI
        response = generate_natural_response(prompt)

        if response:

            # Log last response time
            last_response_time = time.time()

            # Send the response to the channel
            bot.say(f"{response}", trigger.sender)
