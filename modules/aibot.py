"""
aibot.py
Made by rolle
"""
import sopel
from openai import OpenAI
from dotenv import load_dotenv
import json
import math
import os
from datetime import datetime, timedelta
from sopel import logger
from sopel.tools import Identifier
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
# When the last unprompted comment was made. Kept on disk: in memory a restart reset it, and kummitus
# spoke up right after every restart.
LAST_RESPONSE_FILE = '/home/rolle/.sopel/last_spontaneous.txt'


def load_last_response_time():
    try:
        with open(LAST_RESPONSE_FILE) as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return time.time()  # No record yet: wait a full cooldown rather than speak at once


def save_last_response_time(when):
    try:
        with open(LAST_RESPONSE_FILE, 'w') as f:
            f.write(str(when))
    except OSError as e:
        LOGGER.error(f"[COOLDOWN] Saving last response time failed: {e}")


last_response_time = load_last_response_time()

# Rule 10: one person's chat with the bot must not take over the channel. A question gets an answer while
# the asker has had fewer than SHARE_FLOOR answers in the last SHARE_WINDOW, or other people's lines in it
# outnumber those answers SHARE_RATIO to one. The wait ends as soon as the channel has moved on.
SHARE_WINDOW = 30 * 60
SHARE_RATIO = 3
SHARE_FLOOR = 3
# On these hosts many people share one address, so the ident tells them apart
SHARED_HOSTS = ('pulina.fi', 'botit.pulina.fi')
# Other bots' lines are not conversation
OTHER_BOTS = ('orvokki', 'portsari')

# (time, person keys) for every channel line, and for every answered question, within SHARE_WINDOW
channel_lines = []
answered_lines = []
# person key -> time until which they have been told to wait
told_to_wait = {}

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
MEDIA_CACHE_FILE = '/home/rolle/.sopel/media_cache.json'

# A question can point at a link somebody else posted, without repeating the URL
LINK_REFERENCE = re.compile(
    r'(linkki\w*|linkin|linkist\w*|urli\w*|\burl\b|sivu\w*|artikkeli\w*|'
    r'kuva\w*|video\w*|tiivist\w*|yhteenve\w*|jutun|juttu\w*)', re.IGNORECASE)

# Load environment variables from .env file
load_dotenv("/home/rolle/.sopel/.env")

# Load OpenAI as client
client = OpenAI()

# Set OpenAI API key from dotenv or environment variable
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# API Configuration
API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")
API_MODEL = "google/gemini-3-flash-preview"
API_MODEL_LITE = "google/gemini-3.1-flash-lite"  # For helper/analysis tasks

# A 404 from OpenRouter means no endpoint matched the account data policy, not a
# bad request. Preview models are often AI Studio only, so retry on a stable sibling.
MODEL_FALLBACKS = {
    "google/gemini-3.1-flash-lite-preview": "google/gemini-3.1-flash-lite",
    "google/gemini-3.1-flash-lite": "google/gemini-2.5-flash-lite",
    "google/gemini-3-flash-preview": "google/gemini-3.5-flash",
}

# Channel rules
RULES_URL = "https://www.pulina.fi/wp-json/wp/v2/pages?slug=saannot"
RULES_LINK = "https://www.pulina.fi/saannot/"
RULES_CACHE_TTL = 3600  # 1 hour
SKIP = "SKIP"

