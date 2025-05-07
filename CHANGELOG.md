# Changelog

## [Dev Branch] - 2025-05-07

### Added
- **Dynamic Personality System (Experimental):**
  - Sally now adapts her core personality traits (warmth, humor, sarcasm, formality, patience) per user, based on interaction patterns and sentiment analysis.
  - Personality traits evolve over time and affect the system prompt, making Sally's conversational style more responsive and realistic.
  - Traits are stored in `personality_data.json` and revert toward defaults if not reinforced.
  - Sentiment analysis is powered by NLTK VADER (optional, bot runs even if NLTK is unavailable).
  - Interaction history is tracked for each user and viewable by the owner.
- **Owner-Only Personality Commands:**
  - `!personality [@user] [trait]`: View Sally's current personality profile or a specific trait for any user (owner only).
  - `!resetpersonality [@user]`: Reset Sally's personality adaptation for a user (owner only).
  - `!viewpersonality <user_id>`: View personality data for any user ID, even if not in the server (owner only).
  - `!setpersonality <user_id> <trait> <value>`: Directly set a personality trait for any user (owner only).
- **Robust NLTK Handling:**
  - Bot will run without sentiment analysis if NLTK is not installed, logging a warning instead of crashing.

### Changed
- All personality-related commands are now strictly owner-only for privacy and testing.
- System prompt is now dynamically modified with trait-based instructions, not just mood.
- Improved error handling and startup checks for dependencies.

### Testing/Notes
- These changes are currently on the **Dev Branch** for testing and feedback.
- Personality adaptation is experimental and may be tweaked or reset in future updates.
- Please report any bugs or unexpected behavior during testing.


## [1.3.1] - 2025-05-07

### Changed
- **System Prompt Consolidation:**
  - The content of `system_prompt_no_gif.txt` has been merged into `system_prompt.txt`, which is now the sole file for the bot's default persona.
  - `bot.py`: Updated `load_system_prompt()` function to exclusively load `system_prompt.txt` and exit if it's not found (removed fallback logic). Global `SYSTEM_PROMPT` renamed to `DEFAULT_SYSTEM_PROMPT` for clarity and updated in relevant functions.
  - `README.md`: All references to `system_prompt_no_gif.txt` removed; documentation now correctly points to `system_prompt.txt` as the single default prompt file.

### Removed
- **Redundant Prompt File:** Deleted `system_prompt_no_gif.txt` as its content is now in `system_prompt.txt`.

---

## [1.3.0] - 2025-05-07

### Added
- **API Key Checks:** Bot now performs explicit checks for `DISCORD_TOKEN` and `GEMINI_API_KEY` on startup and will exit if they are missing from the `.env` file.
- **Owner-Specific Prompt Logic:** Introduced `OWNER_SYSTEM_PROMPT_ADDENDUM` to systematically apply special interaction rules when the bot communicates with the owner.
- **Centralized Canned Responses:** Implemented `send_canned_response()` helper function in `bot.py` to manage sending pre-defined replies (for ignore list, repeated messages, 'are you sure' catches) and consistently update conversation histories.
- **Dynamic System Prompt Selection:** Added `get_system_prompt_for_user()` within `on_message` to robustly select and apply system prompts (default, per-user, or owner-specific variations).

### Changed
- **Import Organization:** Moved `import random` and `import string` to the top of `bot.py` for better organization.
- **Error Handling:** Improved exception handling in `load_user_history` to catch more specific errors (e.g., `json.JSONDecodeError`) and provide clearer console messages.
- **Refactored `on_message` Catches:** The logic for handling ignored users, repeated user messages, and "are you sure" phrases now utilizes the `send_canned_response()` helper, reducing code duplication.
- **Gemini API Call Consistency:** Ensured the correct `system_prompt_to_use` is passed to `call_gemini_api` during both initial calls and retries within the repetition-check loop.
- **README.md - Conversation History:** Clarified the distinction between persistent per-user history (`user_history.json`) and in-memory per-channel history (for repetition checks).
- **README.md - .env Setup:** Removed `TENOR_API_KEY` from the `.env` setup instructions.
- **Code Maintainability:** General improvements to code structure and comments in `bot.py` for better readability and maintainability.

### Removed
- **GIF Functionality:** All code and configuration related to GIF fetching (Tenor API integration, `MOOD_KEYWORDS`, helper functions like `fetch_gif_url`, `extract_gemini_gif`, and related logic) has been completely removed from `bot.py`. References to GIF-related system prompts were also updated in the README.

---

## [1.2.5] - 2025-05-06

