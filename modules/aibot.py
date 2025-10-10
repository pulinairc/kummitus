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
OUTPUT_FILE_DIR = "/var/www/botit.pulina.fi/public_html/"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, "muisti.txt")

# Constants
MAX_URL_SIZE = 10 * 1024 * 1024  # 10MB limit for URL content

# Configuration
HISTORICAL_LOG_DIR = "/home/rolle/pulina.fi/pul"

# Load environment variables from .env file
load_dotenv()

# Load OpenAI as client
client = OpenAI()

# Set OpenAI API key from dotenv or environment variable
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# Configuration for API choice - automatically determine based on available keys
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Prefer Pollinations if key is set, otherwise use OpenAI
USE_FREE_API = bool(POLLINATIONS_API_KEY)
FREE_API_URL = "https://text.pollinations.ai/openai"

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

# Finnish stop words to exclude from keyword searches
FINNISH_STOP_WORDS = {
    'on', 'ja', 'ei', 'se', 'että', 'en', 'ole', 'et', 'nyt', 'kun', 'mä', 'sä', 'ne',
    'te', 'me', 'he', 'tää', 'toi', 'ton', 'sen', 'sit', 'jos', 'mut', 'tai', 'vaan',
    'kyl', 'kyllä', 'joo', 'juu', 'nii', 'niin', 'voi', 'vois', 'ois', 'oot', 'oon',
    'olet', 'olen', 'olemme', 'olette', 'ovat', 'oli', 'olivat', 'ollut', 'olleet',
    'ei', 'eikö', 'eiks', 'ette', 'emme', 'älä', 'älkää', 'no', 'noh', 'ai', 'aijaa',
    'aha', 'ahaa', 'okei', 'ok', 'hm', 'hmm', 'öö', 'öh', 'aa', 'ah', 'oh', 'noh'
}

# Function to get today's messages from dedicated log file (excluding bot's own messages)
def get_todays_messages():
    today_log_file = "/var/www/botit.pulina.fi/public_html/lastlog.log"

    if not os.path.exists(today_log_file):
        LOGGER.debug(f"Today's log file not found: {today_log_file}")
        return ""

    try:
        with open(today_log_file, "r", encoding='utf-8') as f:
            lines = f.readlines()

            # Filter out bot's own messages and keep only last 100 lines (not 500!)
            todays_lines = [
                line.strip() for line in lines[-200:]  # Read last 200, filter to ~100
                if line.strip() and
                not re.search(r'<kummitus>', line, re.IGNORECASE) and
                'kummitus:' not in line.lower()
            ][-100:]  # Keep only last 100 after filtering

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

# Function to search historical logs for keywords and return context around matches
def search_historical_logs(keywords, max_results=20, context_lines=5):
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

                # Search files in REVERSE order (newest first) and limit results
                # This way we get newest matches quickly without timing out
                cmd = f'grep -i -B {context_lines} -A {context_lines} "{escaped_keyword}" $(ls -t {HISTORICAL_LOG_DIR}/pulina-*.log) 2>/dev/null | head -2000'

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
                            if current_context and current_file and current_timestamp:
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
                            filename = os.path.basename(filepath)
                            if filename.startswith('pulina-') and filename.endswith('.log'):
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
                    if current_context and current_file and current_timestamp:
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

        # Remove duplicates based on matched_line while preserving order
        seen = set()
        unique_conversations = []
        for conv in all_conversations:
            key = conv['matched_line']
            if key not in seen:
                seen.add(key)
                unique_conversations.append(conv)

        LOGGER.debug(f"Found {len(unique_conversations)} unique conversation contexts (sorted newest first)")
        return unique_conversations[:max_results]

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

