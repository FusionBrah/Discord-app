# Gemini Discord Bot

A lightweight Discord bot that uses Google Gemini API to provide AI-powered responses, supports a backend-only character persona, conversation history, and repetition detection.

## Features
- Responds to @mentions in your Discord server
- Uses Google Gemini 2.0 API for AI responses (with updated integration)
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
     OWNER_ID=your_discord_user_id_here
     ```
   - `OWNER_ID` is the Discord user ID of the bot owner. This can be used to restrict certain commands or actions to only the owner, or for bot identification purposes.
   - The `.env` file is already in `.gitignore` and will not be tracked by git.
3. **User history:**
   - The file `user_history.json` is used to store conversation history for each user. This file is ignored by git (see `.gitignore`) and will not be included when you clone the repository.
   - If you want to preserve or carry over user history to another device, manually copy your `user_history.json` file to the new environment.
   - If starting fresh, the bot will create a new, empty `user_history.json` automatically.
4. **Edit the character system prompt**
   - Open `system_prompt.txt` in the project folder.
   - Change the text to define the bot's persona and behavior (see file for examples).
   - The system prompt is automatically prepended to user messages for Gemini 2.0 API compatibility (no 'system' role is used).

5. **Run the bot**
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
