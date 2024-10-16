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

# Log file
LOG_FILE = 'pulina.log'
MENTIONED_USERS_FILE = "mentioned_users.json"

# Load environment variables from .env file
load_dotenv()

# Load OpenAI as client
client = OpenAI()

# Set OpenAI API key from dotenv or environment variable
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# File paths
NOTES_FILE = "user_notes.json"
LOG_FILE = "pulina.log"  # Path to pulina.log, adjust as necessary

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

# Function to retrieve the last x number of lines from pulina.log, excluding bot's own messages
def get_last_lines():
    if not os.path.exists(LOG_FILE):
        return ""

    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            lines = f.readlines()

            # Do not include "kummitus:" lines in the response
            lines = [line for line in lines if not line.lower().startswith("kummitus:")]

            # Get the last lines, or all if fewer
            lastlines = lines[-200:] if len(lines) >= 200 else lines

            # Strip newline characters and join
            lastlines = [line.strip() for line in lastlines]

            # Exclude lines from 'kummitus'
            filtered_lines = [line for line in lastlines if not line.lower().startswith('kummitus:')]
            return "\n".join(filtered_lines)
    except Exception as e:
        print(f"Error reading log file: {e}")
        return ""

# Function to call OpenAI GPT-4o-mini API and generate a response
def generate_response(messages, question, username):
    try:
        if messages:
            prompt = messages + "\nKysymys: " + question
        else:
            prompt = question

        if username in user_notes:
            prompt += f"\nMuistan, että viimeksi kerroit: {user_notes[username]}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": 'Olet ystävällinen tyyppi, jonka nimi on Kummitus. Vastaa kysymyksiin alle 300 merkillä. Älä koskaan sisällytä vastaukseesi "kummitus:"-merkintää. Vältä turhien "Onko jotain muuta, mistä haluaisit jutella?" kysymysten kyselemistä. Vastaa vain yhteen asiaan kerrallaan.'},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300,
        )

        # Extract the actual text response
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Virhe OpenAI API:n käytössä: {e}"

# Function to store user notes
def store_user_notes(username, message):
    user_notes[username] = message
    save_user_notes()

# Sopel trigger function to respond to questions when bot's name is mentioned or in private messages
@sopel.module.rule(r'(.*)')
def respond_to_questions(bot, trigger):
    # Check if the nickname is "Orvokki" and ignore the message if it is
    if trigger.nick == "Orvokki":
        return

    if bot.nick in trigger.group(0) or trigger.is_privmsg:
        # Do not reply if the private message is !reload or !restart
        if trigger.is_privmsg and trigger.group(0).startswith("!"):
            return

        # Get the last lines from pulina.log, excluding bot's own messages
        lastlines_lines = get_last_lines()

        # The user's message is the entire matched pattern
        user_message = trigger.group(0)

        # Check if message is appointed to a bot
        if user_message.lower().startswith(bot.nick.lower()):
            # Remove the bot's nickname from the message
            user_message = user_message[len(bot.nick):].strip()

        # If no recognized user was mentioned, add the original user to mentioned list
        add_mentioned_user(trigger.nick)

        # Generate a response based on the log and the user's message
        response = generate_response(lastlines_lines, user_message, trigger.nick)

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
