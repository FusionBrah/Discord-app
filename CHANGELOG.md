# Changelog

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
