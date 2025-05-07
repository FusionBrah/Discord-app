import discord
import requests
import json
import os
from discord.ext import commands
from collections import deque
import re
import random
import string
import time
from datetime import datetime
from dotenv import load_dotenv

# Try to import NLTK for sentiment analysis, but make it optional
NLTK_AVAILABLE = False
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    # Download NLTK resources if not already downloaded
    try:
        nltk.data.find('vader_lexicon')
    except LookupError:
        nltk.download('vader_lexicon')
    NLTK_AVAILABLE = True
    print("NLTK successfully loaded. Sentiment analysis will be available.")
except ImportError:
    print("NLTK not available. Sentiment analysis will be disabled.")

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
    global DEFAULT_SYSTEM_PROMPT
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            DEFAULT_SYSTEM_PROMPT = f.read().strip()
            print("Successfully loaded system_prompt.txt as the default system prompt.")
    except FileNotFoundError:
        # No fallback, error out directly
        print(f"ERROR: Default system prompt file 'system_prompt.txt' not found. Please create it. Exiting.")
        exit()
    except Exception as e:
        print(f"Error loading system_prompt.txt: {e}. Exiting.")
        exit()

DEFAULT_SYSTEM_PROMPT = load_system_prompt()

# Conversation history (per channel)
history = {}
# Per-user persistent history
USER_HISTORY_FILE = 'user_history.json'
USER_MAX_HISTORY = 50
user_history = {}
MAX_HISTORY = 50

# Personality adaptation system
PERSONALITY_FILE = 'personality_data.json'

# Personality traits that can be modified
PERSONALITY_TRAITS = {
    'warmth': {
        'default': 50,  # 0-100 scale
        'description': 'How warm and friendly Sally is',
        'high_prompt': 'Be extra warm, friendly, and supportive in your responses. Use more endearing terms and show genuine care.',
        'low_prompt': 'Be more reserved and maintain professional distance. Use fewer endearing terms.'
    },
    'humor': {
        'default': 60,
        'description': 'How humorous and playful Sally is',
        'high_prompt': 'Use more humor, jokes, and playful language. Be witty and incorporate funny observations when possible.',
        'low_prompt': 'Be more serious and straightforward. Minimize jokes and focus on direct responses.'
    },
    'sarcasm': {
        'default': 70,
        'description': 'How sarcastic Sally is',
        'high_prompt': 'Incorporate more sarcasm and gentle teasing. Use more Australian slang terms like "champ", "sport", etc.',
        'low_prompt': 'Minimize sarcasm and avoid teasing. Be more literal and straightforward.'
    },
    'formality': {
        'default': 30,
        'description': 'How formal Sally is',
        'high_prompt': 'Use more formal language, proper grammar, and avoid slang. Be more professional in tone.',
        'low_prompt': 'Use casual language, contractions, and slang. Be conversational and relaxed in tone.'
    },
    'patience': {
        'default': 50,
        'description': 'How patient Sally is',
        'high_prompt': 'Show more patience with repetitive or simple questions. Provide thorough explanations without signs of frustration.',
        'low_prompt': 'Show less patience with repetitive or simple questions. Be more direct and concise.'
    }
}

# Interaction categories that affect personality
INTERACTION_CATEGORIES = {
    'friendly': {
        'traits': {'warmth': 2, 'humor': 1, 'sarcasm': -1, 'formality': -1, 'patience': 1},
        'keywords': ['thanks', 'thank you', 'appreciate', 'helpful', 'kind', 'nice', 'good job', 'love']
    },
    'hostile': {
        'traits': {'warmth': -2, 'humor': -1, 'sarcasm': 2, 'formality': 1, 'patience': -2},
        'keywords': ['stupid', 'dumb', 'idiot', 'useless', 'hate', 'bad', 'terrible', 'worst']
    },
    'formal': {
        'traits': {'warmth': -1, 'humor': -1, 'sarcasm': -2, 'formality': 2, 'patience': 1},
        'keywords': ['please', 'would you', 'could you', 'kindly', 'respectfully', 'sir', 'madam']
    },
    'casual': {
        'traits': {'warmth': 1, 'humor': 1, 'sarcasm': 1, 'formality': -2, 'patience': 0},
        'keywords': ['hey', 'yo', 'sup', 'lol', 'haha', 'cool', 'awesome', 'btw']
    },
    'inquisitive': {
        'traits': {'warmth': 0, 'humor': -1, 'sarcasm': -1, 'formality': 1, 'patience': 2},
        'keywords': ['why', 'how', 'what', 'when', 'where', 'explain', 'help', 'understand']
    },
    'joking': {
        'traits': {'warmth': 1, 'humor': 2, 'sarcasm': 2, 'formality': -2, 'patience': 0},
        'keywords': ['joke', 'funny', 'lmao', 'rofl', 'lol', 'haha', 'jk', 'kidding']
    }
}

