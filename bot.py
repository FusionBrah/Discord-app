import discord
import requests
import json
import os
from discord.ext import commands
from collections import deque
import re
import random
import string
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OWNER_ID = os.getenv('OWNER_ID', None)

if not DISCORD_TOKEN:
    print("Error: DISCORD_TOKEN not found in .env file. Please set it and try again.")
    exit()
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file. Please set it and try again.")
    exit()

GEMINI_API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'

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

OWNER_SYSTEM_PROMPT_ADDENDUM = "The user you are interacting with is your boyfriend. When talking to him, drop the shitposting act and instead be flirty, affectionate, and playful, like a loving but sassy girlfriend. Use pet names, tease him, and show affection, but keep your unique personality. Don't be overly formal—be warm, supportive, and sometimes a little cheeky or romantic."

def load_user_history():
    global user_history
    if os.path.exists(USER_HISTORY_FILE):
        try:
            with open(USER_HISTORY_FILE, 'r', encoding='utf-8') as f:
                user_history = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading user_history.json due to JSON decoding error: {e}. Starting with an empty history.")
            user_history = {}
        except Exception as e:
            print(f"An unexpected error occurred loading user_history.json: {e}. Starting with an empty history.")
            user_history = {}
    else:
        user_history = {}

def save_user_history():
    with open(USER_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_history, f, indent=2)

load_user_history()

# --- HELPER FOR CANNED RESPONSES ---
async def send_canned_response(message, response_list, update_history=True):
    """Helper to send a random response, update history, and reply."""
    response = random.choice(response_list)
    if update_history:
        channel_id = str(message.channel.id)
        user_id_for_history = str(message.author.id)

        prev_channel = history.get(channel_id, deque(maxlen=MAX_HISTORY))
        prev_channel.append(message.content)
        prev_channel.append(response)
        history[channel_id] = prev_channel

        prev_user = deque(user_history.get(user_id_for_history, []), maxlen=USER_MAX_HISTORY)
        prev_user.append(message.content)
        prev_user.append(response)
        user_history[user_id_for_history] = list(prev_user)
        save_user_history()

    await message.reply(response, mention_author=False)

# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
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
    prompt_to_use = system_prompt_override if system_prompt_override is not None else SYSTEM_PROMPT
    if context and isinstance(context, list) and context:
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
    except requests.exceptions.Timeout:
        print(f'[Gemini API] Timeout after 15 seconds')
        return 'Sorry, the request to Gemini timed out.'
    except requests.exceptions.RequestException as exc:
        print(f'[Gemini API] RequestException: {exc}')
        return f'Error: A network problem occurred while contacting Gemini API: {exc}'
    except Exception as exc:
        print(f'[Gemini API] Exception: {exc}')
        return f'Error: Exception occurred while contacting Gemini API: {exc}'

# --- REPETITION DETECTION ---
def is_repeated(channel_id, new_response):
    prev_responses = history.get(channel_id, deque(maxlen=MAX_HISTORY))
    return new_response.strip() in (r.strip() for r in prev_responses)