### Added
- **Owner-only ignore commands:**
  - `!ignore <discord_id>`: Lets the owner add a Discord user ID to an in-memory ignore list. Ignored users always get a generic, in-character response and no further processing occurs.
  - `!clearignores`: Lets the owner clear the ignore list and restore normal bot behavior for all users.
- **Repeated message catch:**
  - If a user sends the exact same message to Sally twice in a row (ignoring case, whitespace, and punctuation), Sally now immediately responds with a generic, in-character roast and does not call the Gemini API.

### Changed
- **'Are you sure' catch:**
  - Now triggers if the phrase "are you sure" appears anywhere in the message (not just as a standalone message). Sally instantly responds with a generic, in-character line and skips Gemini API processing.
- **Context and prompt handling:**
  - Further refinements to keep context concise and relevant, and to clarify per-user prompt logic.

---

- **Context construction:**
  - Further refined conversation context logic, ensuring only the most recent exchanges are included for both channel and user histories. This keeps Gemini prompts concise and relevant.
- **Per-user system prompt logic:**
  - Improved fallback and selection for custom prompts in the `prompts/` directory. Clarified logic for owner and special user handling.
- **Prompt management:**
  - Minor code cleanup and additional comments for maintainability.

---

## [1.2.0] - 2025-05-06

### Added
- **Per-user system prompts:**
  - New `prompts/` directory for storing custom system prompts for individual users by their Discord user ID.
  - Each user can now have a unique Sally persona, with fallback to the default prompt if no custom file exists.
- **Hostile/gaslighting personas:**
  - Added support for extremely hostile, antagonistic, and gaslighting Sally personas for specific users (see example prompts for user IDs `545883597446316032` and `212343952920018944`).
- **Mentioned user history:**
  - When a message mentions another user, that user's recent conversation history is included in the Gemini context for richer, more relevant responses.

### Changed
- **Code cleanup:**
  - Removed all references to the old `system_prompt_special.txt` (now fully handled by per-user prompt files).
  - Refactored prompt selection logic for maintainability and scalability.
- **Improved prompt management:**
  - Adding or updating a user's persona now only requires editing or creating a file in the `prompts/` directory—no code changes needed.
- **Pretty-printed user history:**
  - `user_history.json` is now saved in a human-readable, indented format for easier inspection.

---

### Fixed
- Gemini API integration for Gemini 2.0:
  - Updated payload structure to remove unsupported roles and fields.
  - System prompt is now prepended to the user prompt in a single message (no more 'system' role).
  - Improved error handling and logging for API responses.

## [1.1.1] - 2025-05-06

### Changed
- Increased Gemini API temperature to 2 for more creative and varied responses from Sally.

## [1.1.0] - 2025-05-06

### Added
- `user_history.json` is now in `.gitignore` and will not be tracked by git (local history only by default).
- The README now explains how to migrate or copy `user_history.json` to preserve user history when moving to a new device or environment.

### Changed
- Upgraded Gemini API model from `gemini-1.5-flash-latest` to `gemini-2.0-flash` for improved performance and capabilities.

---

## [1.0.0] - 2025-05-06

### Added
- **Per-user persistent history:**
  - Sally now saves and loads conversation history for each user in `user_history.json`, in addition to per-channel history.
  - User history is included in Gemini context for more personalized responses.
- **Owner recognition:**
  - Added `OWNER_ID` (set in `.env`).
  - When the owner interacts, Sally switches to a flirty, affectionate, girlfriend-like persona (instead of the usual shitposting style).
- **Australian ironic nickname banter:**
  - Sally now frequently uses ironic Australian nicknames ("champ", "chief", "sport", etc.) in a tongue-in-cheek way, especially when roasting or being sarcastic.
- **System prompt variants:**
  - Created `system_prompt_no_gif.txt`, a version of the system prompt with all GIF usage removed for pure text banter mode.

### Changed
- **System prompt:**
  - Updated to reflect the new banter style and nickname usage.
  - Examples now show Sally using nicknames and no GIFs (in the no-GIF version).
- **GIF logic:**
  - All GIF response logic in `bot.py` is now commented out, so Sally only sends text replies for now.

### Fixed
- N/A

### Removed
- N/A

---

**How to use the no-GIF prompt:**
- Switch the loaded prompt in `bot.py` to `system_prompt_no_gif.txt` if you want Sally to avoid GIFs entirely.

**How to re-enable GIFs:**
- Uncomment the relevant code blocks in `bot.py`.
- Switch back to `system_prompt.txt` for prompt instructions/examples with GIFs.

---

For details on individual features or to roll back changes, see the commit history or contact the developer.