# How quickly personality traits adapt (0-1, higher = faster adaptation)
ADAPTATION_RATE = 0.05

# How quickly personality traits revert to default (points per day)
REVERSION_RATE = 5

# Default personality data structure
personality_data = {}

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

# Personality system functions
def load_personality_data():
    global personality_data
    if os.path.exists(PERSONALITY_FILE):
        try:
            with open(PERSONALITY_FILE, 'r', encoding='utf-8') as f:
                personality_data = json.load(f)
                
                # Apply reversion based on time elapsed
                current_time = time.time()
                for user_id, data in personality_data.items():
                    last_update = data.get('last_update', current_time)
                    days_passed = (current_time - last_update) / (24 * 3600)  # Convert to days
                    
                    if days_passed > 0 and 'traits' in data:
                        # Gradually revert traits toward default values
                        for trait, value in data['traits'].items():
                            if trait in PERSONALITY_TRAITS:
                                default_value = PERSONALITY_TRAITS[trait]['default']
                                current_value = value
                                
                                # Calculate reversion
                                reversion = REVERSION_RATE * days_passed
                                if current_value > default_value:
                                    new_value = max(default_value, current_value - reversion)
                                elif current_value < default_value:
                                    new_value = min(default_value, current_value + reversion)
                                else:
                                    new_value = current_value
                                    
                                personality_data[user_id]['traits'][trait] = new_value
                        
                        # Update last_update timestamp
                        personality_data[user_id]['last_update'] = current_time
                        
        except json.JSONDecodeError as e:
            print(f"Error loading personality_data.json due to JSON decoding error: {e}. Starting with empty personality data.")
            personality_data = {}
        except Exception as e:
            print(f"An unexpected error occurred loading personality_data.json: {e}. Starting with empty personality data.")
            personality_data = {}
    else:
        personality_data = {}

def save_personality_data():
    with open(PERSONALITY_FILE, 'w', encoding='utf-8') as f:
        json.dump(personality_data, f, indent=2)

def get_user_personality(user_id):
    """Get the current personality traits for a user"""
    user_id = str(user_id)
    
    # Initialize if not exists
    if user_id not in personality_data:
        personality_data[user_id] = {
            'traits': {trait: info['default'] for trait, info in PERSONALITY_TRAITS.items()},
            'last_update': time.time(),
            'interaction_history': []
        }
    
    return personality_data[user_id]

def analyze_message_sentiment(message_content):
    """Analyze message sentiment using NLTK's VADER if available"""
    if not NLTK_AVAILABLE:
        # Return neutral sentiment if NLTK is not available
        return {'neg': 0, 'neu': 1, 'pos': 0, 'compound': 0}
        
    try:
        sia = SentimentIntensityAnalyzer()
        sentiment_scores = sia.polarity_scores(message_content)
        return sentiment_scores
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        # Return neutral sentiment if analysis fails
        return {'neg': 0, 'neu': 1, 'pos': 0, 'compound': 0}

def categorize_interaction(message_content):
    """Categorize the interaction based on message content"""
    message_lower = message_content.lower()
    
    # Track matched categories and their strength
    categories = {}
    
    # Check for keywords in each category
    for category, info in INTERACTION_CATEGORIES.items():
        match_count = 0
        for keyword in info['keywords']:
            if keyword in message_lower:
                match_count += 1
        
        if match_count > 0:
            # Calculate category strength based on matches
            strength = min(1.0, match_count / 3)  # Cap at 1.0
            categories[category] = strength
    
    # Add sentiment analysis for additional context
    sentiment = analyze_message_sentiment(message_content)
    
    # Strengthen friendly/hostile based on sentiment
    if sentiment['compound'] >= 0.5:  # Very positive
        categories['friendly'] = categories.get('friendly', 0) + 0.5
    elif sentiment['compound'] <= -0.5:  # Very negative
        categories['hostile'] = categories.get('hostile', 0) + 0.5
    
    return categories

