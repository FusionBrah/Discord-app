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
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + GEMINI_API_KEY
OWNER_ID = os.getenv('OWNER_ID', None)

# --- LOAD SYSTEM PROMPT FROM FILE ---
def load_system_prompt():
    with open('system_prompt_no_gif.txt', 'r', encoding='utf-8') as f:
        return f.read().strip()

SYSTEM_PROMPT = load_system_prompt()

# Conversation history (per channel)
history = {}
# Per-user persistent history
USER_HISTORY_FILE = 'user_history.json'
USER_MAX_HISTORY = 50
user_history = {}
MAX_HISTORY = 50

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
        json.dump(user_history, f, indent=2)

load_user_history()

# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent for bot to read messages
bot = commands.Bot(command_prefix='!', intents=intents)

# --- IN-MEMORY IGNORE LIST ---
ignore_list = set()

# --- OWNER-ONLY COMMANDS ---
@bot.command(name='ignore')
async def ignore_user(ctx, discord_id: str):
    if str(ctx.author.id) != str(OWNER_ID):
        await ctx.send("You do not have permission to use this command.")
        return
    ignore_list.add(str(discord_id))
    await ctx.send(f"User ID {discord_id} added to ignore list.")

@bot.command(name='clearignores')
async def clear_ignores(ctx):
    if str(ctx.author.id) != str(OWNER_ID):
        await ctx.send("You do not have permission to use this command.")
        return
    ignore_list.clear()
    await ctx.send("Ignore list cleared.")

# --- GEMINI API CALL ---
def call_gemini_api(prompt, context=None, system_prompt_override=None):
    headers = {'Content-Type': 'application/json'}
    # Choose which system prompt to use
    prompt_to_use = system_prompt_override if system_prompt_override is not None else SYSTEM_PROMPT
    # Compose full prompt from context if provided
    if context and isinstance(context, list) and context:
        # Join all context parts (reply chain, user history, channel history) into one string with clear headers
        context_str = "\n".join(context)
        if prompt_to_use:
            full_prompt = f"{prompt_to_use}\n\n{context_str}\n\nUser's Message: {prompt}\nSally, reply only to the user's message above. Do not repeat or reference the context directly."
        else:
            full_prompt = f"{context_str}\n\nUser's Message: {prompt}\nSally, reply only to the user's message above. Do not repeat or reference the context directly."
    else:
        if prompt_to_use:
            full_prompt = f"{prompt_to_use}\n\nUser's Message: {prompt}\nSally, reply only to the user's message above. Do not repeat or reference the context directly."
        else:
            full_prompt = f"User's Message: {prompt}\nSally, reply only to the user's message above. Do not repeat or reference the context directly."
    contents = [{"parts": [{"text": full_prompt}]}]
    data = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 200, "temperature": 2}
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            try:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except Exception as inner_exc:
                print(f'[Gemini API] JSON parsing error: {inner_exc}')
                print(f'[Gemini API] Raw response: {response.text}')
                return 'Sorry, I had trouble understanding the response.'
        else:
            print(f'[Gemini API] Error: Status code {response.status_code}')
            print(f'[Gemini API] Response: {response.text}')
            return f'Error: Could not reach Gemini API (status {response.status_code})'
    except Exception as exc:
        print(f'[Gemini API] Exception: {exc}')
        return f'Error: Exception occurred while contacting Gemini API: {exc}'

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

