# -*- coding: utf-8 -*-
"""
vv_discord_bot.py — Standalone Discord slash-command bot for VerseView Detector.

This script is launched as a subprocess by the main VerseView app when the user
clicks "Start Bot". It has NO GUI, NO selenium, and NO engine — it only speaks
to the already-running vv_bot_bridge HTTP server (default port 50011) which
wraps the existing Selenium driver.

Environment variables (set by the parent process):
    VV_BOT_TOKEN   — Discord bot token (required)
    VV_HOST        — Bridge host, default 127.0.0.1
    VV_PORT        — Bridge port, default 50011

Slash commands:
    /verse <ref>   — Go to a Bible reference  (e.g. /verse John 3:16)
    /present       — Re-click the PRESENT button
    /next          — Navigate to the next verse
    /prev          — Navigate to the previous verse
    /close         — Close the current presentation
    /status        — Check whether VerseView is connected
"""

import os
import sys
import asyncio
import logging
import urllib.parse
import urllib.request

import discord
from discord import app_commands

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [discord-bot] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Config from env ───────────────────────────────────────────────────────────
TOKEN = os.environ.get("VV_BOT_TOKEN", "").strip()
HOST  = os.environ.get("VV_HOST", "127.0.0.1").strip()
PORT  = int(os.environ.get("VV_PORT", "50011"))

if not TOKEN:
    logger.error("VV_BOT_TOKEN is not set — cannot start Discord bot.")
    sys.exit(1)

BRIDGE_BASE = f"http://{HOST}:{PORT}"

# ── Bridge helper ─────────────────────────────────────────────────────────────

def _bridge(endpoint: str, params: dict | None = None, timeout: int = 8) -> tuple[int, str]:
    """
    Call a vv_bot_bridge endpoint synchronously.
    Returns (http_status_code, body_text).
    Never raises — connection errors return (0, error_message).
    """
    url = BRIDGE_BASE + endpoint
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as exc:
        return 0, str(exc)


# ── Discord bot ───────────────────────────────────────────────────────────────

intents = discord.Intents.default()
client  = discord.Client(intents=intents)
tree    = app_commands.CommandTree(client)


def _reply(status: int, body: str) -> str:
    """Turn a bridge response into a human-friendly Discord message."""
    if status == 200:
        return f"✅ {body}"
    if status == 503:
        return "⚠️ VerseView is not connected — start the engine first."
    if status == 0:
        return f"❌ Could not reach the VerseView bridge ({body}). Is the app running?"
    return f"❌ Bridge error {status}: {body}"


@tree.command(name="verse", description="Go to a Bible verse  (e.g. John 3:16)")
@app_commands.describe(ref="Bible reference, e.g. John 3:16 or 1 Cor 13:4")
async def cmd_verse(interaction: discord.Interaction, ref: str):
    await interaction.response.defer(ephemeral=False)
    status, body = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _bridge("/goto", {"ref": ref})
    )
    await interaction.followup.send(_reply(status, body or f"Presented {ref}"))


@tree.command(name="present", description="Re-present the current verse")
async def cmd_present(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    status, body = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _bridge("/present")
    )
    await interaction.followup.send(_reply(status, body or "Presented"))


@tree.command(name="next", description="Go to the next verse")
async def cmd_next(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    status, body = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _bridge("/next")
    )
    await interaction.followup.send(_reply(status, body or "Next"))


@tree.command(name="prev", description="Go to the previous verse")
async def cmd_prev(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    status, body = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _bridge("/prev")
    )
    await interaction.followup.send(_reply(status, body or "Previous"))


@tree.command(name="close", description="Close the current presentation")
async def cmd_close(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    status, body = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _bridge("/close")
    )
    await interaction.followup.send(_reply(status, body or "Closed"))


@tree.command(name="status", description="Check whether VerseView is connected")
async def cmd_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    status, body = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _bridge("/status")
    )
    await interaction.followup.send(_reply(status, body or "Connected"), ephemeral=True)


@client.event
async def on_ready():
    await tree.sync()
    logger.info(f"Discord bot ready — logged in as {client.user} (id={client.user.id})")
    logger.info(f"Bridge target: {BRIDGE_BASE}")
    print(f"✅ Discord bot online as {client.user}", flush=True)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        client.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("Invalid Discord token — check VV_BOT_TOKEN.")
        sys.exit(1)
    except Exception as exc:
        logger.error(f"Bot crashed: {exc}")
        sys.exit(1)
