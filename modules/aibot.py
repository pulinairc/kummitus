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

# Sopel logger
LOGGER = logger.get_logger(__name__)

# Define a cooldown period in seconds
COOLDOWN_PERIOD = 1800
last_response_time = None

# Files
LOG_FILE = 'pulina.log'
MENTIONED_USERS_FILE = "mentioned_users.json"
MEMORY_FILE = 'memory.json'
MEMORY_BACKUP_FILE = "memory-backup.json"
NOTES_FILE = 'user_notes.json'
LOG_FILE = 'pulina.log'
OUTPUT_FILE_DIR = "/var/www/botit.pulina.fi/public_html/"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, "muisti.txt")

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
                f.write("Muisti on tyhjä.")

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

# Function to retrieve the last 20 lines from pulina.log if the bot hasn't been mentioned in the last x lines
def get_last_lines():
    if not os.path.exists(LOG_FILE):
        return ""

    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            lines = f.readlines()

            # Get the last x lines to check for bot mentions
            last_lines = lines[-200:] if len(lines) >= 200 else lines

            # Initialize variables to track bot mentions
            last_bot_mention = None
            total_lines = len(last_lines)

            for i, line in enumerate(reversed(last_lines), 1):
                if "kummitus" in line.lower():
                    last_bot_mention = i
                    break

            if last_bot_mention is not None:
                # Calculate how many lines ago the bot was mentioned
                lines_since_mention = last_bot_mention
                LOGGER.debug(f"Bot was last mentioned {lines_since_mention} lines ago. No need to respond.")

                # Filter out lines that mention the bot
                non_bot_lines_full = [line for line in last_lines if "kummitus" not in line.lower()]
                return "\n".join(non_bot_lines_full)
            else:
                # If the bot wasn't mentioned in the last x lines
                LOGGER.debug("Bot hasn't been mentioned in the last 200 lines.")
                lines_since_mention = total_lines

                # Answer to random line from the last 10 lines
                last_short_lines = lines[-10:] if len(lines) >= 10 else lines
                last_short_lines = [line.strip() for line in last_short_lines]

                # Filter out lines that mention the bot
                non_bot_lines_short = [line for line in last_short_lines if "kummitus" not in line.lower()]

                if non_bot_lines_short:
                    return random.choice(non_bot_lines_short)
                else:
                    return "\n".join(non_bot_lines_full)

    except Exception as e:
        LOGGER.debug(f"Error reading log file: {e}")
        return ""

# Funktio noutaa lähettäjän nimen satunnaiselta riviltä
def extract_sender_from_line(line):
    match = re.search(r'<([^>]+)>', line)
    if match:
        return match.group(1)
    return None

# Function to call OpenAI GPT-4o-mini API and generate a response
def generate_response(messages, question, username):
    try:
        # Build the prompt from messages and the question
        prompt = (messages if messages else "") + "\nKysymys: " + (question if question else "")

        # Debug prompt
        LOGGER.debug(f"Prompt: {prompt}")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": 'Olet ystävällinen tyyppi, jonka nimi on Kummitus. Vastaa kysymyksiin alle 300 merkillä. Älä koskaan sisällytä vastaukseesi "kummitus:"-merkintää. Vältä turhien "Onko jotain muuta, mistä haluaisit jutella?" kysymysten kyselemistä. Sinun ei tarvitse joka kerta sanoa, että olet täällä tai että muistat kaikki sinulle kerrotut asiat.'},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300,
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
                {"role": "system", "content": 'Olet ystävällinen tyyppi, jonka nimi on Kummitus. Kirjoita kommentti asiaan alle 300 merkillä. Älä koskaan sisällytä vastaukseesi "kummitus:"-merkintää. Vältä turhien "Onko jotain muuta, mistä haluaisit jutella?" kysymysten kyselemistä.'},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300,
        )

        # Extract the actual text response from the API call
        return response.choices[0].message.content.strip()

    except Exception as e:
        LOGGER.debug(f"Error using OpenAI API: {e}")
        return None

def format_cooldown_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes)} minutes {int(seconds)} seconds"

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

        # The user's message is the entire matched pattern
        user_message = trigger.group(0)

        # Remove the bot's nickname from the message
        if user_message.lower().startswith(f"{bot.nick.lower()}:"):
          user_message = user_message[len(f"{bot.nick}:"):].strip()

        # Include the memory in the prompt
        if memory:
            memory_prompt = "Muista tästä etenpäin nämä seuraavat tärkeät asiat, mutta tuo esiin vain tarvittaessa tai satunnaisesti pyytämättä ja yllättäen: " + " ".join(memory)
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
        LOGGER.debug(f"Memory prompt: {memory_prompt}")

        # Debug last lines
        LOGGER.debug(f"Last lines: {lastlines}")

        # Generate a response based on the log and the user's message
        prompt = (lastlines if lastlines else "") + "\n" + (memory_prompt if memory_prompt else "") + "\n" + (user_message if user_message else "")
        response = generate_response(lastlines, prompt, trigger.nick)

        # If trigger nick is bot's nickname, remove it from the response
        if trigger.nick.lower() == bot.nick.lower():
            response = response.replace(f"{bot.nick}:", "").strip()

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
    if last_response_time and (time.time() - last_response_time) < COOLDOWN_PERIOD:
        remaining_time = COOLDOWN_PERIOD - (time.time() - last_response_time)
        LOGGER.debug(f"Cooldown active, bot will not respond randomly. Cooldown ends in {format_cooldown_time(remaining_time)}.")
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
            bot.say(f"{sender}: {response}", trigger.sender)