# --- COMMANDS ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if OWNER_ID and contains_racist_content(message.content):
        await message.channel.send(f"<@{OWNER_ID}> Alert: Racist content detected in a message from {message.author.mention}.")
    should_respond = False
    if bot.user.mentioned_in(message):
        should_respond = True
    elif message.reference:
        ref = message.reference.resolved if hasattr(message.reference, 'resolved') else None
        if ref and hasattr(ref, 'author') and ref.author.id == bot.user.id:
            should_respond = True
    if should_respond:
        user_id = str(message.author.id)

        if user_id in ignore_list:
            sally_ignore_responses = [
                "Not interested, champ.", "You're on ignore, legend.", "Nope. Try again later, mate.",
                "Ignored. Find someone else to bother, chief.", "I'm not talking to you right now, big guy.",
                "Blocked energy detected. Move along, sport.",
            ]
            await send_canned_response(message, sally_ignore_responses, update_history=True)
            return

        # --- Catch repeated user messages (ignore case, whitespace, punctuation) ---
        current_user_history_for_repeat_check = deque(user_history.get(user_id, []), maxlen=USER_MAX_HISTORY)
        def normalize_msg(msg):
            return ''.join(c for c in msg.lower().strip() if c not in string.whitespace + string.punctuation)
        
        if len(current_user_history_for_repeat_check) >= 2:
            # The user's last actual message is at [-2] because history stores [user_msg, bot_reply, user_msg, bot_reply ...]
            last_user_msg_from_history = current_user_history_for_repeat_check[-2] 
            if normalize_msg(message.content) == normalize_msg(last_user_msg_from_history):
                sally_repeat_responses = [
                    "You just said that, champ.", "Try something new, legend.", "Is your keyboard stuck, mate?",
                    "Deja vu, chief? You already asked.", "Mix it up, big guy.",
                    "Copy-paste game strong, but I'm not impressed.", "You expecting a different answer, sport?",
                    "Boring! Next question, boss.",
                ]
                await send_canned_response(message, sally_repeat_responses, update_history=True)
                return

        # --- Catch for 'are you sure' anywhere in the message (case-insensitive) ---
        if 'are you sure' in message.content.lower():
            sally_are_you_sure_responses = [
                "Not interested, champ.", "You're on ignore, legend.", "Nope. Try again later, mate.",
                "Ignored. Find someone else to bother, chief.", "I'm not talking to you right now, big guy.",
                "Blocked energy detected. Move along, sport.", "Yes. Are you done being annoying?",
                "YES. Now go touch grass, sport.", "You expecting a different answer, sport?",
                "Boring! Next question, boss.",
            ]
            await send_canned_response(message, sally_are_you_sure_responses, update_history=True)
            return

        channel_id = str(message.channel.id)
        # user_id is already defined
        current_channel_history = history.get(channel_id, deque(maxlen=MAX_HISTORY))
        user_context_history = deque(user_history.get(user_id, []), maxlen=USER_MAX_HISTORY)

        # --- Determine System Prompt --- 
        def get_system_prompt_for_user(current_user_id):
            prompt_path = os.path.join('prompts', f'{current_user_id}.txt')
            base_prompt_text = ""
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    base_prompt_text = f.read().strip()
            else:
                # Fallback to default system prompt if no user-specific one
                with open('system_prompt_no_gif.txt', 'r', encoding='utf-8') as f:
                    base_prompt_text = f.read().strip()
            
            # Append owner-specific addendum if applicable
            if OWNER_ID and current_user_id == OWNER_ID:
                return f"{base_prompt_text}\n\n{OWNER_SYSTEM_PROMPT_ADDENDUM}"
            return base_prompt_text

        system_prompt_to_use = get_system_prompt_for_user(user_id)

        reply_chain = []
        current = message
        try:
            while current.reference:
                ref = current.reference.resolved if hasattr(current.reference, 'resolved') else None
                if ref and hasattr(ref, 'content'):
                    author_name = getattr(ref.author, 'display_name', getattr(ref.author, 'name', 'User'))
                    reply_chain.append(f"{author_name}: {ref.content}")
                    current = ref
                else:
                    break
        except Exception:
            pass
        reply_chain = reply_chain[::-1]
        context_strings = []
        # Removed direct OWNER_ID check here as it's handled by get_system_prompt_for_user
        # if OWNER_ID and user_id == OWNER_ID:
        #     context_strings.append(OWNER_SYSTEM_PROMPT_ADDENDUM) # This is now part of system_prompt_to_use
        if reply_chain:
            context_strings.append("--- Reply Chain ---")
            context_strings.extend(reply_chain[-2:])
        if mentioned_histories:
            context_strings.append("--- Mentioned User History ---")
            context_strings.extend(mentioned_histories[-2:])
        if user_context_history: # Use user_context_history here
            context_strings.append("--- User & Sally Previous Exchanges ---")
            context_strings.extend(list(user_context_history)[-4:])
        if current_channel_history: # Use current_channel_history here
            context_strings.append("--- Channel Previous Exchanges ---")
            context_strings.extend(list(current_channel_history)[-4:])
        prompt = message.content
        context_strings.append("--- End of Context ---\nReply ONLY to the user's latest message above. Do NOT repeat or reference the above context directly. Always stay in character as Sally.")
        
        response = call_gemini_api(prompt, context_strings, system_prompt_override=system_prompt_to_use)

        tries = 0
        while is_repeated(channel_id, response) and tries < 2:
            response = call_gemini_api(prompt, context_strings, system_prompt_override=system_prompt_to_use) # Pass system_prompt_to_use
            tries += 1

        current_channel_history.append(message.content)
        current_channel_history.append(response)
        history[channel_id] = current_channel_history

        final_user_persistence_history = deque(user_history.get(user_id, []), maxlen=USER_MAX_HISTORY)
        final_user_persistence_history.append(message.content)
        final_user_persistence_history.append(response)
        user_history[user_id] = list(final_user_persistence_history)
        save_user_history()

        if response.strip():
            await message.reply(response, mention_author=False)
    await bot.process_commands(message)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