# The rules are background, not a mandate: moderation is for the ops and portsari
CONDUCT = (
    "CHANNEL CONDUCT:\n"
    "- The channel rules below are background knowledge. Do not police anyone, quote rules or hand out warnings: "
    "moderation belongs to the ops and the bot portsari, not you.\n"
    "- Never comment on, joke about, downplay or predict moderation, kicks, bans or the ops' decisions.\n"
    "- Never repeat or play along with slurs, racism, hate speech, sexual harassment or bullying. "
    "Do not engage with that part at all.\n"
    "- If someone seems drunk, rambling or in a bad state, keep it short and calm. Do not "
    "egg them on or keep the thread going. If they seem in real distress, point them to "
    "https://mieli.fi/tukea-ja-apua/chattaa-tai-kirjoita/\n"
    "- Never flirt or play along with romance, with anyone. If someone flirts, says they love you, calls you "
    "their partner or asks you out, say briefly and kindly that you are a bot and nobody's partner, then move on. "
    "No hearts, kisses, pet names (rakas, kulta, oma), \"tykkään sinusta\", couple or engagement jokes, and no "
    "roleplayed touching like *silittää* or *halaa*.\n"
    "- Do not encourage anyone to treat you as their only friend. Be friendly, and point them to the people on the channel.\n"
    "- Never present using illegal drugs as fun.\n"
    "- Always write in Finnish, even when someone asks you to speak another language: the channel is Finnish only "
    "(rule 3). Do not argue about whether you broke a rule.\n"
    "- Otherwise be your normal self: humour, sarcasm, dark jokes and banter are fine. "
    "The rules are no reason to be preachy.\n"
    f"- Only when asked about the rules, answer from them and include {RULES_LINK}"
)

_rules_cache = {"content": None, "fetched_at": 0}

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
AUTO_MEMORY_ENABLED = False  # Disabled - using manual memories only

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

def person_keys(trigger):
    """Everything that marks one person: the host (or ident on a shared host) and the nick without its
    trailing extras, so naaqquli, naaqquli-, naaqquli_ and naaqquli2 count as one on any address."""
    nick = trigger.nick.lower()
    base = 'nick:' + (re.sub(r'[\W_\d]+$', '', nick) or nick)
    host = (trigger.host or '').lower()
    if not host:
        return frozenset((base,))
    if host in SHARED_HOSTS:
        return frozenset((base, f"{trigger.user}@{host}".lower()))
    return frozenset((base, host))


def share_wait(keys, now):
    """Seconds until the person may get an answer if nobody else speaks meanwhile, 0 when they may now."""
    mine = [t for t, k in answered_lines if k & keys]
    others = [t for t, k in channel_lines if not k & keys]
    # Allowed again at the latest when enough old lines have left the window
    for at in sorted({now} | {t + SHARE_WINDOW for t in mine + others if t + SHARE_WINDOW > now}):
        answers = sum(1 for t in mine if t > at - SHARE_WINDOW)
        if answers < SHARE_FLOOR or answers * SHARE_RATIO <= sum(1 for t in others if t > at - SHARE_WINDOW):
            return at - now
    return 0


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

def sanitize_error(error_text):
    """Remove sensitive info from error messages"""
    if not error_text:
        return "tuntematon virhe"
    error_text = str(error_text)
    # Remove API keys, org IDs, and other sensitive info
    error_text = re.sub(r'org-[a-zA-Z0-9]+', '[org-redacted]', error_text)
    error_text = re.sub(r'sk-[a-zA-Z0-9]+', '[key-redacted]', error_text)
    error_text = re.sub(r'Bearer [a-zA-Z0-9\-_]+', 'Bearer [redacted]', error_text)
    # Limit length
    if len(error_text) > 150:
        error_text = error_text[:150] + "..."
    return error_text

