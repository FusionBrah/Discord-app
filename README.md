# Gemini Discord Bot

A lightweight Discord bot that uses Google Gemini API to provide AI-powered responses, supports a backend-only character persona, conversation history, and repetition detection.

## Features
- Responds to @mentions in your Discord server
- Uses Google Gemini API for AI responses
- Backend-only character persona (cannot be changed by Discord users)
- Remembers recent conversation history per channel
- Avoids repeating the same response to similar questions

## Setup
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Add your API keys and tokens**
   - Create a file named `.env` in the project folder (see example below).
   - Add your secrets (do **not** commit this file to GitHub):
     ```env
     DISCORD_TOKEN=your_discord_token_here
     GEMINI_API_KEY=your_gemini_api_key_here
     TENOR_API_KEY=your_tenor_api_key_here
     ```
   - The `.env` file is already in `.gitignore` and will not be tracked by git.

3. **Edit the character system prompt**
   - Open `system_prompt.txt` in the project folder.
   - Change the text to define the bot's persona and behavior (see file for examples).

4. **Run the bot**
   ```bash
   python bot.py
   ```

## Usage
- Mention the bot in any channel to get a response.
- Only the backend system prompt (in `system_prompt.txt`) defines the bot's personality. Users cannot change it via Discord.

---

**Note:**
- Conversation history is stored in memory and resets when the bot restarts.
- The character system prompt is stored in `system_prompt.txt` and loaded on startup.
