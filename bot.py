import os
import re
import asyncio
import sqlite3
from datetime import datetime, timedelta
from collections import Counter
import discord
from discord.ext import commands, tasks
from jinja2 import Environment, FileSystemLoader
from html2image import Html2Image
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "snapshot.db")
TEMPLATES_DIR = "templates"
STATIC_DIR = "static"
RECAP_HOUR = 21 

# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- DB SETUP ---
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS messages (
    user_id INTEGER,
    server_id INTEGER,
    channel_id INTEGER,
    date TEXT,
    message_count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, server_id, channel_id, date)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS words (
    user_id INTEGER,
    date TEXT,
    word TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date, word)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS emojis (
    user_id INTEGER,
    date TEXT,
    emoji TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date, emoji)
)
''')

c.execute('DROP TABLE IF EXISTS moods')

c.execute('''
CREATE TABLE moods (
    user_id INTEGER,
    date TEXT,
    mood TEXT,
    PRIMARY KEY (user_id, date)
)
''')

c.execute('DROP TABLE IF EXISTS notes')

c.execute('''
CREATE TABLE notes (
    user_id INTEGER,
    date TEXT,
    note TEXT,
    PRIMARY KEY (user_id, date)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS themes (
    user_id INTEGER PRIMARY KEY,
    theme TEXT DEFAULT 'pastel'
)
''')

conn.commit()

# --- UTILITIES ---

STOP_WORDS = {
    "the", "and", "to", "a", "of", "in", "i", "is", "that", "it", "on", "you",
    "this", "for", "with", "but", "are", "not", "have", "be", "at", "or", "as",
    "was", "so", "if", "we", "they", "he", "she", "an", "my", "me", "do", "no",
    "just", "from", "by", "your", "all", "can", "will", "what", "about", "up",
    "out", "get", "like", "when", "would", "there", "one", "some"
}

EMOJI_REGEX = re.compile(r'[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\u2600-\u26FF]', flags=re.UNICODE)

def clean_and_split_words(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    words = text.split()
    return [w for w in words if w not in STOP_WORDS]

def extract_emojis(text):
    return EMOJI_REGEX.findall(text)

def get_today_date():
    return datetime.utcnow().strftime("%Y-%m-%d")

def get_user_theme(user_id):
    c.execute("SELECT theme FROM themes WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else "pastel"

def set_user_theme(user_id, theme):
    c.execute("INSERT INTO themes(user_id, theme) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET theme=excluded.theme", (user_id, theme))
    conn.commit()

# --- JINJA ENV ---
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

hti = Html2Image(output_path="output", size=(900, 500))

# --- BOT EVENTS & COMMANDS ---

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    daily_recap.start()


@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return

    user_id = message.author.id
    date = get_today_date()

    # Increment message count per server/channel
    c.execute('''
    INSERT INTO messages(user_id, server_id, channel_id, date, message_count)
    VALUES (?, ?, ?, ?, 1)
    ON CONFLICT(user_id, server_id, channel_id, date) DO UPDATE SET message_count = message_count + 1
    ''', (user_id, message.guild.id if message.guild else 0, message.channel.id, date))
    
    # Count words
    words = clean_and_split_words(message.content)
    for w in words:
        c.execute('''
        INSERT INTO words(user_id, date, word, count)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id, date, word) DO UPDATE SET count = count + 1
        ''', (user_id, date, w))
    
    # Count emojis
    emojis = extract_emojis(message.content)
    for e in emojis:
        c.execute('''
        INSERT INTO emojis(user_id, date, emoji, count)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id, date, emoji) DO UPDATE SET count = count + 1
        ''', (user_id, date, e))
    
    conn.commit()

    await bot.process_commands(message)

# --- !mood command ---
@bot.command(name="mood")
async def mood(ctx):
    embed = discord.Embed(title="How are you feeling today?", description="React with one of the emojis below to log your mood:")
    mood_emojis = ["😃", "😐", "😢", "😠", "😴"]
    for e in mood_emojis:
        embed.add_field(name=e, value=f"{e}", inline=True)
    message = await ctx.send(embed=embed)
    for e in mood_emojis:
        await message.add_reaction(e)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in mood_emojis and reaction.message.id == message.id

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Mood input timed out. Please try again.")
        return

    mood_emoji = str(reaction.emoji)
    date = get_today_date()
    c.execute('''
        INSERT INTO moods(user_id, date, mood)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, date)
        DO UPDATE SET mood = excluded.mood
    ''', (ctx.author.id, date, mood_emoji))
    conn.commit()
    await ctx.send(f"Your mood {mood_emoji} has been recorded for today!")

# --- !note command ---
@bot.command(name="note")
async def note(ctx, *, text: str):
    date = get_today_date()
    c.execute('''
    INSERT INTO notes (user_id, date, note)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id, date)
    DO UPDATE SET note = excluded.note
    ''', (ctx.author.id, date, text))
    conn.commit()
    await ctx.send("Your note has been saved for tonight's recap!")

# --- !theme command ---
@bot.command(name="theme")
async def theme(ctx, theme_name: str):
    valid_themes = ["pastel", "dark", "neon"]
    if theme_name.lower() not in valid_themes:
        await ctx.send(f"Invalid theme. Choose from: {', '.join(valid_themes)}")
        return
    set_user_theme(ctx.author.id, theme_name.lower())
    await ctx.send(f"Theme set to {theme_name}!")

# --- !snapshot now command ---
@bot.command(name="snapshot")
async def snapshot(ctx, arg=None):
    if arg != "now":
        await ctx.send("Usage: `!snapshot now`")
        return
    await generate_and_send_card(ctx.author)
    await ctx.send("Snapshot sent via DM!")

# --- HELPER: Generate Snapshot Card ---
async def generate_and_send_card(user):
    date = get_today_date()

    # Gather message counts
    c.execute('''
    SELECT SUM(message_count) FROM messages WHERE user_id = ? AND date = ?
    ''', (user.id, date))
    total_messages = c.fetchone()[0] or 0

    # Top 5 words
    c.execute('''
    SELECT word, count FROM words WHERE user_id = ? AND date = ? ORDER BY count DESC LIMIT 5
    ''', (user.id, date))
    top_words = c.fetchall()

    # Top emoji
    c.execute('''
    SELECT emoji, count FROM emojis WHERE user_id = ? AND date = ? ORDER BY count DESC LIMIT 1
    ''', (user.id, date))
    top_emoji_row = c.fetchone()
    top_emoji = top_emoji_row[0] if top_emoji_row else "—"

    # Mood
    c.execute('''
    SELECT mood FROM moods WHERE user_id = ? AND date = ?
    ''', (user.id, date))
    mood_row = c.fetchone()
    mood = mood_row[0] if mood_row else "—"

    # Note
    c.execute('''
    SELECT note FROM notes WHERE user_id = ? AND date = ?
    ''', (user.id, date))
    note_row = c.fetchone()
    note = note_row[0] if note_row else ""

    # Theme
    theme = get_user_theme(user.id)

    def pretty_date(dt: datetime) -> str:
        # Use %#d for Windows, %-d for Linux/macOS
        return dt.strftime("%#d %B %Y") if os.name == "nt" else dt.strftime("%-d %B %Y")

    # Read CSS content and pass to template
    css_file = os.path.join(STATIC_DIR, f"{theme}.css")
    with open(css_file, "r", encoding="utf-8") as cssf:
        css_content = cssf.read()

    # Prepare data for template
    data = {
        "username": user.display_name,
        "date": pretty_date(datetime.strptime(date, "%Y-%m-%d")),
        "theme": theme,
        "messages_sent": total_messages,
        "top_words": [w for w, _ in top_words],
        "top_emoji": top_emoji,
        "mood": mood,
        "mood_desc": mood_description(mood),
        "note": note or "No note for today.",
        "css_content": css_content,
    }

    # Render HTML
    template = env.get_template("snapshot.html")
    html_content = template.render(data)

    # Save HTML temporarily
    html_file = f"output/{user.id}_snapshot.html"
    os.makedirs("output", exist_ok=True)
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Render image
    css_file = os.path.join(STATIC_DIR, f"{theme}.css")
    img_file = f"{user.id}_snapshot.png"
    hti.screenshot(html_file=html_file, save_as=img_file)

    # Send DM with image
    try:
        dm_channel = await user.create_dm()
        with open(f"output/{img_file}", "rb") as img:
            await dm_channel.send(file=discord.File(img, filename="snapshot.png"))
    except Exception as e:
        print(f"Failed to send DM to {user}: {e}")

def mood_description(mood_emoji):
    return {
        "😃": "Positive",
        "😐": "Neutral",
        "😢": "Sad",
        "😠": "Angry",
        "😴": "Tired"
    }.get(mood_emoji, "Unknown")


@tasks.loop(minutes=60)
async def daily_recap():
    now = datetime.utcnow()
    if now.hour == RECAP_HOUR:
        print("Starting daily recap...")
        # Get all users with messages today
        date = get_today_date()
        c.execute('SELECT DISTINCT user_id FROM messages WHERE date = ?', (date,))
        users = c.fetchall()
        for (user_id,) in users:
            user = bot.get_user(user_id)
            if user:
                await generate_and_send_card(user)
        print("Daily recap complete.")


if __name__ == "__main__":
    if TOKEN is None:
        print("Error: DISCORD_BOT_TOKEN environment variable not set.")
        exit(1)
    bot.run(TOKEN)
