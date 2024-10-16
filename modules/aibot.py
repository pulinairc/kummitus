"""
aibot.py
Made by rolle
"""
import sopel
from openai import OpenAI
from dotenv import load_dotenv
import json
import os

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

# Function to retrieve the last 100 lines from pulina.log, excluding bot's own messages
def get_last_100_lines():
    if not os.path.exists(LOG_FILE):
        return ""

    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            lines = f.readlines()
            # Get the last 100 lines, or all if fewer
            last_100 = lines[-100:] if len(lines) >= 100 else lines
            # Strip newline characters and join
            last_100 = [line.strip() for line in last_100]
            # Exclude lines from 'kummitus'
            filtered_lines = [line for line in last_100 if not line.lower().startswith('kummitus:')]
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
                {"role": "system", "content": "Olet ystävällinen tyyppi, jonka nimi on Kummitus. Haluat auttaa muita."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200,
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
        # Get the last 100 lines from pulina.log, excluding bot's own messages
        last_100_lines = get_last_100_lines()
        # The user's message is the entire matched pattern
        user_message = trigger.group(0)
        # Generate a response based on the log and the user's message
        response = generate_response(last_100_lines, user_message, trigger.nick)
        # Prepend the user's nickname to the response
        final_response = f"{trigger.nick}: {response}"
        # Send the response back to the channel or user
        bot.say(final_response, trigger.sender)

        # Store a note from the user's question
        store_user_notes(trigger.nick, user_message)
