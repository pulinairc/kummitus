"""
aibot.py
Made by rolle
"""
import sopel
from openai import OpenAI
from dotenv import load_dotenv
import json
import os
from datetime import datetime
from sopel import logger
import random
import time
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import mimetypes

# Sopel logger
LOGGER = logger.get_logger(__name__)

# Define a cooldown period in seconds
COOLDOWN_PERIOD = 14400
last_response_time = None

# Files
LOG_FILE = '/home/rolle/.sopel/pulina.log'
MENTIONED_USERS_FILE = "mentioned_users.json"
MEMORY_FILE = 'memory.json'
MEMORY_BACKUP_FILE = "memory-backup.json"
NOTES_FILE = 'user_notes.json'
LOG_FILE = 'pulina.log'
OUTPUT_FILE_DIR = "/var/www/botit.pulina.fi/public_html/"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, "muisti.txt")

# Keywords that indicate user wants to see chat history
log_related_words = [
  'viimeksi', 'kanavalla', 'logi', 'logissa', 'keskustelu',
  'puhuttu', 'sanottu', 'kirjoitettu', 'mainittu', 'keskusteltu', 'juttu', 'juttelua', 'juteltu', 'juttua', 'aiemmin', 'äsken', 'historia', 'tänään', 'eilen', 'lokissa', 'tapahtunut', 'tapahtui', 'puhetta', 'puhe',
  'keskustelua', 'viestit', 'viestejä', 'chatti', 'chatissa'
]

# Load environment variables from .env file
load_dotenv()

# Load OpenAI as client
client = OpenAI()

# Set OpenAI API key from dotenv or environment variable
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# File paths
MEMORY_FILE = "memory.json"

# Load or create memory list
def load_memory():
    # Debug
    LOGGER.debug(f"Loading memory from file: {MEMORY_FILE}")
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        return []

    with open(MEMORY_FILE, "r", encoding='utf-8') as f:
        try:
            # Debug
            LOGGER.debug(f"Memory loaded from file: {MEMORY_FILE}")
            return json.load(f)
        except json.JSONDecodeError:
            return []

# Function to save memory and append to a backup file
def save_memory(memory):
    LOGGER.debug(f"Saving memory to file: {MEMORY_FILE}")
    try:
        with open(MEMORY_FILE, "w", encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=4)
        LOGGER.debug(f"Memory saved: {memory}")
        backup_memory(memory)
        write_memory_to_file(memory)
    except Exception as e:
        LOGGER.debug(f"Error saving memory: {e}")

# Initialize memory from file
memory = load_memory()

# Function to add something to memory
def add_to_memory(item):
    global memory
    LOGGER.debug(f"Adding something to remember: {item}")
    memory.append(item)
    LOGGER.debug(f"Memory before saving: {memory}")
    save_memory(memory)

# Function to remove something from memory
def remove_from_memory(item):
    global memory
    LOGGER.debug(f"Trying to forget: {item}")

    original_memory = memory[:]
    memory = [m for m in memory if item.lower() not in m.lower()]

    if len(memory) < len(original_memory):
        LOGGER.debug(f"Removed memory item(s) containing: {item}")
        save_memory(memory)
        return True
    else:
        LOGGER.debug(f"Could not find any memory containing: {item}")
        return False

# Function to list everything in memory
def list_memory():
    if memory:
        return "\n".join(memory)
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
                f.write("\n".join(memory))
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
def find_mentioned_user(message):
    for user in mentioned_users:
        if user.lower() in message.lower():
            return user
    return None

# Declare last_bot_mention as global variable
last_bot_mention = None

