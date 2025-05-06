import discord
import requests
import json
import os
from discord.ext import commands
from collections import deque
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', 'YOUR_DISCORD_TOKEN_HERE')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=' + GEMINI_API_KEY
OWNER_ID = os.getenv('OWNER_ID', None)

# --- LOAD SYSTEM PROMPT FROM FILE ---
def load_system_prompt():
    with open('system_prompt.txt', 'r', encoding='utf-8') as f:
        return f.read().strip()

SYSTEM_PROMPT = load_system_prompt()

# Conversation history (per channel)
history = {}
# Per-user persistent history
USER_HISTORY_FILE = 'user_history.json'
USER_MAX_HISTORY = 10
user_history = {}
MAX_HISTORY = 10

def load_user_history():
    global user_history
    if os.path.exists(USER_HISTORY_FILE):
        with open(USER_HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                user_history = json.load(f)
            except Exception:
                user_history = {}
    else:
        user_history = {}

def save_user_history():
    with open(USER_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_history, f)

load_user_history()

# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- GEMINI API CALL ---
def call_gemini_api(prompt, context=None):
    headers = {'Content-Type': 'application/json'}
    data = {
        'contents': [
            {'role': 'user', 'parts': [{'text': prompt}]}
        ],
        'safety_settings': [
            {"category": "HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    if context:
        data['contents'].extend(context)
    response = requests.post(GEMINI_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            return 'Sorry, I had trouble understanding the response.'
    else:
        return 'Error: Could not reach Gemini API.'

# --- CONTEXT-AWARE GIF FETCHING ---
TENOR_API_KEY = os.getenv('TENOR_API_KEY', 'LIVDSRZULELA')  # Public demo key, replace with your own for production
TENOR_URL = 'https://tenor.googleapis.com/v2/search'

MOOD_KEYWORDS = [
    ('celebrate', ['celebrate', 'congrats', 'party', 'victory', 'success']),
    ('happy', ['happy', 'joy', 'smile', 'excited', 'yay']),
    ('sad', ['sad', 'cry', 'tears', 'upset', 'depressed']),
    ('funny', ['funny', 'lol', 'lmao', 'rofl', 'hilarious']),
    ('angry', ['angry', 'mad', 'rage', 'furious']),
    ('love', ['love', 'heart', 'romance', 'cute']),
]

# --- GIF-related logic (commented out) ---
# def extract_gif_mood(text):
#     lowered = text.lower()
#     for mood, keywords in MOOD_KEYWORDS:
#         for kw in keywords:
#             if re.search(r'\b' + re.escape(kw) + r'\b', lowered):
#                 return mood
#     return None
#
# def fetch_gif_url(query):
#     params = {
#         'q': query,
#         'key': TENOR_API_KEY,
#         'limit': 1,
#         'media_filter': 'minimal',
#         'contentfilter': 'off',
#     }
#     try:
#         resp = requests.get(TENOR_URL, params=params)
#         if resp.status_code == 200:
#             results = resp.json().get('results', [])
#             if results and 'media_formats' in results[0]:
#                 gif_url = results[0]['media_formats']['gif']['url']
#                 return gif_url
#     except Exception:
#         pass
#     return None
#
# --- Parse for Gemini GIF suggestion ---
# def extract_gemini_gif(response_text):
#     match = re.search(r'^GIF:\s*(.+)$', response_text, re.MULTILINE)
#     if match:
#         search_term = match.group(1).strip()
#         # Remove GIF line from response
#         cleaned = re.sub(r'^GIF:.*$', '', response_text, flags=re.MULTILINE).strip()
#         return cleaned, search_term
#     return response_text, None

# --- REPETITION DETECTION ---
def is_repeated(channel_id, new_response):
    prev_responses = history.get(channel_id, deque(maxlen=MAX_HISTORY))
    return new_response.strip() in (r.strip() for r in prev_responses)

# --- COMMANDS ---
# (setprofile command removed to prevent user changes to character)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user.mentioned_in(message):
        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        # Prepare channel history
        prev = history.get(channel_id, deque(maxlen=MAX_HISTORY))
        # Prepare user history
        user_prev = deque(user_history.get(user_id, []), maxlen=USER_MAX_HISTORY)
        # Compose context: system prompt, (optionally owner system prompt), user history, then channel history
        context = [{'role': 'system', 'parts': [{'text': SYSTEM_PROMPT}]}]
        if OWNER_ID and user_id == OWNER_ID:
            context.append({'role': 'system', 'parts': [{'text': "The user you are interacting with is your boyfriend. When talking to him, drop the shitposting act and instead be flirty, affectionate, and playful, like a loving but sassy girlfriend. Use pet names, tease him, and show affection, but keep your unique personality. Don't be overly formal—be warm, supportive, and sometimes a little cheeky or romantic."}]})
        context += [{'role': 'user', 'parts': [{'text': m}]} for m in list(user_prev)]
        context += [{'role': 'user', 'parts': [{'text': m}]} for m in list(prev)]
        prompt = message.content
        response = call_gemini_api(prompt, context)
        # Repetition detection (still per channel)
        tries = 0
        while is_repeated(channel_id, response) and tries < 2:
            response = call_gemini_api(prompt, context)
            tries += 1
        # Parse for Gemini GIF suggestion (commented out)
        # response, gemini_gif_term = extract_gemini_gif(response)
        # Save to channel history
        prev.append(message.content)
        prev.append(response)
        history[channel_id] = prev
        # Save to user history (persisted)
        user_prev.append(message.content)
        user_prev.append(response)
        user_history[user_id] = list(user_prev)
        save_user_history()
        # --- GIF RESPONSE LOGIC (commented out) ---
        # sent_text = False
        # if response.strip():
        #     await message.channel.send(response)
        #     sent_text = True
        # if gemini_gif_term:
        #     gif_url = fetch_gif_url(gemini_gif_term)
        #     if gif_url:
        #         await message.channel.send(gif_url)
        # elif not sent_text:  # If no text and no explicit GIF, fallback to mood
        #     mood = extract_gif_mood(response)
        #     if mood:
        #         gif_url = fetch_gif_url(mood)
        #         if gif_url:
        #             await message.channel.send(gif_url)
        # Instead, just send the text response:
        if response.strip():
            await message.channel.send(response)
    await bot.process_commands(message)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