def update_user_personality(user_id, message_content):
    """Update personality traits based on interaction"""
    user_id = str(user_id)
    
    # Get current personality
    user_personality = get_user_personality(user_id)
    
    # Categorize the interaction
    interaction_categories = categorize_interaction(message_content)
    
    # Record this interaction for history
    timestamp = datetime.now().isoformat()
    user_personality['interaction_history'].append({
        'timestamp': timestamp,
        'message': message_content[:100] + ('...' if len(message_content) > 100 else ''),
        'categories': interaction_categories
    })
    
    # Limit history length
    if len(user_personality['interaction_history']) > 20:
        user_personality['interaction_history'] = user_personality['interaction_history'][-20:]
    
    # Apply trait changes based on interaction categories
    if interaction_categories:
        for category, strength in interaction_categories.items():
            if category in INTERACTION_CATEGORIES:
                trait_effects = INTERACTION_CATEGORIES[category]['traits']
                
                for trait, effect in trait_effects.items():
                    if trait in user_personality['traits']:
                        # Apply effect scaled by strength and adaptation rate
                        change = effect * strength * ADAPTATION_RATE
                        current_value = user_personality['traits'][trait]
                        new_value = max(0, min(100, current_value + change))
                        user_personality['traits'][trait] = new_value
    
    # Update timestamp
    user_personality['last_update'] = time.time()
    
    # Save changes
    save_personality_data()
    
    return user_personality

def generate_personality_prompt_modifiers(user_id):
    """Generate prompt modifiers based on personality traits"""
    user_personality = get_user_personality(user_id)
    traits = user_personality['traits']
    
    modifiers = []
    
    # For each trait, determine if it's significantly high or low
    for trait, value in traits.items():
        if trait in PERSONALITY_TRAITS:
            trait_info = PERSONALITY_TRAITS[trait]
            default = trait_info['default']
            
            # If trait is significantly different from default
            if value >= default + 15:  # Significantly higher
                modifiers.append(trait_info['high_prompt'])
            elif value <= default - 15:  # Significantly lower
                modifiers.append(trait_info['low_prompt'])
    
    return modifiers

load_user_history()
load_personality_data()

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

@bot.command(name='personality')
async def check_personality(ctx, target_user: discord.Member = None, trait: str = None):
    """Check Sally's personality adaptation toward a user (owner only)"""
    if str(ctx.author.id) != str(OWNER_ID):
        await ctx.send("You do not have permission to use this command.")
        return
        
    if target_user is None:
        target_user = ctx.author
    
    user_id = str(target_user.id)
    user_personality = get_user_personality(user_id)
    
    if trait and trait.lower() in [t.lower() for t in PERSONALITY_TRAITS.keys()]:
        # Show specific trait
        trait_key = next(t for t in PERSONALITY_TRAITS.keys() if t.lower() == trait.lower())
        trait_value = user_personality['traits'][trait_key]
        trait_info = PERSONALITY_TRAITS[trait_key]
        trait_bar = generate_trait_bar(trait_value)
        
        await ctx.send(f"Sally's **{trait_key}** toward {target_user.display_name}: {trait_value:.1f}/100\n{trait_bar}\n*{trait_info['description']}*")
    else:
        # Show all traits
        embed = discord.Embed(title=f"Sally's Personality Toward {target_user.display_name}", color=0x00aaff)
        
        for trait, value in user_personality['traits'].items():
            if trait in PERSONALITY_TRAITS:
                trait_bar = generate_trait_bar(value)
                embed.add_field(
                    name=f"{trait.capitalize()}: {value:.1f}/100", 
                    value=f"{trait_bar}\n*{PERSONALITY_TRAITS[trait]['description']}*", 
                    inline=False
                )
        
        # Add recent interactions
        if user_personality.get('interaction_history', []):
            recent_interactions = user_personality['interaction_history'][-3:]
            interaction_text = "\n".join([f"• {i['timestamp'].split('T')[0]}: {i['message']}" for i in recent_interactions])
            embed.add_field(name="Recent Interactions", value=interaction_text or "No recent interactions", inline=False)
        
        await ctx.send(embed=embed)

