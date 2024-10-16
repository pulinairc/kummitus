"""
openai.py
Made by rolle
"""
import sopel
import openai
from dotenv import load_dotenv
import os

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Get the last 100 messages from the channel
def get_last_100_lines(bot, trigger):
    channel = trigger.sender
    last_100_messages = []

    for message in bot.channels[channel].messages[-100:]:
        last_100_messages.append(f"{message.nick}: {message.message}")

    return "\n".join(last_100_messages)

# Call OpenAI API to generate a response
def generate_response(messages):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Olet ystävällinen IRC-botti nimeltään kummitus #pulina-kanavalla. Sinut on ohjelmoinut Roni 'rolle' Laukkarinen."},
                {"role": "user", "content": messages}
            ],
            max_tokens=500,
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Rajapintavirhe: {e}"

# Trigger
@sopel.module.rule(r'(.*)')
def respond_to_questions(bot, trigger):
    if bot.nick in trigger.group(0):
        last_100_lines = get_last_100_lines(bot, trigger)
        response = generate_response(last_100_lines)
        bot.say(response, trigger.sender)