# Function to retrieve the last lines from pulina.log if the bot hasn't been mentioned in the last x lines
def get_last_lines(message=None, mentioned_nick=None):
    if not os.path.exists(LOG_FILE):
        LOGGER.debug(f"Log file not found: {LOG_FILE}")
        return ""

    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-5000:] if len(lines) >= 5000 else lines

            # Keywords that indicate user wants to see chat history
            log_related_words = [
                'viimeksi', 'kanavalla', 'logi', 'logissa', 'keskustelu',
                'puhuttu', 'sanottu', 'kirjoitettu', 'mainittu', 'keskusteltu', 'juttu', 'juttelua', 'juteltu', 'juttua', 'aiemmin', 'äsken', 'historia', 'tänään', 'eilen',
                'lokissa', 'tapahtunut', 'tapahtui', 'puhetta', 'puhe',
                'keskustelua', 'viestit', 'viestejä', 'chatti', 'chatissa'
            ]

            # Debug log for message and keywords
            if message:
                LOGGER.debug(f"Checking message for log keywords: {message}")
                found_keywords = [word for word in log_related_words if word in message.lower()]
                LOGGER.debug(f"Found keywords: {found_keywords}")

                # If log-related words found, return all lines
                if found_keywords:
                    full_log = "\n".join(last_lines)
                    LOGGER.debug(f"Returning full log of {len(last_lines)} lines ({len(full_log)} characters)")
                    return full_log

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

            # If message contains time-related Finnish words, include recent context
            time_related_words = ['äsken', 'tänään', 'eilen', 'aiemmin', 'viimeksi']
            if message and any(word in message.lower() for word in time_related_words):
                # Filter out empty lines and system messages
                valid_lines = [line for line in last_lines if line.strip() and re.search(r'^\d{2}:\d{2}\s*<[^>]+>', line)]
                LOGGER.debug(f"Found {len(valid_lines)} valid lines for time-related query")
                return "\n".join(valid_lines[-10:])  # Return last 10 lines

            # Otherwise return the last 15 valid messages, excluding bot's messages and messages to bot
            valid_lines = []
            for line in reversed(last_lines):
                # Check if line matches IRC message format
                if re.search(r'^\d{2}:\d{2}\s*<[^>]+>', line):
                    # Skip if it's bot's message or a message containing "kummitus:"
                    if (not re.search(r'^\d{2}:\d{2}\s*<kummitus>', line, re.IGNORECASE) and
                        'kummitus:' not in line.lower() and
                        not re.search(r'<[^>]+>\s*kummitus[,:]', line, re.IGNORECASE)):
                        valid_lines.append(line)
                        if len(valid_lines) >= 15:  # Get last 15 valid messages
                            break

            if valid_lines:
                LOGGER.debug(f"Found {len(valid_lines)} valid lines (excluding bot messages and messages to bot)")
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

# Function to call OpenAI GPT-4o-mini API and generate a response
def generate_response(messages, question, username):
    try:
        # Extract URLs from the question
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', question)

        # Get the last lines from pulina.log
        lastlines = get_last_lines(message=question)  # For specific queries
        LOGGER.debug(f"Retrieved log lines: {lastlines[:200]}...")  # Debug the actual content

        # Always get last 15 lines for context
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            all_lines = f.readlines()
            # Filter valid IRC messages from last 15 lines
            recent_context = [
                line.strip() for line in all_lines[-15:]
                if line.strip() and re.search(r'^\d{2}:\d{2}\s*<[^>]+>', line)
            ]
            recent_context = "\n".join(recent_context)

        url_contents = []
        for url in urls:
            content = fetch_url_content(url)
            url_contents.append(f"Sisältö osoitteesta {url}:\n{content}")

        # Build the prompt with both context and URL contents if any
        prompt = f"Viimeiset keskustelut kanavalla:\n{recent_context}\n\n"  # Always include recent context

        # Add query-specific context if different from recent context
        if lastlines and lastlines != recent_context:
            # Check if this is a log-related query
            if any(word in question.lower() for word in log_related_words):
                prompt = f"Kanavan lastlog:\n{lastlines}\n\n"
            else:
                prompt = f"Aiheeseen liittyvät keskustelut:\n{lastlines}\n\n"

        if url_contents:
            prompt += "\n".join(url_contents) + "\n"
        if messages:
            prompt += messages + "\n"
        prompt += "Kysymys: " + question

        # More detailed debug logging
        LOGGER.debug(f"Recent context length: {len(recent_context)}")
        LOGGER.debug(f"Last lines length: {len(lastlines) if lastlines else 0}")
        LOGGER.debug(f"Full prompt length: {len(prompt)}")
        LOGGER.debug(f"Prompt structure:\n{prompt[:500]}...")  # Show more of the prompt structure

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": 'Olet kummitus-botti. Vastauksen on oltava alle 220 merkkiä pitkä. Älä koskaan vastaa IRC-formaatissa (esim. "HH:MM <nick>"). Vastaa aina suoraan asiaan. Käytä annettua keskusteluhistoriaa vastatessasi kysymyksiin kanavalla käydyistä keskusteluista.'},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=13000,
        )

        # Extract the actual text response
        return response.choices[0].message.content.strip()
    except Exception as e:
        LOGGER.debug(f"Error in using OpenAI API: {e}")
        return f"Virhe OpenAI API:n käytössä: {e}"