def generate_trait_bar(value):
    """Generate a visual bar representing a trait value"""
    bar_length = 20
    filled_length = int(bar_length * value / 100)
    
    # Use a gradient of colors
    if value >= 75:  # Very high
        bar_char = '🟦'
    elif value >= 50:  # High
        bar_char = '🟩'
    elif value >= 25:  # Low
        bar_char = '🟨'
    else:  # Very low
        bar_char = '🟥'
    
    empty_char = '⚫'
    
    bar = bar_char * filled_length + empty_char * (bar_length - filled_length)
    return bar

@bot.command(name='resetpersonality')
async def reset_personality(ctx, target_user: discord.Member = None):
    """Reset Sally's personality adaptation toward a user (owner only)"""
    if str(ctx.author.id) != str(OWNER_ID):
        await ctx.send("You do not have permission to use this command.")
        return
    
    if target_user is None:
        target_user = ctx.author
    
    user_id = str(target_user.id)
    personality_data[user_id] = {
        'traits': {trait: info['default'] for trait, info in PERSONALITY_TRAITS.items()},
        'last_update': time.time(),
        'interaction_history': []
    }
    save_personality_data()
    
    await ctx.send(f"Reset Sally's personality adaptation toward {target_user.display_name} to default values.")

@bot.command(name='viewpersonality')
async def view_personality_by_id(ctx, user_id: str):
    """View personality data for any user ID (owner only)"""
    if str(ctx.author.id) != str(OWNER_ID):
        await ctx.send("You do not have permission to use this command.")
        return
    
    # Ensure user_id is a string
    user_id = str(user_id)
    
    # Get personality data
    user_personality = get_user_personality(user_id)
    
    # Create embed
    embed = discord.Embed(title=f"Sally's Personality Toward User ID: {user_id}", color=0x00aaff)
    
    # Add traits
    for trait, value in user_personality['traits'].items():
        if trait in PERSONALITY_TRAITS:
            trait_bar = generate_trait_bar(value)
            embed.add_field(
                name=f"{trait.capitalize()}: {value:.1f}/100", 
                value=f"{trait_bar}\n*{PERSONALITY_TRAITS[trait]['description']}*", 
                inline=False
            )
    
    # Add recent interactions
    if user_personality.get('interaction_history', []):
        recent_interactions = user_personality['interaction_history'][-3:]
        interaction_text = "\n".join([f"• {i['timestamp'].split('T')[0]}: {i['message']}" for i in recent_interactions])
        embed.add_field(name="Recent Interactions", value=interaction_text or "No recent interactions", inline=False)
    
    # Add last update time
    if 'last_update' in user_personality:
        last_update = datetime.fromtimestamp(user_personality['last_update']).strftime('%Y-%m-%d %H:%M:%S')
        embed.set_footer(text=f"Last updated: {last_update}")
    
    await ctx.send(embed=embed)

@bot.command(name='setpersonality')
async def set_personality_trait(ctx, user_id: str, trait: str, value: float):
    """Set a specific personality trait value for a user (owner only)"""
    if str(ctx.author.id) != str(OWNER_ID):
        await ctx.send("You do not have permission to use this command.")
        return
    
    # Ensure user_id is a string
    user_id = str(user_id)
    
    # Check if trait exists
    trait = trait.lower()
    valid_traits = [t.lower() for t in PERSONALITY_TRAITS.keys()]
    
    if trait not in valid_traits:
        await ctx.send(f"Invalid trait. Valid traits are: {', '.join(PERSONALITY_TRAITS.keys())}")
        return
    
    # Get the actual trait name with correct casing
    trait_key = next(t for t in PERSONALITY_TRAITS.keys() if t.lower() == trait)
    
    # Validate value
    try:
        value = float(value)
        if value < 0 or value > 100:
            await ctx.send("Value must be between 0 and 100.")
            return
    except ValueError:
        await ctx.send("Value must be a number between 0 and 100.")
        return
    
    # Get personality data and update the trait
    user_personality = get_user_personality(user_id)
    user_personality['traits'][trait_key] = value
    user_personality['last_update'] = time.time()
    
    # Save changes
    save_personality_data()
    
    # Generate trait bar for visual feedback
    trait_bar = generate_trait_bar(value)
    
    await ctx.send(f"Set {trait_key} to {value:.1f}/100 for user ID {user_id}\n{trait_bar}\n*{PERSONALITY_TRAITS[trait_key]['description']}*")

