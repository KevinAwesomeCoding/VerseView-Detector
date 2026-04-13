# -*- coding: utf-8 -*-
"""
verseview_bot.py — Discord bot that remotely controls VerseView.

Run directly:  python3 verseview_bot.py
Launched by vv_gui.py via subprocess with env vars:
    VV_BOT_TOKEN, VV_HOST, VV_PORT
"""

import os
import sys
import asyncio
import platform
import socket
import datetime
import logging

import aiohttp
import discord
from discord.ext import commands, tasks
from discord import app_commands

# ── Config (env vars → fallback constants) ─────────────────────────────────────
BOT_TOKEN   = os.environ.get("VV_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
VV_HOST     = os.environ.get("VV_HOST",      "127.0.0.1")
VV_PORT     = os.environ.get("VV_PORT",      "12345")
VV_BASE     = f"http://{VV_HOST}:{VV_PORT}"

# ── VerseView HTTP endpoint paths — fill in after inspecting Network tab ───────
ENDPOINT_GOTO    = "/goto"        # POST  body: {"ref": "John 3:16"}
ENDPOINT_FORWARD = "/forward"     # POST
ENDPOINT_BACK    = "/back"        # POST
ENDPOINT_PRESENT = "/present"     # POST
ENDPOINT_CLOSE   = "/close"       # POST

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("vv_bot")

# ── Book map (all 66 books) ────────────────────────────────────────────────────
BOOK_MAP: dict[str, str] = {
    # OT
    "gen": "Genesis",       "genesis": "Genesis",
    "ex":  "Exodus",        "exo": "Exodus",        "exodus": "Exodus",
    "lev": "Leviticus",     "leviticus": "Leviticus",
    "num": "Numbers",       "numbers": "Numbers",
    "deu": "Deuteronomy",   "deut": "Deuteronomy",  "deuteronomy": "Deuteronomy",
    "jos": "Joshua",        "josh": "Joshua",        "joshua": "Joshua",
    "jdg": "Judges",        "judg": "Judges",        "judges": "Judges",
    "rut": "Ruth",          "ruth": "Ruth",
    "1sa": "1 Samuel",      "1sam": "1 Samuel",      "1 samuel": "1 Samuel",
    "2sa": "2 Samuel",      "2sam": "2 Samuel",      "2 samuel": "2 Samuel",
    "1ki": "1 Kings",       "1kings": "1 Kings",     "1 kings": "1 Kings",
    "2ki": "2 Kings",       "2kings": "2 Kings",     "2 kings": "2 Kings",
    "1ch": "1 Chronicles",  "1chr": "1 Chronicles",  "1 chronicles": "1 Chronicles",
    "2ch": "2 Chronicles",  "2chr": "2 Chronicles",  "2 chronicles": "2 Chronicles",
    "ezr": "Ezra",          "ezra": "Ezra",
    "neh": "Nehemiah",      "nehemiah": "Nehemiah",
    "est": "Esther",        "esther": "Esther",
    "job": "Job",
    "psa": "Psalms",        "ps":  "Psalms",         "psalms": "Psalms",  "psalm": "Psalms",
    "pro": "Proverbs",      "prov": "Proverbs",      "proverbs": "Proverbs",
    "ecc": "Ecclesiastes",  "eccl": "Ecclesiastes",  "ecclesiastes": "Ecclesiastes",
    "sng": "Song of Solomon","song": "Song of Solomon",
    "isa": "Isaiah",        "isaiah": "Isaiah",
    "jer": "Jeremiah",      "jeremiah": "Jeremiah",
    "lam": "Lamentations",  "lamentations": "Lamentations",
    "eze": "Ezekiel",       "ezek": "Ezekiel",       "ezekiel": "Ezekiel",
    "dan": "Daniel",        "daniel": "Daniel",
    "hos": "Hosea",         "hosea": "Hosea",
    "joe": "Joel",          "joel": "Joel",
    "amo": "Amos",          "amos": "Amos",
    "oba": "Obadiah",       "obadiah": "Obadiah",
    "jon": "Jonah",         "jonah": "Jonah",
    "mic": "Micah",         "micah": "Micah",
    "nah": "Nahum",         "nahum": "Nahum",
    "hab": "Habakkuk",      "habakkuk": "Habakkuk",
    "zep": "Zephaniah",     "zeph": "Zephaniah",     "zephaniah": "Zephaniah",
    "hag": "Haggai",        "haggai": "Haggai",
    "zec": "Zechariah",     "zech": "Zechariah",     "zechariah": "Zechariah",
    "mal": "Malachi",       "malachi": "Malachi",
    # NT
    "mat": "Matthew",       "matt": "Matthew",       "matthew": "Matthew",
    "mar": "Mark",          "mark": "Mark",
    "luk": "Luke",          "luke": "Luke",
    "joh": "John",          "john": "John",
    "act": "Acts",          "acts": "Acts",
    "rom": "Romans",        "romans": "Romans",
    "1co": "1 Corinthians", "1cor": "1 Corinthians", "1 corinthians": "1 Corinthians",
    "2co": "2 Corinthians", "2cor": "2 Corinthians", "2 corinthians": "2 Corinthians",
    "gal": "Galatians",     "galatians": "Galatians",
    "eph": "Ephesians",     "ephesians": "Ephesians",
    "phi": "Philippians",   "phil": "Philippians",   "philippians": "Philippians",
    "col": "Colossians",    "colossians": "Colossians",
    "1th": "1 Thessalonians","1thes": "1 Thessalonians","1 thessalonians": "1 Thessalonians",
    "2th": "2 Thessalonians","2thes": "2 Thessalonians","2 thessalonians": "2 Thessalonians",
    "1ti": "1 Timothy",     "1tim": "1 Timothy",     "1 timothy": "1 Timothy",
    "2ti": "2 Timothy",     "2tim": "2 Timothy",     "2 timothy": "2 Timothy",
    "tit": "Titus",         "titus": "Titus",
    "phm": "Philemon",      "philemon": "Philemon",
    "heb": "Hebrews",       "hebrews": "Hebrews",
    "jam": "James",         "jas": "James",          "james": "James",
    "1pe": "1 Peter",       "1pet": "1 Peter",       "1 peter": "1 Peter",
    "2pe": "2 Peter",       "2pet": "2 Peter",       "2 peter": "2 Peter",
    "1jo": "1 John",        "1joh": "1 John",        "1 john": "1 John",
    "2jo": "2 John",        "2joh": "2 John",        "2 john": "2 John",
    "3jo": "3 John",        "3joh": "3 John",        "3 john": "3 John",
    "jud": "Jude",          "jude": "Jude",
    "rev": "Revelation",    "revelation": "Revelation",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def detect_platform() -> str:
    sys_name = platform.system()
    machine  = platform.machine().lower()
    if sys_name == "Darwin":
        return "🍎 Mac Silicon" if "arm" in machine else "🍎 Mac Intel"
    if sys_name == "Windows":
        ver = platform.version()
        win_ver = "11" if int(ver.split(".")[2]) >= 22000 else "10"
        return f"🪟 Windows ({win_ver})"
    if sys_name == "Linux":
        return "🐧 Linux"
    return sys_name


async def ping_internet(session: aiohttp.ClientSession) -> bool:
    try:
        async with session.get("https://www.google.com", timeout=aiohttp.ClientTimeout(total=5)) as r:
            return r.status < 400
    except Exception:
        return False


async def ping_verseview(session: aiohttp.ClientSession) -> bool:
    try:
        async with session.get(VV_BASE, timeout=aiohttp.ClientTimeout(total=3)) as r:
            return r.status < 500
    except Exception:
        return False


async def vv_post(session: aiohttp.ClientSession, endpoint: str, body: dict | None = None) -> bool:
    try:
        async with session.post(
            VV_BASE + endpoint,
            json=body or {},
            timeout=aiohttp.ClientTimeout(total=5)
        ) as r:
            return r.status < 400
    except Exception:
        return False


def parse_verse_ref(parts: list[str]) -> str | None:
    """
    Parse a list of string tokens into a canonical verse reference.
    Examples:
      ["gen", "5", "2"]        → "Genesis 5:2"
      ["1", "cor", "13", "4"]  → "1 Corinthians 13:4"
      ["john", "3:16"]         → "John 3:16"
    Returns None if the book cannot be resolved.
    """
    if not parts:
        return None

    # Handle numbered books: ["1", "cor", ...] → ["1cor", ...]
    if parts[0].isdigit() and len(parts) > 1:
        parts = [parts[0] + parts[1]] + parts[2:]

    book_key = parts[0].lower().rstrip(".")
    book     = BOOK_MAP.get(book_key)
    if not book:
        return None

    nums = parts[1:]
    if not nums:
        return book

    # Allow "3:16" as a single token
    if len(nums) == 1 and ":" in nums[0]:
        return f"{book} {nums[0]}"
    if len(nums) == 1:
        return f"{book} {nums[0]}"
    if len(nums) >= 2:
        return f"{book} {nums[0]}:{nums[1]}"

    return book


# ── Bot ────────────────────────────────────────────────────────────────────────

intents         = discord.Intents.default()
intents.message_content = True
bot             = commands.Bot(command_prefix="!", intents=intents)
tree            = bot.tree
_http_session: aiohttp.ClientSession | None = None


# ── Startup embed ──────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    global _http_session
    _http_session = aiohttp.ClientSession()

    log.info(f"Logged in as {bot.user} ({bot.user.id})")

    try:
        synced = await tree.sync()
        log.info(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        log.warning(f"Slash command sync failed: {e}")

    # Post startup embed to first available text channel
    channel = None
    for guild in bot.guilds:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                channel = ch
                break
        if channel:
            break

    if channel:
        internet_ok = await ping_internet(_http_session)
        vv_ok       = await ping_verseview(_http_session)
        embed = discord.Embed(
            title="🎬 VerseView Bot Online",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="💻 Machine",   value=detect_platform(), inline=True)
        embed.add_field(name="🖥 Hostname",  value=socket.gethostname(), inline=True)
        embed.add_field(name="🐍 Python",    value=platform.python_version(), inline=True)
        embed.add_field(name="🌐 Internet",  value="✅ Online" if internet_ok else "❌ Offline", inline=True)
        embed.add_field(name="📡 VerseView", value="✅ Connected" if vv_ok else "❌ Not reachable", inline=True)
        embed.set_footer(text=f"Started at {datetime.datetime.now().strftime('%H:%M:%S')}")
        await channel.send(embed=embed)

    update_presence.start()
    log.info("Bot ready.")


@bot.event
async def on_close():
    if _http_session:
        await _http_session.close()


# ── Presence loop ──────────────────────────────────────────────────────────────

@tasks.loop(seconds=20)
async def update_presence():
    if not _http_session:
        return
    internet_ok = await ping_internet(_http_session)
    vv_ok       = await ping_verseview(_http_session)

    if not internet_ok:
        status = discord.Status.dnd
        activity = discord.Activity(type=discord.ActivityType.watching, name="No Internet")
    elif not vv_ok:
        status = discord.Status.idle
        activity = discord.Activity(type=discord.ActivityType.watching, name="VerseView Offline")
    else:
        status = discord.Status.online
        activity = discord.Activity(type=discord.ActivityType.watching, name="VerseView Live")

    await bot.change_presence(status=status, activity=activity)


# ── /vv control panel ──────────────────────────────────────────────────────────

class TypeVerseModal(discord.ui.Modal, title="Type a Verse Reference"):
    verse_input = discord.ui.TextInput(
        label="Verse Reference",
        placeholder="e.g. John 3:16 or gen 5 2",
        required=True,
        max_length=80,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw    = self.verse_input.value.strip()
        parts  = raw.split()
        ref    = parse_verse_ref(parts)
        if not ref:
            await interaction.response.send_message(
                f"❌ Could not parse `{raw}` — try `John 3:16` or `gen 5 2`",
                ephemeral=True
            )
            return
        ok = await vv_post(_http_session, ENDPOINT_GOTO, {"ref": ref})
        await interaction.response.send_message(
            f"{'📖 Sent' if ok else '⚠️ Failed'}: **{ref}**",
            ephemeral=True
        )


class VVControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📖 Type Verse", style=discord.ButtonStyle.primary, custom_id="vv_type_verse")
    async def type_verse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TypeVerseModal())

    @discord.ui.button(label="◀ Back", style=discord.ButtonStyle.secondary, custom_id="vv_back")
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = await vv_post(_http_session, ENDPOINT_BACK)
        await interaction.response.send_message("◀ Back" if ok else "⚠️ Failed", ephemeral=True)

    @discord.ui.button(label="▶ Forward", style=discord.ButtonStyle.secondary, custom_id="vv_forward")
    async def go_forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = await vv_post(_http_session, ENDPOINT_FORWARD)
        await interaction.response.send_message("▶ Forward" if ok else "⚠️ Failed", ephemeral=True)

    @discord.ui.button(label="🎬 Present", style=discord.ButtonStyle.success, custom_id="vv_present")
    async def present(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = await vv_post(_http_session, ENDPOINT_PRESENT)
        await interaction.response.send_message("🎬 Presented" if ok else "⚠️ Failed", ephemeral=True)

    @discord.ui.button(label="✕ Close", style=discord.ButtonStyle.danger, custom_id="vv_close")
    async def close_verse(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = await vv_post(_http_session, ENDPOINT_CLOSE)
        await interaction.response.send_message("✕ Closed" if ok else "⚠️ Failed", ephemeral=True)


@tree.command(name="vv", description="Open the VerseView control panel")
async def vv_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📺 VerseView Control Panel",
        description="Use the buttons below to control VerseView.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=VVControlView())


# ── /verse ─────────────────────────────────────────────────────────────────────

@tree.command(name="verse", description="Jump to a verse — e.g. /verse gen 5 2 or /verse 1 cor 13 4")
@app_commands.describe(reference="Book chapter verse — e.g. john 3 16 or 1 cor 13 4")
async def verse_cmd(interaction: discord.Interaction, reference: str):
    parts = reference.strip().split()
    ref   = parse_verse_ref(parts)
    if not ref:
        await interaction.response.send_message(
            f"❌ Could not parse `{reference}`.\nTry: `john 3 16` or `1 cor 13 4`",
            ephemeral=True
        )
        return
    ok = await vv_post(_http_session, ENDPOINT_GOTO, {"ref": ref})
    color = discord.Color.green() if ok else discord.Color.red()
    embed = discord.Embed(
        title="📖 " + ref,
        description="Sent to VerseView ✅" if ok else "⚠️ VerseView not reachable",
        color=color
    )
    await interaction.response.send_message(embed=embed)


# ── /vv_status ─────────────────────────────────────────────────────────────────

@tree.command(name="vv_status", description="Check VerseView and internet connectivity")
async def vv_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    internet_ok = await ping_internet(_http_session)
    vv_ok       = await ping_verseview(_http_session)
    embed = discord.Embed(title="📡 VerseView Status", color=discord.Color.blurple())
    embed.add_field(name="💻 Machine",   value=detect_platform(), inline=True)
    embed.add_field(name="🖥 Hostname",  value=socket.gethostname(), inline=True)
    embed.add_field(name="🌐 Internet",  value="✅ Online"  if internet_ok else "❌ Offline", inline=True)
    embed.add_field(name="📡 VerseView", value="✅ Connected" if vv_ok else "❌ Not reachable", inline=True)
    embed.add_field(name="🔗 VV URL",    value=VV_BASE, inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Set VV_BOT_TOKEN environment variable or edit BOT_TOKEN in this file.")
        sys.exit(1)
    bot.run(BOT_TOKEN, log_handler=None)