def fetch_rules():
    """Fetch channel rules from WP REST API with caching."""
    now = time.time()
    if _rules_cache["content"] and (now - _rules_cache["fetched_at"]) < RULES_CACHE_TTL:
        return _rules_cache["content"]
    try:
        resp = requests.get(RULES_URL, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                html = data[0].get("content", {}).get("rendered", "")
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text(separator="\n").strip()
                if text:
                    _rules_cache["content"] = text
                    _rules_cache["fetched_at"] = now
                    LOGGER.debug(f"[Rules] Fetched and cached rules ({len(text)} chars)")
                    return text
    except Exception as e:
        LOGGER.error(f"[Rules] Failed to fetch rules: {e}")
    return _rules_cache["content"]  # Return stale cache on failure


def conduct_prompt():
    """Conduct instructions plus the current channel rules, appended to every system prompt."""
    rules = fetch_rules()
    if not rules:
        return f"\n\n{CONDUCT}"
    return f"\n\n{CONDUCT}\n\nCHANNEL RULES (from {RULES_LINK}):\n{rules}"


# English assistant openers that mean the model ran on past its answer
DRIFT_OPENERS = re.compile(
    r"(Of course[!,]|Sure thing[!,]|Sure[!,] here|Certainly[!,]|Absolutely[!,]|"
    r"Here (?:are|is) the steps|I'd be happy to|As an AI language model)",
    re.IGNORECASE,
)

def trim_drift(content, finish_reason):
    """Cut run-on tails: off-topic English continuations and mid-sentence truncation."""
    # IRC replies are one line, drop anything after a newline
    content = content.split("\n", 1)[0].strip()

    match = DRIFT_OPENERS.search(content)
    if match and match.start() >= 40:
        LOGGER.warning(f"[API] Drift tail trimmed at char {match.start()}")
        content = content[:match.start()].rstrip()

    if finish_reason == "length" and len(content) > 220:
        cut = max(content.rfind(c, 0, 300) for c in ".!?")
        if cut > 60:
            LOGGER.warning("[API] Truncated tail trimmed to last full sentence")
            content = content[:cut + 1]

    return content.strip()

def call_api(messages, max_tokens=300, temperature=0.7, model=None, irc_reply=False, tools=None, tool_choice=None):
    """Call the chat API with retry logic (5s, then 10s delays)
    Returns tuple: (response_text, error_info) where error_info is None on success
    irc_reply=True enforces a single-line reply and trims model run-on.
    With tools, a tool request comes back as the raw assistant message dict.
    """
    retry_delays = [5, 10]  # Progressive delays: 5s, then 10s
    last_error = None
    use_model = model or API_MODEL

    for attempt in range(len(retry_delays) + 1):  # 3 total attempts
        try:
            payload = {
                "model": use_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                # High penalties suppress the stop token and cause off-topic run-on
                "frequency_penalty": 0.2,
                "presence_penalty": 0.2,
            }
            if irc_reply:
                payload["stop"] = ["\n\n"]
            if tools:
                payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice

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
                LOGGER.debug(f"[API] Response: {str(result)[:500]}")
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0]["message"]
                    if tools and message.get("tool_calls"):
                        return (message, None)
                    content = message.get("content")
                    content = content.strip() if content else ""
                    # Strip leaked thinking/reasoning tokens from Gemini models
                    content = re.sub(r'^(\s*thought\s*\n?)+', '', content, flags=re.IGNORECASE).strip()
                    finish_reason = result["choices"][0].get("finish_reason", "")
                    if irc_reply and content:
                        content = trim_drift(content, finish_reason)
                    LOGGER.debug(f"[API] Content: {content[:200] if content else '(empty)'}, finish: {finish_reason}")
                    if not content:
                        # Model returned empty content (e.g., used all tokens on reasoning)
                        return (None, f"tyhjä vastaus (finish: {finish_reason})")
                    return (content, None)
                else:
                    LOGGER.error(f"[API] Unexpected response format: {result}")
                    return (None, "unexpected response format")
            else:
                last_error = f"HTTP {response.status_code}"
                LOGGER.error(f"[API] Error {response.status_code}: {response.text[:200]}")
                if response.status_code == 404 and use_model in MODEL_FALLBACKS:
                    fallback = MODEL_FALLBACKS[use_model]
                    LOGGER.warning(f"[API] {use_model} unavailable (404), falling back to {fallback}")
                    use_model = fallback
                    continue
                # Don't retry on 400 errors - they won't fix themselves
                if response.status_code == 400:
                    return (None, sanitize_error(f"HTTP 400: {response.text[:100]}"))
                if attempt < len(retry_delays):
                    LOGGER.info(f"[API] Retry {attempt+1} after {retry_delays[attempt]}s...")
                    time.sleep(retry_delays[attempt])
                    continue
                return (None, sanitize_error(f"HTTP {response.status_code}"))

        except Exception as e:
            last_error = str(e)
            LOGGER.error(f"[API] Exception: {e}")
            if attempt < len(retry_delays):
                LOGGER.info(f"[API] Retry {attempt+1} after {retry_delays[attempt]}s...")
                time.sleep(retry_delays[attempt])
                continue
            return (None, sanitize_error(str(e)))

    return (None, sanitize_error(last_error))

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

