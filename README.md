# Gemini Discord Bot

A lightweight Discord bot that uses Google Gemini API to provide AI-powered responses, supports a backend-only character persona, conversation history, and repetition detection.

## Features
- Responds to @mentions in your Discord server
- Uses Google Gemini 2.0 API for AI responses (with updated integration)
- **Per-user system prompts:** Easily define custom Sally personalities for specific users by adding a text file in the `prompts/` directory named after their Discord user ID. The default persona is used if no custom file is found.
- **Owner-only ignore commands:** `!ignore <discord_id>` and `!clearignores` allow the bot owner to ignore or unignore users at runtime.
- Backend-only character persona (cannot be changed by Discord users)
- Remembers recent conversation history per channel
- Avoids repeating the same response to similar questions
- **Repeated message catch:** If a user repeats the same message, Sally responds with a generic roast instead of calling the API.
- **'Are you sure' catch:** Instantly replies with a generic, in-character response if "are you sure" appears anywhere in the message, skipping the API call.

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
4. **Edit the character system prompt or add per-user prompts**
   - To change the default Sally persona, open `system_prompt.txt` (or `system_prompt_no_gif.txt`) and edit as desired.
   - To assign a custom persona to a specific user, create a file in the `prompts/` directory named `<discord_user_id>.txt` and write their unique Sally prompt.
   - The bot will automatically use a user's custom prompt if present; otherwise, it falls back to the default.
   - The system prompt is automatically prepended to user messages for Gemini 2.0 API compatibility (no 'system' role is used).

5. **Run the bot**
   ```bash
   python bot.py
   ```

## Usage
- Mention the bot in any channel to get a response.
- The backend system prompt (in `system_prompt.txt` or `system_prompt_no_gif.txt`) defines Sally's default personality. For specific users, a custom prompt can be added in the `prompts/` directory.
- Only backend maintainers can change prompts by editing files; Discord users cannot change Sally's persona from within Discord.
- **Owner-only commands:**
  - `!ignore <discord_id>`: Add a user to the ignore list. Ignored users always get a generic Sally response and no Gemini API call is made.
  - `!clearignores`: Clear the ignore list and restore normal behavior.

---

**Note:**
- Conversation history is stored in memory and resets when the bot restarts.
- The character system prompt is stored in `system_prompt.txt` and loaded on startup.
