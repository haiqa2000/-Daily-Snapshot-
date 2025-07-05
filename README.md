# 📸 Daily Snapshot (SnapBot)

**Turn your daily Discord chatter into a stylish, share-worthy recap card — delivered every night via DM!**

---

## Elevator Pitch

Daily Snapshot is a tiny personal-analytics Discord bot that quietly watches how you chat each day, cooks the data into a stylish HTML “story card,” and DMs you a screenshot at night so you can reflect, laugh, and level-up your vibes. No third-party APIs or token headaches — just pure Discord magic.

---

## Features (MVP)

- **Message Counter:** Tracks how many messages you sent today per server/channel.
- **Top 5 Words & Emojis:** Frequency tally excluding common stop words.
- **Mood Check-In:** Use `!mood` command to log your mood with emoji reactions.
- **Mini Notepad:** DM `!note Your thought` to save a daily note.
- **Automatic 9 PM Recap:** At 21:00 server local time, generates an HTML snapshot, converts it to an image, and sends it via DM.
- **Theme Selector:** Use `!theme pastel | dark | neon` to customize your card style.

---

## Stretch & Fun Ideas

- Daily streaks & XP for opening your recap.
- Water reminder toggled by counting 💧 emojis.
- Leaderboard of top chatterers and most positive moods.
- Weather integration for card decoration.
- Seasonal themes (Eid, Halloween, New Year).

---

## Tech Stack

- **Bot Core:** Python + discord.py
- **Templating:** Jinja2 HTML templates
- **Styling:** Pure CSS (pastel, dark, neon themes)
- **HTML → Image:** `html2image` (uses wkhtmltoimage)
- **Data:** SQLite (single file DB)
- **Optional Frontend:** Tiny Node/Express panel (not included)

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- [wkhtmltoimage](https://wkhtmltopdf.org/downloads.html) installed and in your system PATH (required by `html2image`)

### Installation

1. Clone this repo:
- git clone this respiratory
- cd daily-snapshot


2. Install Python dependencies:
- pip install -r requirements.txt


3. Set your Discord bot token as an environment variable:
- export DISCORD_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"

4. Run the bot:
- python bot.py


---

## Usage

- **Log your mood:** `!mood` → React with an emoji.
- **Add a note:** `!note Your thought here`
- **Change theme:** `!theme pastel` (options: pastel, dark, neon)
- **Get snapshot now:** `!snapshot now`

At 9 PM server local time, the bot automatically sends your daily snapshot card via DM.

---

## Privacy & Security

- No third-party APIs or external data storage.
- All data is stored locally in SQLite.
- Your data never leaves your VPS or PC.

---

## Troubleshooting

- Make sure `wkhtmltoimage` is installed and accessible in your PATH.
- For large servers, consider opt-in usage to avoid DB bloat.
- Timezone handling is UTC-based by default; adjust if needed.

---

## License

MIT License

---

## Credits

Created by Haiqa Shahzad — inspired by the idea of turning daily Discord activity into a fun, shareable visual recap.

---

Happy chatting & snapshotting! 📸✨