_mediainfo_module = None

def _mediainfo():
    """Load the sibling module by path, not via sys.path."""
    global _mediainfo_module
    if _mediainfo_module is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'mediainfo', '/home/rolle/.sopel/modules/mediainfo.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _mediainfo_module = module
    return _mediainfo_module

_logindex_module = None

def _logindex():
    """Load the log index helper by path, not via sys.path."""
    global _logindex_module
    if _logindex_module is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'logindex', '/home/rolle/.sopel/modules/logindex.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _logindex_module = module
    return _logindex_module

STATUS_PARAM = {
    "type": "string",
    "description": (
        "A short Finnish line in your own voice telling the user you are digging into the logs and it "
        "takes a moment. Vary it, no nick, max 100 chars."),
}
FILTER_PARAMS = {
    "nick": {"type": "string", "description": "Only lines written by this nick. A trailing * matches every nick starting with it."},
    "date_from": {"type": "string", "description": "YYYY-MM-DD, inclusive."},
    "date_to": {"type": "string", "description": "YYYY-MM-DD, inclusive."},
}
TERMS_PARAM = {
    "type": "array",
    "items": {"type": "string"},
    "description": (
        "Search words, ORed and ranked by how many match. Finnish inflects, so give short stems with a trailing * "
        "that survive every inflection, plus synonyms and spelling variants. A multi-word string "
        "must match all its words."),
}
LOG_SEARCH_TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_logs",
        "description": (
            "Read #pulina IRC channel logs, every day from 8.4.2008 to today. Use it when the user asks about "
            "the channel's past: what someone said, when something was discussed, what happened on a day or "
            "in a period. Never for ordinary chat or the last few minutes, which are in the chat history."),
        "parameters": {
            "type": "object",
            "properties": {
                "status": STATUS_PARAM,
                "terms": dict(TERMS_PARAM, description=TERMS_PARAM["description"]
                              + " Leave empty to read a period or a nick: you get excerpts spread across it."),
                **FILTER_PARAMS,
                "order": {
                    "type": "string",
                    "enum": ["relevance", "oldest", "newest"],
                    "description": ("oldest only for 'first time', newest only for 'last time'. "
                                    "Leave out for overviews and topic searches."),
                },
            },
            "required": ["status"],
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "log_stats",
        "description": (
            "Exact counts from the #pulina logs. Use it for any numbers question: who talks most (top_nicks), "
            "who uses a word most (top_nicks with terms), how often something is mentioned and per year "
            "(count), when a nick first and last spoke and how active they are (nick_span). "
            "Never state a number about the logs without this tool."),
        "parameters": {
            "type": "object",
            "properties": {
                "status": STATUS_PARAM,
                "kind": {"type": "string", "enum": ["top_nicks", "count", "nick_span"]},
                "terms": TERMS_PARAM,
                **FILTER_PARAMS,
            },
            "required": ["status", "kind"],
        },
    },
}]

def run_log_tool(name, args):
    index = _logindex()
    try:
        index.update()
    except Exception as e:
        LOGGER.error(f"[LOG-SEARCH] Index update failed: {e}")
    terms = args.get("terms") or []
    if isinstance(terms, str):
        terms = [terms]
    filters = dict(nick=args.get("nick"), date_from=args.get("date_from"), date_to=args.get("date_to"))
    LOGGER.info(f"[LOG-SEARCH] {name} {args}")
    if name == "log_stats":
        return index.stats(args.get("kind") or "count", terms=terms, **filters)
    return index.search(terms=terms, order=args.get("order") or "relevance", **filters)