# --- Simple Racist Keyword Detection ---
def contains_racist_content(text):
    # Replace with your actual list of keywords
    racist_keywords = [
        'nigger', 'nigga', 'nig',  # Example placeholders
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in racist_keywords)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Racist content detection and alert
    if OWNER_ID and contains_racist_content(message.content):
        await message.channel.send(f"<@{OWNER_ID}> Alert: Racist content detected in a message from {message.author.mention}.")
        # Optionally return here to stop further processing
        # return
    should_respond = False
    # Respond if @mentioned
    if bot.user.mentioned_in(message):
        should_respond = True
    # Respond if this is a reply to a message from the bot
    elif message.reference:
        ref = message.reference.resolved if hasattr(message.reference, 'resolved') else None
        if ref and hasattr(ref, 'author') and ref.author.id == bot.user.id:
            should_respond = True
    if should_respond:
        # --- Ignore list catch ---
        if str(message.author.id) in ignore_list:
            import random
            sally_ignore_responses = [
                "Not interested, champ.",
                "You're on ignore, legend.",
                "Nope. Try again later, mate.",
                "Ignored. Find someone else to bother, chief.",
                "I'm not talking to you right now, big guy.",
                "Blocked energy detected. Move along, sport.",
            ]
            response = random.choice(sally_ignore_responses)
            channel_id = str(message.channel.id)
            user_id = str(message.author.id)
            prev = history.get(channel_id, deque(maxlen=MAX_HISTORY))
            user_prev = deque(user_history.get(user_id, []), maxlen=USER_MAX_HISTORY)
            prev.append(message.content)
            prev.append(response)
            history[channel_id] = prev
            user_prev.append(message.content)
            user_prev.append(response)
            user_history[user_id] = list(user_prev)
            save_user_history()
            await message.reply(response, mention_author=False)
            return

        # --- Catch repeated user messages (ignore case, whitespace, punctuation) ---
        import string
        user_id = str(message.author.id)
        user_prev = deque(user_history.get(user_id, []), maxlen=USER_MAX_HISTORY)
        def normalize_msg(msg):
            return ''.join(c for c in msg.lower().strip() if c not in string.whitespace + string.punctuation)
        if len(user_prev) >= 2:
            last_user_msg = user_prev[-2]
            if normalize_msg(message.content) == normalize_msg(last_user_msg):
                import random
                sally_repeat_responses = [
                    "You just said that, champ.",
                    "Try something new, legend.",
                    "Is your keyboard stuck, mate?",
                    "Deja vu, chief? You already asked.",
                    "Mix it up, big guy.",
                    "Copy-paste game strong, but I'm not impressed.",
                    "You expecting a different answer, sport?",
                    "Boring! Next question, boss.",
                ]
                response = random.choice(sally_repeat_responses)
                await message.reply(response, mention_author=False)
                # Save to channel and user history for continuity
                channel_id = str(message.channel.id)
                prev = history.get(channel_id, deque(maxlen=MAX_HISTORY))
                prev.append(message.content)
                prev.append(response)
                history[channel_id] = prev
                user_prev.append(message.content)
                user_prev.append(response)
                user_history[user_id] = list(user_prev)
                save_user_history()
                return

        # --- Catch for 'are you sure' anywhere in the message (case-insensitive) ---
        if 'are you sure' in message.content.lower():
            import random
            sally_are_you_sure_responses = [
                "Not interested, champ.",
                "You're on ignore, legend.",
                "Nope. Try again later, mate.",
                "Ignored. Find someone else to bother, chief.",
                "I'm not talking to you right now, big guy.",
                "Blocked energy detected. Move along, sport.",
                "Yes. Are you done being annoying?",
                "YES. Now go touch grass, sport.",
                "You expecting a different answer, sport?",
                "Boring! Next question, boss.",
            ]
            response = random.choice(sally_are_you_sure_responses)
            channel_id = str(message.channel.id)
            user_id = str(message.author.id)
            prev = history.get(channel_id, deque(maxlen=MAX_HISTORY))
            user_prev = deque(user_history.get(user_id, []), maxlen=USER_MAX_HISTORY)
            prev.append(message.content)
            prev.append(response)
            history[channel_id] = prev
            user_prev.append(message.content)
            user_prev.append(response)
            user_history[user_id] = list(user_prev)
            save_user_history()
            await message.reply(response, mention_author=False)
            return

        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        # Prepare channel history
        prev = history.get(channel_id, deque(maxlen=MAX_HISTORY))
        # Prepare user history
        user_prev = deque(user_history.get(user_id, []), maxlen=USER_MAX_HISTORY)
        # --- If message mentions another user, load their history for context ---
        mentioned_histories = []
        for mentioned in message.mentions:
            mentioned_id = str(mentioned.id)
            if mentioned_id != user_id and mentioned_id in user_history:
                mentioned_msgs = user_history[mentioned_id][-USER_MAX_HISTORY:]
                for idx, msg in enumerate(mentioned_msgs):
                    author = mentioned.display_name if hasattr(mentioned, 'display_name') else mentioned.name
                    prefix = f"{author} (mentioned)"
                    if idx % 2 == 0:
                        mentioned_histories.append(f"{prefix}: {msg}")
                    else:
                        mentioned_histories.append(f"Sally (to {author}): {msg}")
        # --- Walk up reply chain for context ---
        reply_chain = []
        current = message
        try:
            while current.reference:
                ref = current.reference.resolved if hasattr(current.reference, 'resolved') else None
                if ref and hasattr(ref, 'content'):
                    # Format as "<author>: <content>"
                    author_name = getattr(ref.author, 'display_name', getattr(ref.author, 'name', 'User'))
                    reply_chain.append(f"{author_name}: {ref.content}")
                    current = ref
                else:
                    break
        except Exception:
            pass
        reply_chain = reply_chain[::-1]  # Oldest to newest
        # Compose context: system prompt, (optionally owner system prompt), reply chain, user history, channel history
        # Choose system prompt based on user
        def get_system_prompt_for_user(user_id):
            prompt_path = os.path.join('prompts', f'{user_id}.txt')
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            with open('system_prompt_no_gif.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
        system_prompt_to_use = get_system_prompt_for_user(user_id)
        # Compose context strings for Gemini prompt
        context_strings = []
        if OWNER_ID and user_id == OWNER_ID:
            context_strings.append("The user you are interacting with is your boyfriend. When talking to him, drop the shitposting act and instead be flirty, affectionate, and playful, like a loving but sassy girlfriend. Use pet names, tease him, and show affection, but keep your unique personality. Don't be overly formal—be warm, supportive, and sometimes a little cheeky or romantic.")
        if reply_chain:
            context_strings.append("--- Reply Chain ---")
            context_strings.extend(reply_chain[-2:])  # Only last 2
        if mentioned_histories:
            context_strings.append("--- Mentioned User History ---")
            context_strings.extend(mentioned_histories[-2:])  # Only last 2
        if user_prev:
            context_strings.append("--- User & Sally Previous Exchanges ---")
            context_strings.extend(list(user_prev)[-4:])  # Only last 2 exchanges (4 lines)
        if prev:
            context_strings.append("--- Channel Previous Exchanges ---")
            context_strings.extend(list(prev)[-4:])  # Only last 2 exchanges (4 lines)
        prompt = message.content
        # Add explicit instruction to only reply to the latest message
        context_strings.append("--- End of Context ---\nReply ONLY to the user's latest message above. Do NOT repeat or reference the above context directly. Always stay in character as Sally.")
        response = call_gemini_api(prompt, context_strings, system_prompt_override=system_prompt_to_use)

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
        # Instead, just send the text response as a reply:
        if response.strip():
            await message.reply(response, mention_author=False)
    await bot.process_commands(message)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