# --- GEMINI API CALL ---
def call_gemini_api(prompt, context=None, system_prompt_override=None, personality_modifiers=None):
    headers = {'Content-Type': 'application/json'}
    prompt_to_use = system_prompt_override if system_prompt_override is not None else DEFAULT_SYSTEM_PROMPT
    
    # Add personality modifiers if provided
    if personality_modifiers and isinstance(personality_modifiers, list):
        # Combine all modifiers into a single instruction block
        if personality_modifiers:
            personality_instruction = "\n\nAdditional personality instructions:\n" + "\n".join([f"- {modifier}" for modifier in personality_modifiers])
            prompt_to_use = f"{prompt_to_use}{personality_instruction}"
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

# --- CONTENT MODERATION ---
def contains_racist_content(text):
    """
    Check if the message contains racist content.
    Returns True if racist content is detected, False otherwise.
    """
    # List of racist terms and patterns to check for
    racist_terms = [
        # Add appropriate terms that you want to filter
        # This is a simplified implementation - consider using more sophisticated
        # content moderation APIs for production use
    ]
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Check for any racist terms in the message
    for term in racist_terms:
        if term in text_lower:
            return True
            
    # No racist content detected
    return False

# --- COMMANDS ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if OWNER_ID and contains_racist_content(message.content):
        await message.channel.send(f"<@{OWNER_ID}> Alert: Racist content detected in a message from {message.author.mention}.")
        
    # Update user's personality based on their message
    user_personality = update_user_personality(message.author.id, message.content)
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
                with open("system_prompt.txt", "r", encoding="utf-8") as f:
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
        # Extract mentioned users from the message content
        mentioned_histories = []
        mentioned_user_ids = []
        
        # Check for user mentions in the message
        for mention in message.mentions:
            if not mention.bot and str(mention.id) != user_id:  # Skip bot mentions and self-mentions
                mentioned_user_ids.append(str(mention.id))
        
        # Get conversation history for mentioned users
        for mentioned_id in mentioned_user_ids:
            user_convo = user_history.get(mentioned_id, [])
            if user_convo:
                # Get username if possible
                mentioned_user = None
                try:
                    mentioned_user = await bot.fetch_user(int(mentioned_id))
                    username = mentioned_user.display_name
                except:
                    username = f"User {mentioned_id}"
                
                # Add the last few exchanges from this user
                user_exchanges = list(user_convo)[-4:]  # Get last 4 messages
                if user_exchanges:
                    mentioned_histories.append(f"--- {username}'s recent messages ---")
                    mentioned_histories.extend(user_exchanges)
        
        if reply_chain:
            context_strings.append("--- Reply Chain ---")
            context_strings.extend(reply_chain[-2:])
        if mentioned_histories:  # Now this will check the populated mentioned_histories
            context_strings.append("--- Mentioned User History ---")
            context_strings.extend(mentioned_histories)
        if user_context_history: # Use user_context_history here
            context_strings.append("--- User & Sally Previous Exchanges ---")
            context_strings.extend(list(user_context_history)[-4:])
        if current_channel_history: # Use current_channel_history here
            context_strings.append("--- Channel Previous Exchanges ---")
            context_strings.extend(list(current_channel_history)[-4:])
        prompt = message.content
        context_strings.append("--- End of Context ---\nReply ONLY to the user's latest message above. Do NOT repeat or reference the above context directly. Always stay in character as Sally.")
        
        # Get personality modifiers based on user's personality traits
        personality_modifiers = generate_personality_prompt_modifiers(message.author.id)
        
        # Process with Gemini API, passing the personality modifiers
        response = call_gemini_api(message.content, context=context_strings, system_prompt_override=system_prompt_to_use, personality_modifiers=personality_modifiers)

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