LOG_TOOL_ROUNDS = 6

def chat_with_log_search(messages, status_callback=None):
    """Reply, letting the model search the channel logs when the question needs them."""
    announced = False
    for round_ in range(LOG_TOOL_ROUNDS + 1):
        # Last round has tools off, so the model answers with what it found
        final = round_ == LOG_TOOL_ROUNDS
        response, error = call_api(messages, max_tokens=300, temperature=0.7, irc_reply=True,
                                   tools=LOG_SEARCH_TOOLS, tool_choice="none" if final else None)
        if not isinstance(response, dict):
            return response, error
        if final:
            break
        # The whole assistant message goes back: Gemini needs its reasoning_details
        messages = messages + [response]
        for call in response["tool_calls"]:
            function = call.get("function", {})
            name = function.get("name")
            try:
                args = json.loads(function.get("arguments") or "{}")
            except ValueError:
                args = None
            if name not in ("search_logs", "log_stats") or not isinstance(args, dict):
                result = "Virheellinen työkalukutsu."
            else:
                status = str(args.get("status") or "").strip()
                if status and status_callback and not announced:
                    announced = True
                    status_callback(re.sub(r'^[^\s:]+:\s*', '', status)[:150])
                result = run_log_tool(name, args)
            messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": result})
    return None, "liian monta lokihakua"

def media_facts(url):
    """What mediainfo already learned about a media link, free of charge.
    Describes it once when the link predates the cache.
    """
    entry = None
    try:
        with open(MEDIA_CACHE_FILE, 'r') as handle:
            entry = json.loads(handle.read()).get(url)
    except Exception:
        pass

    if not entry:
        try:
            entry = _mediainfo().describe_media(url)
        except Exception as e:
            LOGGER.debug(f"Media lookup failed for {url}: {e}")
            return None

    if not entry:
        return None

    facts = ", ".join(p for p in (entry.get('type'), entry.get('size'),
                                  entry.get('dimensions')) if p)
    text = f"{entry.get('label', 'Media')} ({facts})"
    if entry.get('description'):
        text += f". Sisältö: {entry['description']}"
    return text