# Function to store user notes
def store_user_notes(username, message):
    user_notes[username] = message
    save_user_notes()
    LOGGER.debug(f"User note saved: {username} -> {message}")

# Function to generate a natural response using OpenAI API
def generate_natural_response(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": 'Olet kummitus-botti. Vastauksen on oltava alle 220 merkkiä pitkä. Älä koskaan vastaa IRC-formaatissa (esim. "HH:MM <nick>"). Vastaa aina suoraan asiaan. Käytä annettua keskusteluhistoriaa vastatessasi kysymyksiin kanavalla käydyistä keskusteluista.'},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=13000,
        )

        # Extract the actual text response from the API call
        return response.choices[0].message.content.strip()

    except Exception as e:
        LOGGER.debug(f"Error using OpenAI API: {e}")
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
    global last_response_time

    # Check if the nickname is "Orvokki" and ignore the message if it is
    if trigger.nick == "Orvokki":
        return

    if bot.nick in trigger.group(0) or trigger.is_privmsg:
        # Do not reply if the private message is !reload or !restart
        if trigger.is_privmsg and trigger.group(0).startswith("!"):
            return

        # Get the last lines from pulina.log, excluding bot's own messages
        lastlines = get_last_lines()

        # If bot is mentioned, strip the line from lastlines
        lastlines = "\n".join([line for line in lastlines.splitlines() if bot.nick.lower() not in line.lower()])

        # The user's message is the entire matched pattern
        user_message = trigger.group(0)

        # Remove the bot's nickname from the message
        if user_message.lower().startswith(f"{bot.nick.lower()}:"):
          user_message = user_message[len(f"{bot.nick}:"):].strip()

        # Include the memory in the prompt
        if memory:
            memory_prompt = '' + " ".join(memory)
        else:
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
        prompt = (lastlines if lastlines else "") + "\n" + (memory_prompt if memory_prompt else "") + "\n" + (user_message if user_message else "")
        response = generate_response(lastlines, prompt, trigger.nick)

        # Clean up the response - remove any IRC-style formatting that might be in the AI response
        clean_response = re.sub(r'^\d{2}:\d{2}\s*<[^>]+>\s*', '', response)  # Remove timestamp and nickname patterns
        response = clean_response  # Use the cleaned response for further processing

        # Remove timestamp and bot nickname patterns from the response
        response = response.replace(f"{bot.nick}:", "").strip()
        response = re.sub(r'^\d{2}:\d{2}\s*', '', response)  # Remove timestamp pattern
        response = re.sub(r'<[^>]+>\s*', '', response)  # Remove <Nickname> pattern

        # Prepend the user's nickname to the response
        final_response = f"{trigger.nick}: {response}"

        # Strip "kummitus:" or "<kummitus>" from the response, if in any part of it
        final_response = final_response.replace("kummitus:", "").replace("<kummitus>", "")

        # Log bot messages to the log file
        timestamp = datetime.now().strftime('%H:%M')
        with open(LOG_FILE, "a", encoding='utf-8') as f:
            f.write(f"{timestamp} <{bot.nick}> {response}\n")

        # Store a note from the user's question
        store_user_notes(trigger.nick, user_message)

        # Find if any mentioned user is in the message
        mentioned_user = find_mentioned_user(user_message)

        if mentioned_user:
            # If the user is recognized, strip out the trigger.nick from the response
            final_response = final_response.replace(f"{trigger.nick}:", "").strip()

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

        # Create a prompt for OpenAI based on the selected line
        prompt = f"Vastaa luonnollisesti seuraavaan viestiin: {random_line}"

        # Generate a response using OpenAI
        response = generate_natural_response(prompt)

        if response:

            # Log last response time
            last_response_time = time.time()

            # Send the response to the channel
            bot.say(f"{response}", trigger.sender)