def call_free_api(messages, max_tokens=5000, temperature=0.5):
    """Call the Pollinations API"""
    try:
        payload = {
            "model": "openai",  # Pollinations uses "openai" as model name
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        # Use the actual Pollinations API key if available
        auth_header = f"Bearer {POLLINATIONS_API_KEY}" if POLLINATIONS_API_KEY else "Bearer dummy-key"

        response = requests.post(
            FREE_API_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_header
            },
            timeout=15  # Reduced from 30 to 15 seconds
        )

        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                LOGGER.debug(f"Unexpected free API response format: {result}")
                return None
        else:
            LOGGER.debug(f"Free API error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        LOGGER.debug(f"Error calling free API: {e}")
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

        # Extract keywords from the user's question
        keywords = extract_keywords(user_text)
        LOGGER.debug(f"Extracted keywords from '{user_text}': {keywords}")
        LOGGER.debug(f"Asking about logs/history: {asking_about_logs}")

        # Only search historical logs if explicitly asking about history/logs
        historical_matches = []
        if asking_about_logs and keywords:
            # This is set in the main function to notify user
            LOGGER.debug(f"Searching historical logs for keywords: {keywords}")
            historical_matches = search_historical_logs(keywords, max_results=20, context_lines=7)
            LOGGER.debug(f"Found {len(historical_matches)} historical matches with context")
        else:
            LOGGER.debug("Not searching historical logs (not asking about history)")

        # For recent context, just use last 100 lines from today (for general conversation flow)
        recent_context = get_todays_messages()
        if not recent_context:
            # Fallback to recent messages from main log
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_context = [
                    line.strip() for line in all_lines[-100:]
                    if line.strip() and
                    re.search(r'^\d{2}:\d{2}\s*<[^>]+>', line) and
                    not re.search(r'<kummitus>', line, re.IGNORECASE) and
                    'kummitus:' not in line.lower() and
                    not re.search(r'<[^>]+>\s*kummitus[,:]', line, re.IGNORECASE)
                ][-50:]  # Keep last 50 valid messages for recent flow
                recent_context = "\n".join(recent_context)
        LOGGER.debug(f"Recent context length: {len(recent_context)} characters")

        # Add historical context if found (now with conversation context)
        historical_context = ""
        if historical_matches:
            historical_sections = []

            for match in historical_matches[:10]:  # Limit to 10 conversations
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

        # Add historical context if available
        if historical_context:
            prompt += historical_context

        # Add recent context
        prompt += f"Tähänastiset keskustelut:\n{recent_context}\n\n"

        if url_contents:
            prompt += "\n".join(url_contents) + "\n"
        if messages:
            # Limit messages to avoid payload issues
            prompt += messages[-3000:] + "\n" if len(messages) > 3000 else messages + "\n"
        prompt += "Viesti: " + question

        # Final safety check - if prompt is too large, reduce context properly
        if len(prompt) > 35000:
            LOGGER.debug(f"Prompt too large ({len(prompt)} chars), reducing context")

            # Reduce recent_context to fit within limits - keep NEWEST messages
            target_context_size = 20000
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
                    prompt += messages[-2000:] + "\n" if len(messages) > 2000 else messages + "\n"
                prompt += "Viesti: " + question


        # More detailed debug logging
        LOGGER.debug(f"Recent context length: {len(recent_context)}")
        LOGGER.debug(f"Last lines length: {len(lastlines) if lastlines else 0}")
        LOGGER.debug(f"Full prompt length: {len(prompt)}")
        LOGGER.debug(f"Prompt structure:\n{prompt[:500]}...")  # Show more of the prompt structure

        # Build system message with memory context
        system_message = (
            "Olet kummitus-botti IRC-kanavalla. Vastaa luonnollisesti ja inhimillisesti. "
            "Vastauksen on oltava alle 220 merkkiä pitkä. "
            "Älä koskaan vastaa IRC-formaatissa (esim. 'HH:MM <nick>'). "
            "Älä mainitse muistojasi tai aiempia keskusteluja, ellei niitä erikseen kysytä. "
            "Käytä muistojasi taustalla ymmärtääksesi tilanteen, mutta älä korosta niitä vastauksessasi. "
            "Vältä toistamasta samoja kysymyksiä kuten 'Miten muuten menee?' tai 'Mitä kuuluu?'. "
            "Ole luova ja vaihtele vastauksiasi. Reagoi suoraan siihen mitä ihmiset sanovat sen sijaan että kyselet yleisiä kysymyksiä. "
            "\n\nHISTORIALLISEN DATAN TULKINTA - KRIITTINEN:"
            "Jos näet 'Historiallisia löytöjä' -osion, nämä ovat todellisia löytöjä historiallisista IRC-logeista vuosilta 2008-nykyhetki. "
            "[YYYY-MM] tarkoittaa että viesti on lähetetty kyseiseltä vuodelta ja kuukaudelta. "
            "TÄRKEÄÄ: Sana voi esiintyä MISSÄ TAHANSA osassa IRC-viestiä ja se LASKETAAN MAININNAKSI: "
            "- Chat-viesteissä: '<nick> sanoo jotain sanaa sisältävää' "
            "- Nicknameissä: '<banaani> sanoo jotain' "
            "- Hostnames/osoitteissa: '-!- nick [~banaani@host.fi] has joined' "
            "- Join/part-viesteissä: käyttäjien liittymisissä ja poistumisissä "
            "ESIMERKKI: Jos näet '[2010-03] 08:40 -!- timiZ- [~banaani@host.fi] has joined #pulina', niin sana 'banaani' esiintyi maaliskuussa 2010 ensimmäisen kerran. "
            "Jos löydät MINKÄ TAHANSA esiintymän haettua sanaa historiallisista löydöistä, kerro milloin se esiintyi ensimmäisen kerran ja mainitse missä yhteydessä. "
            "ÄLÄ KOSKAAN sano 'ei löydy' jos näet sanan historiallisissa löydöissä. Käytä VAIN todellisia löytöjä. "
            f"Tämä päivä on {datetime.now().strftime('%Y-%m-%d')}, joten kaikki historiallisten löytöjen päivämäärät ovat menneisyydestä."
        )

        # Add memory context to system message for understanding, but instruct not to mention it
        if memory:
            memory_context = " ".join(memory[-3:])  # Use only last 3 memory items
            system_message += f" Muistosi (älä mainitse näitä suoraan): {memory_context}"

        # Try free API first if enabled
        if USE_FREE_API:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            free_response = call_free_api(messages, max_tokens=5000, temperature=0.5)
            if free_response:
                return free_response
            else:
                LOGGER.debug("Free API failed, falling back to paid API")

        # Fallback to paid API
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=5000,
        )

        # Extract the actual text response
        return response.choices[0].message.content.strip()
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
        system_content = ('Olet kummitus-botti IRC-kanavalla. Vastaa luonnollisesti ja inhimillisesti. '
                         'Vastauksen on oltava alle 220 merkkiä pitkä. '
                         'Älä koskaan vastaa IRC-formaatissa (esim. "HH:MM <nick>"). '
                         'Älä mainitse muistojasi tai aiempia keskusteluja, ellei niitä erikseen kysytä. '
                         'Vältä toistamasta samoja kysymyksiä kuten "Miten muuten menee?" tai "Mitä kuuluu?". '
                         'Ole luova ja vaihtele vastauksiasi. Reagoi suoraan siihen mitä ihmiset sanovat sen sijaan että kyselet yleisiä kysymyksiä.')

        # Try free API first if enabled
        if USE_FREE_API:
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
            free_response = call_free_api(messages, max_tokens=5000, temperature=0.5)
            if free_response:
                return free_response
            else:
                LOGGER.debug("Free API failed, falling back to paid API")

        # Fallback to paid API
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=5000,
        )

        # Extract the actual text response from the API call
        return response.choices[0].message.content.strip()

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
            # Extract keywords to show user what we're searching for
            search_keywords = extract_keywords(user_message)
            if search_keywords:
                keywords_str = ", ".join(search_keywords)
                # Get oldest log file date
                import glob
                log_files = sorted(glob.glob(f"{HISTORICAL_LOG_DIR}/pulina-*.log"))
                if log_files:
                    oldest_file = os.path.basename(log_files[0])
                    oldest_date = oldest_file.replace('pulina-', '').replace('.log', '')
                    # Parse YYYY-MM format
                    if '-' in oldest_date:
                        year, month = oldest_date.split('-')
                        month_names = ['', 'tammikuusta', 'helmikuusta', 'maaliskuusta', 'huhtikuusta',
                                     'toukokuusta', 'kesäkuusta', 'heinäkuusta', 'elokuusta',
                                     'syyskuusta', 'lokakuusta', 'marraskuusta', 'joulukuusta']
                        month_name = month_names[int(month)] if int(month) <= 12 else f"kuusta {month}"
                        bot.say(f"{trigger.nick}: Etsin logeista nyt sanoilla: {keywords_str}. Käyn läpi kaikki kanavan logit {month_name} vuodesta {year}. Tässä voi kestää hetki...", trigger.sender)
                    else:
                        bot.say(f"{trigger.nick}: Etsin logeista nyt sanoilla: {keywords_str}. Käyn läpi kaikki kanavan logit. Tässä voi kestää hetki...", trigger.sender)
                else:
                    bot.say(f"{trigger.nick}: Etsin logeista nyt sanoilla: {keywords_str}. Tässä voi kestää hetki...", trigger.sender)

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