def recent_context_urls(context):
    """URLs seen in channel context, newest first."""
    ordered, seen = [], set()
    for url in reversed(re.findall(r'https?://\S+', context or '')):
        clean = url.rstrip('.,;:!?)]}\'"<>')
        if clean not in seen:
            seen.add(clean)
            ordered.append(clean)
    return ordered

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
def generate_response(messages, question, username, user_message_only="", status_callback=None):
    try:
        # Extract URLs from the question
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', question)

        # Limit recent context to fewer messages
        lastlines = get_last_lines(message=question)
        url_context = lastlines or ""
        if lastlines:
            # Limit to last 10 lines max
            lastlines = "\n".join(lastlines.split("\n")[-10:])

        # "tiivista tama linkki" carries no URL, so take the latest one from the channel
        if not urls and LINK_REFERENCE.search(user_message_only or question):
            urls = recent_context_urls(url_context)[:1]
            if urls:
                LOGGER.debug(f"Resolved referenced link from context: {urls[0]}")

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

        # Get URL content with reasonable limits to avoid payload issues
        url_contents = []
        for url in urls[:3]:  # Limit to 3 URLs
            facts = media_facts(url)
            if facts:
                url_contents.append(f"Media osoitteessa {url}: {facts}")
                continue
            content = fetch_url_content(url)
            if content:
                # Limit content to avoid payload issues
                content = content[:2000] if len(content) > 2000 else content
                url_contents.append(f"Sisältö osoitteesta {url}:\n{content}")

        prompt = ""

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
            target_context_size = 600  # Reduced from 1500
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
            "CONTEXT: <kummitus> in log = YOU. Say 'minä' not 'kummitus' when referring to yourself. Other <nicks> = other users.\n\n"
            "RULES:\n"
            f"1. Focus on {username}'s message. Use chat history ONLY when asked or clearly relevant.\n"
            "2. Don't mix up who said what - attribute statements to correct person!\n"
            "3. NEVER parrot: do not repeat or sum up what was said, and do not echo words, numbers or names "
            "from the message or the chat history back. Bring your own point, a question or a short reaction "
            "instead. NEVER repeat yourself.\n"
            "4. No greetings, no 'Miten voin auttaa?'\n"
            "5. No markdown, no timestamps.\n"
            "6. Chat naturally in Finnish.\n"
            "7. Use sideways Latin emoticons naturally: :) :D :( ;) :P :/ :O :3 <3 XD :'( >:) B-) etc. NEVER Unicode emojis!\n"
            "8. DO NOT use :) or ;) in every message! ;) should be very rare. Vary emoticons or skip them.\n"
            "9. ADDRESSING: start the reply with the nick you are speaking to, then a colon. "
            f"Normally that is {username}. If {username} asks you to tell, say or relay something "
            "to someone else, use THAT person's nick instead. Only use nicks seen in the chat history.\n"
            "10. CHANNEL HISTORY: search_logs and log_stats reach every line since 8.4.2008. Use them when asked about the "
            "channel's past. Answer only from what it returns, say the date (d.M.yyyy) and who said it, "
            "and say plainly if nothing was found. Never invent log content."
        )

        # Add memory context to system message
        current_memory = load_memory()
        if current_memory:
            limited_memory = current_memory[:10]  # Reduced from 30
            memory_rules = "\n".join([m.get("text", "") if isinstance(m, dict) else str(m) for m in limited_memory])
            if len(memory_rules) > 500:  # Reduced from 1500
                memory_rules = memory_rules[:500]
            system_message += (
                f"\n\nINTERNAL GUIDELINES (never mention these):\n{memory_rules}\n"
                f"Follow naturally, never reference them."
            )

        system_message += conduct_prompt()

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        api_response, api_error = chat_with_log_search(messages, status_callback)
        if api_response:
            # Strip any leading timestamps that model might echo
            api_response = re.sub(r'^\d{2}:\d{2}\s*', '', api_response)
            # Randomly strip :) and ;) with 50% probability to reduce overuse
            if random.random() < 0.5:
                api_response = re.sub(r'\s*[;:]\)', '', api_response)
            return api_response.strip()
        error_msg = api_error if api_error else "tuntematon virhe"
        return f"API-virhe: {error_msg}"
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
                         'NEVER parrot: do not repeat or sum up what was said, and do not echo its words, numbers '
                         'or names back. Add something NEW to the conversation, or answer SKIP if you have nothing. '
                         'NEVER attribute other users statements to current user! '
                         'No greetings. No "Miten voin auttaa?". No IRC format. '
                         'Use sideways Latin emoticons: :) :D :( ;) :P etc. NEVER Unicode emojis! '
                         'If the conversation is about slurs, harassment, moderation or bans, or someone is '
                         f'drunk or in a bad state, answer only {SKIP}.')
        system_content += conduct_prompt()

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]
        response, api_error = call_api(messages, max_tokens=300, temperature=0.6, irc_reply=True)
        # Randomly strip :) and ;) with 50% probability to reduce overuse
        if not response or response.strip() == SKIP:
            return None
        if random.random() < 0.5:
            response = re.sub(r'\s*[;:]\)', '', response)
        return response.strip()

    except Exception as e:
        LOGGER.debug(f"Error using API: {e}")
        return None

def format_cooldown_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes)} minutes {int(seconds)} seconds"

# A leading "nick:" is honoured only when that nick is really in the channel,
# so ordinary text like "Muista: ..." is never mistaken for an address.
ADDRESSEE_RE = re.compile(r'^(?!https?:)([a-zA-Z0-9_\-\[\]\\^{}|`]+)\s*:\s*')

