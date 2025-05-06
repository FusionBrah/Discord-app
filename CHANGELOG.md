# Changelog

## [Unreleased]

### Added

### Changed

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