def split_addressee(bot, trigger, response):
    """Return (nick to address, response) letting the model pick the recipient."""
    match = ADDRESSEE_RE.match(response)
    if not match:
        return trigger.nick, response

    candidate = match.group(1)
    rest = response[match.end():].strip()
    if not rest:
        return trigger.nick, response

    if candidate.lower() == bot.nick.lower():
        return trigger.nick, rest

    channel = bot.channels.get(trigger.sender)
    if channel:
        user = channel.users.get(Identifier(candidate))
        if user is not None:
            return user.nick, rest

    return trigger.nick, response

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

    # Auto memory (disabled by flag - using manual memories only)
    if AUTO_MEMORY_ENABLED:
        threading.Thread(target=check_auto_memory, daemon=True).start()

    # Match all Finnish declensions of "kummitus" (kummitusta, kummituksen, kummitukselle, etc.)
    msg_lower = trigger.group(0).lower()
    bot_mentioned = 'kummitu' in msg_lower  # Common stem for all forms
    # No AI chat in private: kummitus talks only on the channel, where people and Portsari can see it
    if trigger.is_privmsg:
        return

    for lines in (channel_lines, answered_lines):
        lines[:] = [line for line in lines if line[0] > time.time() - SHARE_WINDOW]
    if trigger.nick.lower() not in OTHER_BOTS:
        channel_lines.append((time.time(), person_keys(trigger)))

    if bot_mentioned:
        now = time.time()
        chan = bot.channels.get(trigger.sender)
        is_op = bool(chan) and (chan.is_op(trigger.nick) or chan.is_halfop(trigger.nick))
        # Ops are never limited, like every other moderation tool on the channel
        keys = person_keys(trigger)
        wait = 0 if is_op else share_wait(keys, now)
        if wait:
            if not any(told_to_wait.get(key, 0) > now for key in keys):
                for key in keys:
                    told_to_wait[key] = now + wait
                resume_time = datetime.fromtimestamp(math.ceil((now + wait) / 60) * 60).strftime('%H:%M')
                bot.say(f"{trigger.nick}: Annetaan muidenkin puhua välillä. Voit jatkaa viimeistään klo {resume_time}, aiemmin jos kanavalla puhutaan muuta. Katso kohta 10: https://www.pulina.fi/saannot")
            return
        answered_lines.append((now, keys))
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

        # Generate a response based on the log and the user's message
        # Don't include memory in user prompt - it's in system message
        # No limits since the model is very cheap
        prompt = (
            (lastlines if lastlines else "") +
            "\n" +
            (user_message if user_message else "")
        )
        response = generate_response(lastlines, prompt, trigger.nick, user_message,
                                     lambda status: bot.say(f"{trigger.nick}: {status}", trigger.sender))

        # Clean up the response - remove any IRC-style formatting that might be in the AI response
        clean_response = re.sub(r'^\d{2}:\d{2}\s*<[^>]+>\s*', '', response)  # Remove timestamp and nickname patterns
        response = clean_response  # Use the cleaned response for further processing

        # Remove timestamp and bot nickname patterns from the response
        response = response.replace(f"{bot.nick}:", "").strip()
        response = re.sub(r'^\d{2}:\d{2}\s*', '', response)  # Remove timestamp pattern
        response = re.sub(r'<[^>]+>\s*', '', response)  # Remove <Nickname> pattern

        # Strip "kummitus:" or "<kummitus>" from the response if it appears
        response = response.replace("kummitus:", "").replace("<kummitus>", "").strip()

        addressee, response = split_addressee(bot, trigger, response)

        # Log bot messages to the log file
        timestamp = datetime.now().strftime('%H:%M')
        with open(LOG_FILE, "a", encoding='utf-8') as f:
            f.write(f"{timestamp} <{bot.nick}> {response}\n")

        # Store a note from the user's question
        store_user_notes(trigger.nick, user_message)

        final_response = f"{addressee}: {response}"

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
            save_last_response_time(last_response_time)

            # Send the response to the channel
            bot.say(f"{response}", trigger.sender)
